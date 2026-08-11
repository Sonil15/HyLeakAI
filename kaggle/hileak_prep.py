"""Fetch the Mao et al. UHS dataset from Zenodo and convert it to memmaps.

Zenodo serves ~2-3 MB/s per connection but honours HTTP range requests, so
several concurrent connections cut wall time substantially (measured 9.6 MB/s
at 10 connections versus 2.6 MB/s single-stream).

The raw 12.38 GB LMDB is deleted once conversion is verified, keeping peak disk
well inside a Kaggle session's budget.

Layout produced:
    constants.npy  (1000, 2, 128, 128)      float32   ~131 MB
    states.npy     (1000, 60, 2, 128, 128)  float16   ~3.9 GB
    stats.json
"""

from __future__ import annotations

import hashlib
import json
import pickle
import threading
import time
from pathlib import Path

import numpy as np
import requests

URL = "https://zenodo.org/records/14029514/files/data.mdb?download=1"
TOTAL_BYTES = 12_380_934_144
MD5 = "6bc841f02ad3f40c9a8ef8ad187edf43"      # from the Zenodo record

GRID, N_SIMS, N_TIMESTEPS = 128, 1000, 60
P_INIT_BAR = 197.2


# ---------------------------------------------------------------- download


def download(dest, connections: int = 16, chunk_mb: int = 64) -> None:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size == TOTAL_BYTES:
        print("Raw file already present, skipping download.")
        return

    cs = chunk_mb * 1024 * 1024
    chunks = [(s, min(s + cs, TOTAL_BYTES) - 1) for s in range(0, TOTAL_BYTES, cs)]
    with open(dest, "wb") as f:
        f.truncate(TOTAL_BYTES)          # preallocate so threads write disjoint offsets

    todo = list(range(len(chunks)))[::-1]
    lock = threading.Lock()
    done_bytes = [0]
    errors = []

    def worker():
        sess = requests.Session()
        while True:
            with lock:
                if not todo:
                    return
                i = todo.pop()
            a, b = chunks[i]
            written = 0
            try:
                r = sess.get(URL, headers={"Range": f"bytes={a}-{b}"},
                             stream=True, timeout=(15, 120))
                if r.status_code != 206:
                    raise RuntimeError(f"expected 206, got {r.status_code}")
                with open(dest, "r+b") as f:
                    f.seek(a)
                    for blk in r.iter_content(1 << 20):
                        if blk:
                            f.write(blk)
                            written += len(blk)
                if written != b - a + 1:
                    raise RuntimeError(f"short chunk {i}: {written}/{b - a + 1}")
                with lock:
                    done_bytes[0] += written
            except Exception as exc:
                with lock:
                    errors.append(f"chunk {i}: {exc}")
                    todo.append(i)          # requeue and retry
                time.sleep(2)

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(connections)]
    t0 = time.time()
    for t in threads:
        t.start()
    while any(t.is_alive() for t in threads):
        time.sleep(10)
        d = done_bytes[0]
        rate = d / max(time.time() - t0, 1e-9)
        print(f"  {d / 2**30:6.2f}/{TOTAL_BYTES / 2**30:.2f} GiB  "
              f"{rate / 2**20:5.1f} MiB/s  "
              f"ETA {(TOTAL_BYTES - d) / max(rate, 1) / 60:5.1f} min", flush=True)
    for t in threads:
        t.join()

    if errors:
        print(f"{len(errors)} transient error(s) were retried.")

    print("Verifying md5...")
    h = hashlib.md5()
    with open(dest, "rb") as f:
        for blk in iter(lambda: f.read(8 << 20), b""):
            h.update(blk)
    got = h.hexdigest()
    assert got == MD5, f"md5 mismatch: {got} != {MD5}"
    print(f"OK md5 {got}")


# ---------------------------------------------------------------- convert


class _Stats:
    """float64 accumulators, so statistics are exact regardless of storage dtype."""

    def __init__(self):
        self.n = 0
        self.s = 0.0
        self.q = 0.0
        self.lo = np.inf
        self.hi = -np.inf

    def add(self, a):
        a = np.asarray(a, np.float64)
        self.n += a.size
        self.s += float(a.sum())
        self.q += float(np.square(a).sum())
        self.lo = min(self.lo, float(a.min()))
        self.hi = max(self.hi, float(a.max()))

    def out(self):
        m = self.s / self.n
        return {"count": self.n, "mean": m,
                "std": float(np.sqrt(max(self.q / self.n - m * m, 0.0))),
                "min": self.lo, "max": self.hi}


def _to_np(o):
    """Values are torch tensors in this dataset; normalise to numpy."""
    return o.detach().cpu().numpy() if hasattr(o, "detach") else np.asarray(o)


def convert(lmdb_path, out_dir) -> dict:
    """Stream the LMDB into compact memmaps.

    Two precision decisions, both deliberate:

    * Constants stay float32. Permeability is in millidarcy here (1.03-738.8 mD)
      so float16 would suffice, but a future revision in m^2 (~1e-13) would
      silently flush to zero. 131 MB is not worth that risk.

    * Pressure is stored as (P_bar - 197.2), centred on the initial reservoir
      pressure. Raw ~200 bar in float16 resolves to only 0.125 bar; centred, the
      values sit where the step is ~0.06 bar. Uses a known constant, so no extra
      pass over 12 GB is needed.

    Timestep 0 is dropped: the paper and README both state it is the
    pre-injection state, identical across all 1,000 simulations.

    Only the two channels the paper predicts are kept. The records actually
    carry an undocumented third channel which we measured to be ~99% collinear
    with pressure (aux ~= -1.17e-4 * (P - P_init)); it is not a training target.
    """
    import lmdb

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if (out_dir / "states.npy").exists() and (out_dir / "stats.json").exists():
        print("Converted arrays already present, skipping conversion.")
        return json.loads((out_dir / "stats.json").read_text())

    env = lmdb.open(str(lmdb_path), subdir=False, readonly=True, lock=False,
                    readahead=False, max_readers=256)
    C = np.lib.format.open_memmap(out_dir / "constants.npy", mode="w+",
                                  dtype=np.float32, shape=(N_SIMS, 2, GRID, GRID))
    S = np.lib.format.open_memmap(out_dir / "states.npy", mode="w+", dtype=np.float16,
                                  shape=(N_SIMS, N_TIMESTEPS, 2, GRID, GRID))
    st = {k: _Stats() for k in ("porosity", "permeability", "log10_permeability",
                                "pressure_bar", "saturation")}

    t0 = time.monotonic()
    with env.begin() as txn:
        for sim in range(N_SIMS):
            poro, perm = [_to_np(a) for a in pickle.loads(txn.get(pickle.dumps(str(sim))))]
            C[sim, 0], C[sim, 1] = poro, perm
            st["porosity"].add(poro)
            st["permeability"].add(perm)
            st["log10_permeability"].add(np.log10(np.maximum(perm.astype(np.float64), 1e-30)))

            for t in range(1, N_TIMESTEPS + 1):
                v = pickle.loads(txn.get(pickle.dumps(f"{sim}-{t}")))
                p, s = _to_np(v[0]), _to_np(v[1])
                S[sim, t - 1, 0] = p.astype(np.float32) - P_INIT_BAR
                S[sim, t - 1, 1] = s
                st["pressure_bar"].add(p)
                st["saturation"].add(s)

            if (sim + 1) % 100 == 0:
                el = time.monotonic() - t0
                print(f"  {sim + 1}/{N_SIMS} sims  {el / 60:5.1f} min  "
                      f"ETA {(N_SIMS - sim - 1) / ((sim + 1) / el) / 60:5.1f} min", flush=True)

    env.close()
    C.flush()
    S.flush()
    summary = {
        "n_sims": N_SIMS, "n_timesteps": N_TIMESTEPS, "grid": GRID,
        "p_init_bar": P_INIT_BAR,
        "pressure_storage": "centred: stored = P_bar - P_INIT_BAR",
        "channels": {"constants": ["porosity", "permeability"],
                     "states": ["pressure_centred", "saturation"]},
        "stats": {k: v.out() for k, v in st.items()},
    }
    (out_dir / "stats.json").write_text(json.dumps(summary, indent=2))
    return summary


def verify(lmdb_path, out_dir, n_samples: int = 15, seed: int = 0) -> bool:
    """Round-trip random records against the LMDB.

    Tolerances are DERIVED from float16's resolution at each field's observed
    magnitude, not chosen to make the test pass. Pressure spans 82.7-293.8 bar,
    so centred values reach |114| bar where the float16 step is 0.125 — an error
    of ~0.03% of the excursion, roughly 300x below the surrogate's own ~8.6%.
    """
    import lmdb

    C = np.load(Path(out_dir) / "constants.npy", mmap_mode="r")
    S = np.load(Path(out_dir) / "states.npy", mmap_mode="r")
    assert C.shape == (N_SIMS, 2, GRID, GRID), C.shape
    assert S.shape == (N_SIMS, N_TIMESTEPS, 2, GRID, GRID), S.shape
    print(f"OK shapes: constants {C.shape}, states {S.shape}")

    env = lmdb.open(str(lmdb_path), subdir=False, readonly=True, lock=False)
    rng = np.random.default_rng(seed)
    worst_p = worst_s = 0.0
    with env.begin() as txn:
        for _ in range(n_samples):
            sim = int(rng.integers(0, N_SIMS))
            t = int(rng.integers(1, N_TIMESTEPS + 1))
            v = pickle.loads(txn.get(pickle.dumps(f"{sim}-{t}")))
            p, s = _to_np(v[0]), _to_np(v[1])
            got_p = np.asarray(S[sim, t - 1, 0], np.float32) + P_INIT_BAR
            got_s = np.asarray(S[sim, t - 1, 1], np.float32)
            worst_p = max(worst_p, float(np.abs(got_p - np.asarray(p, np.float32)).max()))
            worst_s = max(worst_s, float(np.abs(got_s - np.asarray(s, np.float32)).max()))

        # Confirm t=0 was excluded: stored[0] must match t=1, not t=0.
        p0 = _to_np(pickle.loads(txn.get(pickle.dumps("0-0")))[0])
        p1 = _to_np(pickle.loads(txn.get(pickle.dumps("0-1")))[0])
        first = np.asarray(S[0, 0, 0], np.float32) + P_INIT_BAR
        d0 = float(np.abs(first - np.asarray(p0, np.float32)).max())
        d1 = float(np.abs(first - np.asarray(p1, np.float32)).max())
    env.close()

    tol_p = float(np.spacing(np.float16(np.abs(S[:, :, 0]).max()))) / 2 * 1.5
    tol_s = float(np.spacing(np.float16(1.0))) / 2 * 1.5
    ok = worst_p <= tol_p and worst_s <= tol_s and d1 < d0
    print(f"{'OK  ' if worst_p <= tol_p else 'FAIL'} pressure   max|err| {worst_p:.3e} bar "
          f"(float16 limit {tol_p:.3e})")
    print(f"{'OK  ' if worst_s <= tol_s else 'FAIL'} saturation max|err| {worst_s:.3e} "
          f"(float16 limit {tol_s:.3e})")
    print(f"{'OK  ' if d1 < d0 else 'FAIL'} timestep 0 excluded "
          f"(d_to_t1 {d1:.3e} < d_to_t0 {d0:.3e})")
    assert ok, "conversion verification failed"
    return True
