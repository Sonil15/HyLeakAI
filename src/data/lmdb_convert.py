"""Convert the Mao et al. UHS LMDB into compact numpy memmaps.

Why convert at all: the LMDB is 12.38 GB and every read costs a pickle
round-trip, which makes it a poor fit for a DataLoader with several workers and
far too large to put on a free-tier Google Drive for Colab. The converted form
is ~4.1 GB and memory-maps directly.

Layout produced in data/:

    constants.npy  (1000, 2, 128, 128)      float32   ~131 MB
                   channel 0 porosity, channel 1 permeability
    states.npy     (1000, 60, 2, 128, 128)  float16   ~3.93 GB
                   channel 0 pressure (CENTRED, see below), channel 1 saturation
    stats.json     per-channel mean/std/min/max in physical units

Two precision decisions, both deliberate:

  * Constants stay float32. Permeability may be stored in m^2 (~1e-13), and
    float16's smallest normal value is 6.1e-5 — such values would silently
    flush to zero. 131 MB is not worth that risk.

  * Pressure is stored as (P_bar - 197.2), i.e. centred on the initial
    reservoir pressure. Raw ~200 bar in float16 resolves to only ~0.125 bar;
    centred, the values sit in roughly +/-60 bar where the resolution is
    ~0.03 bar. This uses a known constant rather than a dataset mean, so it
    needs no extra pass over 12 GB. Restore with `restore_pressure()`.

Timestep 0 is dropped: the paper and the dataset README both state it is the
pre-injection state and identical across all 1,000 simulations.

Usage:
    python -m src.data.lmdb_convert
    python -m src.data.lmdb_convert --limit-sims 20     # fast smoke test
    python -m src.data.lmdb_convert --verify-only
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src import config as C  # noqa: E402


# --------------------------------------------------------------------------
# LMDB access
# --------------------------------------------------------------------------


def open_env(path: Path):
    """Open the LMDB. The Zenodo download is a bare `data.mdb` rather than an
    LMDB directory, so `subdir=False`; `lock=False` avoids needing lock.mdb."""
    import lmdb

    return lmdb.open(
        str(path),
        subdir=False,
        readonly=True,
        lock=False,
        readahead=False,
        max_readers=256,
    )


def _to_numpy(obj) -> np.ndarray:
    """Values may be numpy arrays or torch tensors (the dataset README lists
    torch as a dependency). Normalise to numpy without importing torch unless
    we actually need it."""
    if isinstance(obj, np.ndarray):
        return obj
    if hasattr(obj, "detach"):  # torch.Tensor
        return obj.detach().cpu().numpy()
    return np.asarray(obj)


def get_constants(txn, sim: int) -> tuple[np.ndarray, np.ndarray]:
    """Key is the pickled simulation number as a *string*, e.g. pickle.dumps("0")."""
    raw = txn.get(pickle.dumps(str(sim)))
    if raw is None:
        raise KeyError(f"missing constants for simulation {sim}")
    porosity, permeability = pickle.loads(raw)
    return _to_numpy(porosity), _to_numpy(permeability)


def get_state(txn, sim: int, t: int) -> tuple[np.ndarray, ...]:
    """Key is pickle.dumps("<sim>-<t>").

    The dataset README documents the value as (pressure_bar, h2_saturation).
    It is in fact a 3-tuple — see the STATE_CHANNEL_NAMES note in config.py for
    what we determined the third channel to be. We unpack whatever arity is
    present rather than assuming, so a future revision of the dataset does not
    silently break or silently drop data.
    """
    raw = txn.get(pickle.dumps(f"{sim}-{t}"))
    if raw is None:
        raise KeyError(f"missing state for simulation {sim}, timestep {t}")
    return tuple(_to_numpy(a) for a in pickle.loads(raw))


def probe(path: Path) -> dict:
    """Inspect one record so the real shapes, dtypes and ranges are known
    before committing to a 4 GB write."""
    env = open_env(path)
    with env.begin() as txn:
        poro, perm = get_constants(txn, 0)
        state = get_state(txn, 0, 1)
        n_entries = txn.stat()["entries"]
    env.close()

    def describe(name, a):
        return {
            "name": name,
            "shape": list(a.shape),
            "dtype": str(a.dtype),
            "min": float(np.min(a)),
            "max": float(np.max(a)),
            "mean": float(np.mean(a)),
        }

    info = {
        "lmdb_entries": n_entries,
        "state_tuple_arity": len(state),
        "porosity": describe("porosity", poro),
        "permeability": describe("permeability", perm),
    }
    for i, arr in enumerate(state):
        name = (
            C.STATE_CHANNEL_NAMES[i]
            if i < len(C.STATE_CHANNEL_NAMES)
            else f"state_channel_{i}"
        )
        info[name] = describe(name, arr)
    return info


# --------------------------------------------------------------------------
# Pressure centring
# --------------------------------------------------------------------------


def centre_pressure(p_bar: np.ndarray) -> np.ndarray:
    return p_bar - C.P_INIT_BAR


def restore_pressure(p_centred: np.ndarray) -> np.ndarray:
    """Inverse of `centre_pressure`. Use this anywhere physical pressure in bar
    is needed (leakage labels, feature extraction, plots)."""
    return np.asarray(p_centred, dtype=np.float32) + C.P_INIT_BAR


# --------------------------------------------------------------------------
# Running statistics
# --------------------------------------------------------------------------


class RunningStats:
    """float64 accumulators so the stats are exact regardless of storage dtype."""

    def __init__(self, name: str):
        self.name = name
        self.n = 0
        self.total = 0.0
        self.total_sq = 0.0
        self.vmin = np.inf
        self.vmax = -np.inf

    def update(self, a: np.ndarray) -> None:
        a64 = np.asarray(a, dtype=np.float64)
        self.n += a64.size
        self.total += float(a64.sum())
        self.total_sq += float(np.square(a64).sum())
        self.vmin = min(self.vmin, float(a64.min()))
        self.vmax = max(self.vmax, float(a64.max()))

    def result(self) -> dict:
        mean = self.total / self.n
        var = max(self.total_sq / self.n - mean * mean, 0.0)
        return {
            "count": self.n,
            "mean": mean,
            "std": float(np.sqrt(var)),
            "min": self.vmin,
            "max": self.vmax,
        }


# --------------------------------------------------------------------------
# Conversion
# --------------------------------------------------------------------------


def convert(
    lmdb_path: Path,
    out_dir: Path,
    n_sims: int = C.N_SIMS,
    n_steps: int = C.N_TIMESTEPS,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    g = C.GRID

    constants = np.lib.format.open_memmap(
        out_dir / "constants.npy", mode="w+", dtype=np.float32, shape=(n_sims, 2, g, g)
    )
    states = np.lib.format.open_memmap(
        out_dir / "states.npy",
        mode="w+",
        dtype=np.float16,
        shape=(n_sims, n_steps, C.N_STATE_CHANNELS, g, g),
    )

    stats = {
        "porosity": RunningStats("porosity"),
        "permeability": RunningStats("permeability"),
        "log10_permeability": RunningStats("log10_permeability"),
        "pressure_bar": RunningStats("pressure_bar"),
        "pressure_centred": RunningStats("pressure_centred"),
        "saturation": RunningStats("saturation"),
        "aux_undocumented": RunningStats("aux_undocumented"),
    }

    env = open_env(lmdb_path)
    t0 = time.monotonic()
    with env.begin(buffers=False) as txn:
        for sim in range(n_sims):
            poro, perm = get_constants(txn, sim)
            constants[sim, C.CONST_POROSITY] = poro
            constants[sim, C.CONST_PERMEABILITY] = perm
            stats["porosity"].update(poro)
            stats["permeability"].update(perm)
            with np.errstate(divide="ignore"):
                stats["log10_permeability"].update(
                    np.log10(np.maximum(np.asarray(perm, np.float64), 1e-30))
                )

            # Timesteps are stored 1..n_steps; index 0 of our array is t=1.
            for t in range(1, n_steps + 1):
                state = get_state(txn, sim, t)
                pres, sat = state[0], state[1]
                aux = state[2] if len(state) > 2 else np.zeros_like(sat)
                pres_c = centre_pressure(np.asarray(pres, np.float32))
                states[sim, t - 1, C.STATE_PRESSURE] = pres_c
                states[sim, t - 1, C.STATE_SATURATION] = sat
                states[sim, t - 1, C.STATE_AUX] = aux
                stats["pressure_bar"].update(pres)
                stats["pressure_centred"].update(pres_c)
                stats["saturation"].update(sat)
                stats["aux_undocumented"].update(aux)

            if (sim + 1) % 25 == 0 or sim + 1 == n_sims:
                elapsed = time.monotonic() - t0
                rate = (sim + 1) / elapsed
                print(
                    f"  {sim + 1:4d}/{n_sims} sims  "
                    f"{elapsed / 60:5.1f} min  "
                    f"ETA {(n_sims - sim - 1) / rate / 60:5.1f} min",
                    flush=True,
                )
    env.close()

    constants.flush()
    states.flush()

    summary = {
        "n_sims": n_sims,
        "n_timesteps": n_steps,
        "grid": g,
        "timestep_zero_dropped": C.DROP_TIMESTEP_ZERO,
        "pressure_storage": "centred: stored = P_bar - P_INIT_BAR",
        "p_init_bar": C.P_INIT_BAR,
        "constants_dtype": "float32",
        "states_dtype": "float16",
        "channels": {
            "constants": ["porosity", "permeability"],
            "states": ["pressure_centred", "saturation", "aux_undocumented"],
        },
        "aux_channel_note": (
            "The dataset README documents a 2-tuple; the records are 3-tuples. "
            "The third channel is ~99% collinear with pressure "
            "(aux ~= -1.17e-4 * (P - P_init)). Preserved for fidelity, not used "
            "as a model target."
        ),
        "stats": {k: v.result() for k, v in stats.items()},
    }
    (out_dir / "stats.json").write_text(json.dumps(summary, indent=2))
    return summary


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------


def verify(lmdb_path: Path, out_dir: Path, n_samples: int = 20, seed: int = 0) -> bool:
    """Round-trip random (sim, t) records from the LMDB against the memmaps.

    Tolerances are DERIVED from float16's resolution at each field's observed
    magnitude, not chosen to make the test pass. The assertion being made is
    "storage is lossless to within float16 precision", which is the strongest
    claim this format can support.

    For pressure that matters most: the field spans 98-290 bar, so centred
    values reach |99| bar, where the float16 step is 0.0625 and the worst
    rounding error is 0.03125 bar. That is 0.016% of the pressure range, about
    500x smaller than the ~8.6% relative error of the surrogate that consumes
    it, so it is irrelevant to any downstream result. Storing pressure as
    float32 to avoid it would double the file for no usable gain.
    """
    constants = np.load(out_dir / "constants.npy", mmap_mode="r")
    states = np.load(out_dir / "states.npy", mmap_mode="r")
    n_sims, n_steps = states.shape[0], states.shape[1]

    assert constants.shape == (n_sims, 2, C.GRID, C.GRID), constants.shape
    assert states.shape == (
        n_sims, n_steps, C.N_STATE_CHANNELS, C.GRID, C.GRID
    ), states.shape
    print(f"OK shapes: constants {constants.shape}, states {states.shape}")

    rng = np.random.default_rng(seed)
    env = open_env(lmdb_path)
    worst_p = worst_s = worst_poro = worst_perm = worst_aux = 0.0
    with env.begin() as txn:
        for _ in range(n_samples):
            sim = int(rng.integers(0, n_sims))
            t = int(rng.integers(1, n_steps + 1))

            poro, perm = get_constants(txn, sim)
            worst_poro = max(
                worst_poro,
                float(np.abs(constants[sim, C.CONST_POROSITY] - poro).max()),
            )
            worst_perm = max(
                worst_perm,
                float(
                    np.abs(
                        constants[sim, C.CONST_PERMEABILITY].astype(np.float64)
                        - np.asarray(perm, np.float64)
                    ).max()
                    / max(float(np.abs(perm).max()), 1e-30)
                ),
            )

            state = get_state(txn, sim, t)
            pres, sat, aux = state[0], state[1], state[2]
            got_p = restore_pressure(states[sim, t - 1, C.STATE_PRESSURE])
            got_s = np.asarray(states[sim, t - 1, C.STATE_SATURATION], np.float32)
            got_a = np.asarray(states[sim, t - 1, C.STATE_AUX], np.float32)
            worst_p = max(worst_p, float(np.abs(got_p - np.asarray(pres, np.float32)).max()))
            worst_s = max(worst_s, float(np.abs(got_s - np.asarray(sat, np.float32)).max()))
            worst_aux = max(
                worst_aux, float(np.abs(got_a - np.asarray(aux, np.float32)).max())
            )

        # t=0 must NOT be present in the converted array: confirm the stored
        # first slice is the t=1 record, not the pre-injection state.
        p0 = get_state(txn, 0, 0)[0]
        p1 = get_state(txn, 0, 1)[0]
        stored_first = restore_pressure(states[0, 0, C.STATE_PRESSURE])
        d0 = float(np.abs(stored_first - np.asarray(p0, np.float32)).max())
        d1 = float(np.abs(stored_first - np.asarray(p1, np.float32)).max())
    env.close()

    def f16_tolerance(peak_magnitude: float, margin: float = 1.5) -> float:
        """Worst-case float16 rounding error at a given magnitude: half the gap
        between adjacent representable values there."""
        step = float(np.spacing(np.float16(abs(peak_magnitude))))
        return step / 2 * margin

    peak_p = float(np.abs(states[:, :, C.STATE_PRESSURE]).max())
    peak_a = float(np.abs(states[:, :, C.STATE_AUX]).max())

    ok = True
    checks = [
        ("porosity   max|abs err|", worst_poro, 1e-6),
        ("permeability max rel err", worst_perm, 1e-6),
        ("pressure   max|abs err| (bar)", worst_p, f16_tolerance(peak_p)),
        ("saturation max|abs err|", worst_s, f16_tolerance(1.0)),
        ("aux        max|abs err|", worst_aux, f16_tolerance(peak_a)),
    ]
    for name, value, tol in checks:
        status = "OK  " if value <= tol else "FAIL"
        ok &= value <= tol
        print(f"{status} {name}: {value:.3e} (float16 limit {tol:.3e})")
    print(f"     pressure error is {100 * worst_p / max(peak_p, 1e-9):.4f}% of the "
          f"peak excursion; the surrogate's own error is ~8.6%")

    if d1 < d0:
        print(f"OK  timestep 0 excluded: stored[0] matches t=1 (d1={d1:.3e} < d0={d0:.3e})")
    else:
        print(f"FAIL stored[0] looks like t=0 (d0={d0:.3e}, d1={d1:.3e})")
        ok = False

    return bool(ok)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lmdb", type=Path, default=C.RAW_LMDB)
    ap.add_argument("--out", type=Path, default=C.DATA_DIR)
    ap.add_argument("--limit-sims", type=int, default=C.N_SIMS)
    ap.add_argument("--probe-only", action="store_true")
    ap.add_argument("--verify-only", action="store_true")
    args = ap.parse_args()

    if args.verify_only:
        return 0 if verify(args.lmdb, args.out) else 1

    print("Probing LMDB...")
    info = probe(args.lmdb)
    print(json.dumps(info, indent=2))
    if args.probe_only:
        return 0

    expected_entries = C.N_SIMS + C.N_SIMS * (C.N_TIMESTEPS + 1)
    if info["lmdb_entries"] != expected_entries:
        print(
            f"\nNote: {info['lmdb_entries']} entries, expected {expected_entries} "
            f"({C.N_SIMS} constants + {C.N_SIMS}x{C.N_TIMESTEPS + 1} states)."
        )

    print(f"\nConverting {args.limit_sims} simulations...")
    summary = convert(args.lmdb, args.out, n_sims=args.limit_sims)
    print("\nStatistics (physical units):")
    for name, s in summary["stats"].items():
        print(
            f"  {name:22s} mean {s['mean']:12.5g}  std {s['std']:12.5g}  "
            f"range [{s['min']:.5g}, {s['max']:.5g}]"
        )

    print("\nVerifying...")
    return 0 if verify(args.lmdb, args.out) else 1


if __name__ == "__main__":
    sys.exit(main())
