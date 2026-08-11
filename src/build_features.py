"""Build the tabular leakage dataset from the converted fields.

Runs feature extraction and label generation over every simulation and every
Monte-Carlo fault realisation, producing roughly
1,000 sims x 20 faults x 54 usable timesteps ~= 1.08M rows.

Sources:
    --source truth   the simulator's own fields. Use this to TRAIN XGBoost.
    --source unet    U-Net predictions. Use this to measure how much surrogate
                     error propagates into the risk estimate, and to confirm
                     the deployment path (geology in, risk out) actually works.

Usage:
    python -m src.build_features --workers 12
    python -m src.build_features --limit-sims 20 --workers 4     # smoke test
    python -m src.build_features --source unet \
        --checkpoint checkpoints/unet_small_best.pt --out data/features_unet.npy
"""

from __future__ import annotations

import argparse
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from src import config as C
from src.config import LEAKAGE
from src.data.lmdb_convert import restore_pressure
from src.leakage.features import (
    FORECAST_HORIZONS,
    apply_leak_threshold,
    build_feature_table,
    feature_columns,
    label_columns,
    save_table,
)

# Set once per worker process so the memmaps are opened lazily and reused.
_WORKER: dict = {}


def _init_worker(data_dir: str) -> None:
    d = Path(data_dir)
    _WORKER["constants"] = np.load(d / "constants.npy", mmap_mode="r")
    _WORKER["states"] = np.load(d / "states.npy", mmap_mode="r")


def _pressure_of(sim: int) -> np.ndarray:
    """Physical pressure in bar; the memmap stores it centred on P_INIT."""
    return restore_pressure(_WORKER["states"][sim, :, C.STATE_PRESSURE])


def _saturation_of(sim: int) -> np.ndarray:
    return np.asarray(_WORKER["states"][sim, :, C.STATE_SATURATION], np.float32)


def _process_chunk(payload: tuple[list[int], tuple[int, ...]]) -> tuple[np.ndarray, list[str]]:
    sim_ids, horizons = payload
    return build_feature_table(
        _WORKER["constants"],
        _pressure_of,
        _saturation_of,
        sim_ids,
        cfg=LEAKAGE,
        horizons=horizons,
        progress_every=0,
    )


def _select_sims(args) -> list[int]:
    """Simulation ids to build, honouring --split and --limit-sims."""
    ids = (list(range(C.N_SIMS)) if args.split == "all"
           else C.simulation_splits()[args.split])
    if args.limit_sims is not None:
        ids = ids[: args.limit_sims]
    return ids


def _chunks(items: list[int], n: int) -> list[list[int]]:
    size = max(1, (len(items) + n - 1) // n)
    return [items[i : i + size] for i in range(0, len(items), size)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=C.DATA_DIR)
    ap.add_argument("--out", type=Path, default=C.DATA_DIR / "features.npy")
    ap.add_argument("--source", choices=["truth", "unet"], default="truth")
    ap.add_argument("--checkpoint", type=Path, default=None,
                    help="required when --source unet")
    ap.add_argument("--limit-sims", type=int, default=None)
    ap.add_argument("--split", choices=["all", "train", "val", "test"], default="all",
                    help="restrict to one simulation split. 'test' is what the "
                         "surrogate-transfer measurement needs, and is ~6x faster "
                         "than building all 1,000 simulations.")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--leak-quantile", type=float, default=0.90)
    ap.add_argument("--horizons", type=int, nargs="+", default=list(FORECAST_HORIZONS),
                    help="forecast horizons in timesteps (2 months each)")
    args = ap.parse_args()
    horizons = tuple(sorted(set(args.horizons)))

    if args.source == "unet":
        if args.checkpoint is None:
            ap.error("--source unet requires --checkpoint")
        return _build_from_unet(args)

    sim_ids = _select_sims(args)
    print(f"Building features for {len(sim_ids)} simulations ({args.split} split), "
          f"{LEAKAGE.n_faults_per_sim} faults each.")
    print(f"Horizons: " + ", ".join(
        f"{h} steps ({h * C.MONTHS_PER_STEP} months)" for h in horizons))

    t0 = time.monotonic()
    if args.workers > 1:
        chunks = [(c, horizons) for c in _chunks(sim_ids, args.workers)]
        tables, columns = [], None
        with ProcessPoolExecutor(
            max_workers=args.workers, initializer=_init_worker,
            initargs=(str(args.data_dir),),
        ) as pool:
            for i, (tbl, cols) in enumerate(pool.map(_process_chunk, chunks), start=1):
                tables.append(tbl)
                columns = columns or cols
                print(f"  chunk {i}/{len(chunks)}: {tbl.shape[0]:,} rows "
                      f"({time.monotonic() - t0:.0f}s elapsed)", flush=True)
        table = np.concatenate(tables, axis=0)
    else:
        _init_worker(str(args.data_dir))
        table, columns = build_feature_table(
            _WORKER["constants"], _pressure_of, _saturation_of, sim_ids,
            horizons=horizons,
        )

    table, thresholds = apply_leak_threshold(table, columns, args.leak_quantile, horizons)
    elapsed = time.monotonic() - t0

    print(f"\nBuilt {table.shape[0]:,} rows x {table.shape[1]} columns in "
          f"{elapsed / 60:.1f} min")
    print(f"Model features: {len(feature_columns(columns))}")

    print(f"\n{'horizon':>8}  {'months':>6}  {'rows':>10}  {'% zero':>7}  "
          f"{'threshold m3/s':>14}  {'pos rate':>8}")
    for h in horizons:
        names = label_columns(h)
        q = table[:, columns.index(names["q"])]
        leak = table[:, columns.index(names["leak"])]
        valid = np.isfinite(q)
        print(f"{h:>8}  {h * C.MONTHS_PER_STEP:>6}  {int(valid.sum()):>10,}  "
              f"{100 * (q[valid] == 0).mean():>6.1f}%  {thresholds[h]:>14.4g}  "
              f"{np.nanmean(leak[valid]):>8.4f}")

    save_table(
        args.out, table, columns,
        meta={
            "source": args.source,
            "n_sims": len(sim_ids),
            "n_faults_per_sim": LEAKAGE.n_faults_per_sim,
            "horizons_steps": list(horizons),
            "horizons_months": [h * C.MONTHS_PER_STEP for h in horizons],
            "leak_thresholds_m3_s": {str(k): v for k, v in thresholds.items()},
            "leak_quantile": args.leak_quantile,
            "build_seconds": elapsed,
            "leakage_config": {
                k: (list(v) if isinstance(v, tuple) else v)
                for k, v in vars(LEAKAGE).items()
            },
        },
    )
    print(f"Saved {args.out}")
    return 0


def _build_from_unet(args) -> int:
    """Same table, but the fields come from the surrogate instead of the simulator."""
    import torch

    from src.data.dataset import Normalizer, UHSDataset
    from src.models.unet import build_unet, load_state_dict_compat

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=False)
    meta = ckpt.get("meta", {})
    normalizer = Normalizer.from_file(args.data_dir / "stats.json")

    probe = UHSDataset(
        "test", data_dir=args.data_dir, normalizer=normalizer,
        use_cyclic=meta.get("use_cyclic", True),
        use_distance=meta.get("use_distance", True),
        sim_ids=[0],
    )
    model = build_unet(meta.get("size", "small"),
                       in_channels=probe.in_channels, out_channels=2).to(device)
    load_state_dict_compat(model, ckpt["model"])
    model.eval()
    print(f"Loaded {args.checkpoint} on {device}")

    constants = np.load(args.data_dir / "constants.npy", mmap_mode="r")
    sim_ids = _select_sims(args)
    print(f"Building {len(sim_ids)} simulations ({args.split} split)")
    cache: dict[int, tuple[np.ndarray, np.ndarray]] = {}

    @torch.no_grad()
    def predict(sim: int) -> tuple[np.ndarray, np.ndarray]:
        if sim in cache:
            return cache[sim]
        ds = UHSDataset(
            "test", data_dir=args.data_dir, normalizer=normalizer,
            use_cyclic=probe.use_cyclic, use_distance=probe.use_distance,
            sim_ids=[sim],
        )
        x = torch.stack([ds.build_input_tensor(sim, t) for t in range(1, C.N_TIMESTEPS + 1)])
        out = model(x.to(device)).cpu().numpy()
        pressure = normalizer.pressure_inverse(out[:, C.STATE_PRESSURE]).astype(np.float32)
        saturation = np.clip(out[:, C.STATE_SATURATION], 0.0, 1.0).astype(np.float32)
        cache.clear()
        cache[sim] = (pressure, saturation)
        return cache[sim]

    # Labels come from the SIMULATOR even though features come from the U-Net.
    # That is the deployment question: given surrogate-predicted fields, can we
    # predict the TRUE leakage? Taking labels from the surrogate too would let
    # its errors cancel out and the score would look fine however wrong the
    # fields were.
    states = np.load(args.data_dir / "states.npy", mmap_mode="r")

    def truth_pressure(sim):
        return restore_pressure(states[sim, :, C.STATE_PRESSURE])

    def truth_saturation(sim):
        return np.asarray(states[sim, :, C.STATE_SATURATION], np.float32)

    horizons = tuple(sorted(set(args.horizons)))
    t0 = time.monotonic()
    table, columns = build_feature_table(
        constants, lambda s: predict(s)[0], lambda s: predict(s)[1], sim_ids,
        horizons=horizons,
        label_pressure_bar=truth_pressure,
        label_saturation=truth_saturation,
    )

    # Reuse the truth table's thresholds so the two runs are directly
    # comparable; a threshold refitted here would shift the class balance and
    # make any difference in score partly an artefact of that.
    thresholds = None
    truth_meta = args.data_dir / "features.columns.json"
    if truth_meta.exists():
        import json

        stored = json.loads(truth_meta.read_text()).get("meta", {}).get(
            "leak_thresholds_m3_s")
        if stored:
            thresholds = {int(k): float(v) for k, v in stored.items()}
            for h in horizons:
                names = label_columns(h)
                qi, li = columns.index(names["q"]), columns.index(names["leak"])
                q = table[:, qi]
                table[:, li] = np.where(
                    np.isfinite(q), (q > thresholds[h]).astype(np.float32), np.nan)
            print(f"Reused truth-table leak thresholds: "
                  + ", ".join(f"h{h}={thresholds[h]:.4g}" for h in horizons))
    if thresholds is None:
        table, thresholds = apply_leak_threshold(
            table, columns, args.leak_quantile, horizons)
        print("WARNING: no truth table found; thresholds refitted on this table, "
              "so scores are NOT directly comparable to the truth-source run.")

    print(f"\nBuilt {table.shape[0]:,} rows in {(time.monotonic() - t0) / 60:.1f} min")
    print("Features from U-Net predictions; labels from the simulator.")
    save_table(args.out, table, columns,
               meta={"source": "unet_features_truth_labels",
                     "checkpoint": str(args.checkpoint),
                     "horizons_steps": list(horizons),
                     "leak_thresholds_m3_s": {str(k): v for k, v in thresholds.items()}})
    print(f"Saved {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
