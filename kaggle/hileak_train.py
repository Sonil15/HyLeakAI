"""Training loop with three-tier checkpointing, built for interruptible sessions.

Optimiser settings follow the paper's Appendix Table A1: Adam, lr 1e-4,
weight decay 1e-5, learning rate halved every 50 epochs.

Checkpointing writes EVERY epoch and keeps three tiers, because a Kaggle GPU
session is capped well below a full 120-epoch run:

    _best.pt        lowest validation loss so far
    _last.pt        most recent epoch, for exact resume
    _epochNNN.pt    archival snapshots, the last few retained

`_best` and `_last` are rolling and overwrite each epoch; the numbered snapshots
are what let you return to a specific earlier epoch if a later one goes bad.

`target` selects the head configuration:

    "both"        one two-channel head for pressure and saturation (our default;
                  halves training cost, but the two targets conflict — pressure
                  is smooth, global and sign-flipping, saturation is local with
                  a sharp front, and a shared trunk must compromise)
    "pressure"    a single-headed model for pressure only
    "saturation"  a single-headed model for saturation only

The paper trains SEPARATE models per state variable. Running the two
single-headed variants tests whether the shared trunk is what costs us ~1.9x
the paper's error.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from hileak_core import (
    STATE_PRESSURE,
    STATE_SATURATION,
    MultiHeadRelativeL2,
    Normalizer,
    UHSDataset,
    build_unet,
    evaluate,
    load_checkpoint,
    relative_l2,
    save_checkpoint,
    simulation_splits,
)

TARGET_CHANNEL = {"pressure": STATE_PRESSURE, "saturation": STATE_SATURATION}


@torch.no_grad()
def evaluate_single(model, loader, device, channel: int, amp: bool = False) -> float:
    """Relative L2 for a one-headed model predicting a single state variable."""
    model.eval()
    total, n = 0.0, 0
    for x, y in loader:
        x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
        with torch.autocast(device_type=device.type, enabled=amp and device.type == "cuda"):
            pred = model(x)
        total += relative_l2(pred[:, 0], y[:, channel]).item()
        n += 1
    return total / max(n, 1)


def train_unet(
    data_dir,
    ckpt_dir,
    size: str = "small",
    epochs: int = 120,
    batch_size: int = 64,
    lr: float = 1e-4,
    weight_decay: float = 1e-5,
    lr_halve_every: int = 50,
    workers: int = 2,
    amp: bool = True,
    overfit: int = 0,
    snapshot_every: int = 10,
    keep_snapshots: int = 4,
    resume: bool = True,
    seed: int = 20260809,
    target: str = "both",
):
    data_dir, ckpt_dir = Path(data_dir), Path(ckpt_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(seed)
    np.random.seed(seed)

    norm = Normalizer.from_file(data_dir / "stats.json")
    print(f"Device: {device}")
    print(norm.describe())

    splits = simulation_splits()
    if overfit:
        # Deliberately tiny: train and evaluate on the SAME few simulations.
        # The only question this answers is whether the model can fit at all.
        ids = splits["train"][:overfit]
        train_ds = UHSDataset(data_dir, ids, norm)
        val_ds = UHSDataset(data_dir, ids, norm)
        weight_decay = 0.0
        print(f"OVERFIT MODE: {overfit} simulations, {len(train_ds)} samples, train == val")
    else:
        train_ds = UHSDataset(data_dir, splits["train"], norm)
        val_ds = UHSDataset(data_dir, splits["val"], norm)
        assert not set(train_ds.sim_ids) & set(val_ds.sim_ids), "train/val overlap"
        print(f"Simulations  train {len(train_ds.sim_ids)}  val {len(val_ds.sim_ids)}  "
              f"test {len(splits['test'])}")
        print(f"Samples      train {len(train_ds):,}  val {len(val_ds):,}")

    kw = dict(num_workers=workers, pin_memory=(device.type == "cuda"),
              persistent_workers=workers > 0)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, **kw)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, **kw)

    if target not in ("both", "pressure", "saturation"):
        raise ValueError(f"target must be both/pressure/saturation, got {target!r}")
    single = target != "both"
    out_channels = 1 if single else 2
    channel = TARGET_CHANNEL[target] if single else None

    model = build_unet(size, train_ds.in_channels, out_channels).to(device)
    print(f"U-Net-{size}: {model.n_parameters / 1e6:.2f}M parameters, "
          f"{train_ds.in_channels} input channels, "
          f"{'single head -> ' + target if single else 'two heads -> pressure + saturation'}")

    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    sched = torch.optim.lr_scheduler.StepLR(opt, step_size=lr_halve_every, gamma=0.5)
    loss_fn = MultiHeadRelativeL2()
    use_amp = amp and device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    tag = f"unet_{size}" + (f"_{target}" if single else "") + ("_overfit" if overfit else "")
    best_path, last_path = ckpt_dir / f"{tag}_best.pt", ckpt_dir / f"{tag}_last.pt"
    meta = {"size": size, "in_channels": train_ds.in_channels, "use_cyclic": True,
            "use_distance": True, "batch_size": batch_size, "overfit": overfit, "target": target,
            "out_channels": out_channels,
            "normalizer": norm.describe()}

    start, history, best_val = 0, [], float("inf")
    if resume:
        # Try _last, then archival snapshots newest-first. A resume should
        # degrade to "lose a few epochs", never to "start over".
        candidates = [last_path] + sorted(ckpt_dir.glob(f"{tag}_epoch*.pt"), reverse=True)
        for cand in candidates:
            if not cand.exists():
                continue
            try:
                ck = load_checkpoint(cand, model, opt, sched, device)
                start = ck["epoch"] + 1
                history = ck.get("history", [])
                best_val = min((h["val_total"] for h in history), default=float("inf"))
                print(f"RESUMED from {cand.name} at epoch {start} (best val {best_val:.4f})")
                break
            except Exception as exc:
                print(f"WARNING: could not load {cand.name}: {exc}")
        else:
            print("No usable checkpoint found; starting fresh.")

    if start >= epochs:
        print(f"Already trained through epoch {start - 1}; nothing to do.")
        return history

    print(f"\nTraining epochs {start}..{epochs - 1}\n", flush=True)
    for epoch in range(start, epochs):
        model.train()
        t0 = time.monotonic()
        run = {"pressure": 0.0, "saturation": 0.0}
        n = 0
        for x, y in train_loader:
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=use_amp):
                out = model(x)
                if single:
                    total = relative_l2(out[:, 0], y[:, channel])
                    parts = {"pressure": total.detach(), "saturation": total.detach()}
                else:
                    total, parts = loss_fn(out, y)
            scaler.scale(total).backward()
            scaler.step(opt)
            scaler.update()
            run["pressure"] += parts["pressure"].item()
            run["saturation"] += parts["saturation"].item()
            n += 1
        sched.step()

        if single:
            v = evaluate_single(model, val_loader, device, channel, amp=use_amp)
            val = {"pressure": v, "saturation": v}
            val_total = v
        else:
            val = evaluate(model, val_loader, device, amp=use_amp)
            val_total = val["pressure"] + val["saturation"]
        rec = {"epoch": epoch, "lr": opt.param_groups[0]["lr"],
               "train_pressure": run["pressure"] / max(n, 1),
               "train_saturation": run["saturation"] / max(n, 1),
               "val_pressure": val["pressure"], "val_saturation": val["saturation"],
               "val_total": val_total, "seconds": time.monotonic() - t0}
        history.append(rec)

        mark = ""
        if val_total < best_val:
            best_val = val_total
            save_checkpoint(best_path, model, opt, sched, epoch, history, meta)
            mark = "  <- best"
        save_checkpoint(last_path, model, opt, sched, epoch, history, meta)

        if snapshot_every > 0 and epoch % snapshot_every == 0:
            save_checkpoint(ckpt_dir / f"{tag}_epoch{epoch:03d}.pt",
                            model, opt, sched, epoch, history, meta)
            snaps = sorted(ckpt_dir.glob(f"{tag}_epoch*.pt"))
            for old in snaps[:-keep_snapshots]:
                old.unlink(missing_ok=True)

        (ckpt_dir / f"{tag}_history.json").write_text(json.dumps(history, indent=2))
        if single:
            print(f"epoch {epoch:3d}  train {target} {rec['train_pressure']:.4f}  |  "
                  f"val {target} {val['pressure']:.4f}  "
                  f"({rec['seconds']:.0f}s){mark}", flush=True)
        else:
            print(f"epoch {epoch:3d}  train P {rec['train_pressure']:.4f} "
                  f"S {rec['train_saturation']:.4f}  |  val P {val['pressure']:.4f} "
                  f"S {val['saturation']:.4f}  ({rec['seconds']:.0f}s){mark}", flush=True)

    print("\n" + "=" * 70)
    if overfit:
        f, l = history[0], history[-1]
        ok = l["train_pressure"] < 0.05 and l["train_saturation"] < 0.05
        print("OVERFIT TEST")
        print(f"  pressure   {f['train_pressure']:.4f} -> {l['train_pressure']:.4f}")
        print(f"  saturation {f['train_saturation']:.4f} -> {l['train_saturation']:.4f}")
        print(f"  {'PASS' if ok else 'NOT YET'}: a correct model drives both below 0.05 "
              f"on a handful of simulations.")
    else:
        b = min(history, key=lambda h: h["val_total"])
        if single:
            paper = 0.086 if target == "pressure" else 0.0577
            print(f"Best epoch {b['epoch']}: val {target} {b['val_pressure']:.4f}")
            print(f"Paper reference for {target}: {paper}")
        else:
            print(f"Best epoch {b['epoch']}: val pressure {b['val_pressure']:.4f}, "
                  f"saturation {b['val_saturation']:.4f}")
            print("Paper (U-Net-Large, 124M params, A100): pressure 0.0861, saturation 0.0577")
    print("=" * 70)
    return history
