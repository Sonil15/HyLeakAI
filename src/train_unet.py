"""Train the U-Net surrogate on the UHS dataset.

Optimiser settings follow the paper's Appendix Table A1: Adam, learning rate
1e-4, weight decay 1e-5, learning rate halved every 50 epochs.

Modes:

    --overfit N     Train on N simulations with no regularisation and confirm
                    the loss collapses toward zero. This catches architecture,
                    normalisation and channel-ordering bugs in a couple of
                    minutes, before committing hours to a real run. Always run
                    this first after touching the model or the dataset.

    (default)       Full training with per-epoch checkpointing, so an
                    interrupted Colab session resumes instead of restarting.

Examples:
    python -m src.train_unet --overfit 4 --epochs 60
    python -m src.train_unet --size small --epochs 120 --batch-size 32
    python -m src.train_unet --resume checkpoints/unet_small_last.pt
    python -m src.train_unet --eval-only checkpoints/unet_small_best.pt
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from src import config as C
from src.data.dataset import UHSDataset, Normalizer, make_datasets
from src.models.unet import build_unet, MultiHeadRelativeL2, relative_l2

PRESSURE_CH, SATURATION_CH = 0, 1


def pick_device(requested: str = "auto") -> torch.device:
    if requested != "auto":
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def set_seed(seed: int) -> None:
    import random

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


# --------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------


@torch.no_grad()
def evaluate(model, loader, device, amp: bool = False) -> dict[str, float]:
    """Mean per-sample relative L2 per state variable — the paper's test-error
    metric, so these numbers are directly comparable to its Table 4."""
    model.eval()
    totals = {"pressure": 0.0, "saturation": 0.0}
    n_batches = 0
    for x, y in loader:
        x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
        with torch.autocast(device_type=device.type, enabled=amp and device.type == "cuda"):
            pred = model(x)
        totals["pressure"] += relative_l2(pred[:, PRESSURE_CH], y[:, PRESSURE_CH]).item()
        totals["saturation"] += relative_l2(
            pred[:, SATURATION_CH], y[:, SATURATION_CH]
        ).item()
        n_batches += 1
    return {k: v / max(n_batches, 1) for k, v in totals.items()}


# --------------------------------------------------------------------------
# Checkpointing
# --------------------------------------------------------------------------


def save_checkpoint(path: Path, model, optimizer, scheduler, epoch: int, history: list, meta: dict):
    """Write a checkpoint atomically.

    Written to a temporary file and then moved into place, so an interruption
    mid-write (a Colab disconnect, a killed process) cannot leave a truncated
    file where a valid one used to be. Without this, being disconnected during
    the save destroys the very checkpoint meant to protect against it.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(
        {
            "epoch": epoch,
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict(),
            "history": history,
            "meta": meta,
        },
        tmp,
    )
    tmp.replace(path)


def prune_snapshots(ckpt_dir: Path, tag: str, keep: int) -> None:
    """Keep only the `keep` most recent archival snapshots.

    Each is ~93 MB for U-Net-Small, so they are capped rather than kept
    forever. `_best.pt` and `_last.pt` are separate files and are never pruned.
    """
    snaps = sorted(ckpt_dir.glob(f"{tag}_epoch*.pt"))
    for old in snaps[:-keep] if keep > 0 else snaps:
        old.unlink(missing_ok=True)


def load_checkpoint(path: Path, model, optimizer=None, scheduler=None, device="cpu"):
    ckpt = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model"])
    if optimizer is not None and "optimizer" in ckpt:
        optimizer.load_state_dict(ckpt["optimizer"])
    if scheduler is not None and "scheduler" in ckpt:
        scheduler.load_state_dict(ckpt["scheduler"])
    return ckpt


# --------------------------------------------------------------------------
# Training
# --------------------------------------------------------------------------


def train(args) -> dict:
    device = pick_device(args.device)
    set_seed(args.seed)
    print(f"Device: {device}")
    if device.type == "cpu":
        torch.set_num_threads(args.cpu_threads)
        print(f"CPU threads: {args.cpu_threads}")

    data_dir = Path(args.data_dir)
    normalizer = Normalizer.from_file(data_dir / "stats.json")
    print(normalizer.describe())

    # ---- datasets ----
    if args.overfit:
        # Deliberately tiny: train and evaluate on the SAME few simulations.
        # The only question this answers is whether the model can fit at all.
        sims = C.simulation_splits()["train"][: args.overfit]
        common = dict(
            data_dir=data_dir,
            normalizer=normalizer,
            use_cyclic=not args.no_cyclic,
            use_distance=not args.no_distance,
            sim_ids=sims,
        )
        train_ds = UHSDataset("train", **common)
        val_ds = UHSDataset("val", **common)
        print(f"OVERFIT MODE: {len(sims)} simulations, {len(train_ds)} samples, train == val")
    else:
        ds = make_datasets(
            data_dir=data_dir,
            use_cyclic=not args.no_cyclic,
            use_distance=not args.no_distance,
            sim_limit=args.sim_limit,
        )
        train_ds, val_ds = ds["train"], ds["val"]
        print(
            f"Simulations  train {len(train_ds.sim_ids)}  "
            f"val {len(val_ds.sim_ids)}  test {len(ds['test'].sim_ids)}"
        )
        print(f"Samples      train {len(train_ds)}  val {len(val_ds)}")
        overlap = set(train_ds.sim_ids) & set(val_ds.sim_ids)
        assert not overlap, f"train/val simulation overlap: {sorted(overlap)[:5]}"

    loader_kw = dict(
        num_workers=args.workers,
        pin_memory=(device.type == "cuda"),
        persistent_workers=args.workers > 0,
    )
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, **loader_kw)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, **loader_kw)

    # ---- model ----
    model = build_unet(
        args.size, in_channels=train_ds.in_channels, out_channels=2
    ).to(device)
    print(f"U-Net-{args.size}: {model.n_parameters / 1e6:.2f}M parameters, "
          f"{train_ds.in_channels} input channels")

    weight_decay = 0.0 if args.overfit else args.weight_decay
    optimizer = torch.optim.Adam(
        model.parameters(), lr=args.learning_rate, weight_decay=weight_decay
    )
    # Paper: "halves the rate every 50 epochs".
    scheduler = torch.optim.lr_scheduler.StepLR(
        optimizer, step_size=args.lr_halve_every, gamma=0.5
    )
    loss_fn = MultiHeadRelativeL2(
        lambda_pressure=args.lambda_pressure,
        lambda_saturation=args.lambda_saturation,
        pressure_channel=PRESSURE_CH,
        saturation_channel=SATURATION_CH,
    )

    tag = f"unet_{args.size}" + ("_overfit" if args.overfit else "")
    ckpt_dir = Path(args.checkpoint_dir)
    best_path, last_path = ckpt_dir / f"{tag}_best.pt", ckpt_dir / f"{tag}_last.pt"

    start_epoch, history, best_val = 0, [], float("inf")
    if args.resume:
        # Try the requested checkpoint, then fall back through the archival
        # snapshots newest-first. A resume should degrade to "lose a few epochs",
        # never to "start over".
        candidates = [Path(args.resume)] + sorted(
            ckpt_dir.glob(f"{tag}_epoch*.pt"), reverse=True
        )
        ckpt = None
        for candidate in candidates:
            if not candidate.exists():
                continue
            try:
                ckpt = load_checkpoint(candidate, model, optimizer, scheduler, device)
                if candidate != Path(args.resume):
                    print(f"WARNING: {args.resume} unreadable; fell back to {candidate.name}")
                break
            except Exception as exc:
                print(f"WARNING: could not load {candidate.name}: {exc}")
        if ckpt is None:
            print(f"No usable checkpoint among {len(candidates)} candidates; starting fresh.")
        else:
            start_epoch = ckpt["epoch"] + 1
            history = ckpt.get("history", [])
            best_val = min((h["val_total"] for h in history), default=float("inf"))
            print(f"Resumed at epoch {start_epoch} (best val {best_val:.4f})")

    meta = {
        "size": args.size,
        "in_channels": train_ds.in_channels,
        "use_cyclic": not args.no_cyclic,
        "use_distance": not args.no_distance,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "weight_decay": weight_decay,
        "overfit": args.overfit,
        "sim_limit": args.sim_limit,
        "train_sims": len(train_ds.sim_ids),
        "normalizer": normalizer.describe(),
    }

    use_amp = args.amp and device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    print(f"\nTraining epochs {start_epoch}..{args.epochs - 1}\n")
    for epoch in range(start_epoch, args.epochs):
        model.train()
        t0 = time.monotonic()
        run = {"total": 0.0, "pressure": 0.0, "saturation": 0.0}
        n = 0
        for x, y in train_loader:
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=use_amp):
                total, parts = loss_fn(model(x), y)
            scaler.scale(total).backward()
            scaler.step(optimizer)
            scaler.update()

            run["total"] += total.item()
            run["pressure"] += parts["pressure"].item()
            run["saturation"] += parts["saturation"].item()
            n += 1
        scheduler.step()

        train_metrics = {k: v / max(n, 1) for k, v in run.items()}
        val = evaluate(model, val_loader, device, amp=use_amp)
        val_total = (
            args.lambda_pressure * val["pressure"]
            + args.lambda_saturation * val["saturation"]
        )
        record = {
            "epoch": epoch,
            "lr": optimizer.param_groups[0]["lr"],
            "train_total": train_metrics["total"],
            "train_pressure": train_metrics["pressure"],
            "train_saturation": train_metrics["saturation"],
            "val_pressure": val["pressure"],
            "val_saturation": val["saturation"],
            "val_total": val_total,
            "seconds": time.monotonic() - t0,
        }
        history.append(record)

        # Three-tier checkpointing, all written every epoch:
        #   _best.pt      lowest validation loss seen so far
        #   _last.pt      most recent epoch, for exact resume
        #   _epochNNN.pt  periodic archival snapshot, last `--keep-snapshots` kept
        # best and last are rolling and overwrite; the snapshots are what let
        # you go back to a specific earlier epoch if a late one goes bad.
        marker = ""
        if val_total < best_val:
            best_val = val_total
            save_checkpoint(best_path, model, optimizer, scheduler, epoch, history, meta)
            marker = "  <- best"
        save_checkpoint(last_path, model, optimizer, scheduler, epoch, history, meta)

        if args.snapshot_every > 0 and epoch % args.snapshot_every == 0:
            save_checkpoint(
                ckpt_dir / f"{tag}_epoch{epoch:03d}.pt",
                model, optimizer, scheduler, epoch, history, meta,
            )
            prune_snapshots(ckpt_dir, tag, args.keep_snapshots)

        print(
            f"epoch {epoch:3d}  "
            f"train P {record['train_pressure']:.4f} S {record['train_saturation']:.4f}  |  "
            f"val P {val['pressure']:.4f} S {val['saturation']:.4f}  "
            f"({record['seconds']:.0f}s){marker}",
            flush=True,
        )

        Path(args.checkpoint_dir).mkdir(parents=True, exist_ok=True)
        (ckpt_dir / f"{tag}_history.json").write_text(json.dumps(history, indent=2))

    # ---- final report ----
    print("\n" + "=" * 68)
    if args.overfit:
        first, last = history[0], history[-1]
        drop_p = last["train_pressure"] / max(first["train_pressure"], 1e-12)
        drop_s = last["train_saturation"] / max(first["train_saturation"], 1e-12)
        print("OVERFIT TEST")
        print(f"  pressure   {first['train_pressure']:.4f} -> {last['train_pressure']:.4f} "
              f"({drop_p * 100:.1f}% of initial)")
        print(f"  saturation {first['train_saturation']:.4f} -> {last['train_saturation']:.4f} "
              f"({drop_s * 100:.1f}% of initial)")
        ok = last["train_pressure"] < 0.05 and last["train_saturation"] < 0.05
        print(f"  {'PASS' if ok else 'FAIL'}: a correct model should drive both below 0.05 "
              f"on a handful of simulations.")
    else:
        best = min(history, key=lambda h: h["val_total"])
        print(f"Best epoch {best['epoch']}: "
              f"val pressure {best['val_pressure']:.4f}, "
              f"saturation {best['val_saturation']:.4f}")
        print("Paper reference (U-Net-Large, A100, 700 sims): "
              "saturation 0.0577, pressure 0.0861")
    print("=" * 68)
    return {"history": history, "best_checkpoint": str(best_path)}


def evaluate_checkpoint(args) -> None:
    """Report held-out TEST error. Run this once, at the end."""
    device = pick_device(args.device)
    data_dir = Path(args.data_dir)
    ckpt = torch.load(Path(args.eval_only), map_location=device, weights_only=False)
    meta = ckpt.get("meta", {})

    ds = make_datasets(
        data_dir=data_dir,
        use_cyclic=meta.get("use_cyclic", True),
        use_distance=meta.get("use_distance", True),
    )
    test_ds = ds["test"]
    # Guard against the single most damaging possible bug in this project.
    for other in ("train", "val"):
        overlap = set(test_ds.sim_ids) & set(ds[other].sim_ids)
        assert not overlap, f"test/{other} simulation overlap: {sorted(overlap)[:5]}"
    print(f"OK splits disjoint. Test simulations: {len(test_ds.sim_ids)}")

    model = build_unet(
        meta.get("size", args.size), in_channels=test_ds.in_channels, out_channels=2
    ).to(device)
    model.load_state_dict(ckpt["model"])

    loader = DataLoader(test_ds, batch_size=args.batch_size, num_workers=args.workers)
    metrics = evaluate(model, loader, device)
    print(f"\nTEST relative L2  pressure {metrics['pressure']:.4f}  "
          f"saturation {metrics['saturation']:.4f}")
    print("Paper (U-Net-Large): pressure 0.0861, saturation 0.0577")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", default=str(C.DATA_DIR))
    p.add_argument("--checkpoint-dir", default=str(C.CHECKPOINT_DIR))
    p.add_argument("--size", default="small", choices=["small", "medium", "large"])
    p.add_argument("--epochs", type=int, default=120)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--learning-rate", type=float, default=1e-4)
    p.add_argument("--weight-decay", type=float, default=1e-5)
    p.add_argument("--lr-halve-every", type=int, default=50)
    p.add_argument("--lambda-pressure", type=float, default=1.0)
    p.add_argument("--lambda-saturation", type=float, default=1.0)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--cpu-threads", type=int, default=12)
    p.add_argument("--device", default="auto")
    p.add_argument("--amp", action="store_true", help="mixed precision (CUDA only)")
    p.add_argument("--seed", type=int, default=C.SPLIT_SEED)
    p.add_argument("--overfit", type=int, default=0,
                   help="sanity mode: fit N simulations, expect loss -> 0")
    p.add_argument("--sim-limit", type=int, default=None,
                   help="cap simulations per split (CPU-only fallback)")
    p.add_argument("--no-cyclic", action="store_true")
    p.add_argument("--no-distance", action="store_true")
    p.add_argument("--snapshot-every", type=int, default=10,
                   help="archive a numbered checkpoint every N epochs (0 disables)")
    p.add_argument("--keep-snapshots", type=int, default=5,
                   help="how many numbered snapshots to retain (~93MB each for Small)")
    p.add_argument("--resume", default=None)
    p.add_argument("--eval-only", default=None, help="checkpoint to evaluate on the test split")
    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    if args.eval_only:
        evaluate_checkpoint(args)
    else:
        train(args)
