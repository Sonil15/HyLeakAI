"""How much does the assumed caprock thickness change the leakage result?

Why thickness is swept here and not used as a Module 1 filter
------------------------------------------------------------
A tempting addition to the suitability score is a hard gate: reject any site
whose caprock is thinner than some minimum. It cannot be built on this dataset.
Caprock thickness is not a per-site measurement here — it is a single assumed
constant (`LeakageConfig.caprock_thickness_m`), identical for all 1,000
realisations, because the source simulations are 2D areal with sealed top and
bottom and carry no caprock geometry. A threshold test would compare one number
against itself a thousand times and pass or fail every site together. It would
look like a safety check and decide nothing.

Thickness does have a real effect, just in a different module: it is the
vertical path length `L_caprock` in the T3 Darcy flux,

    Q = (k_f * k_rg * A_f / mu) * dP / L_caprock

so flux is inversely proportional to it. Halving the caprock doubles the
predicted leak rate. That is worth measuring and reporting, and it is honest,
because it uses the assumption where it actually bites instead of dressing it
up as a screening criterion.

    python -m src.caprock_sensitivity
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from src import config as C
from src.data.lmdb_convert import restore_pressure
from src.leakage.labels import LEAKAGE, fault_leakage_flux, sample_faults

# Thin, our default, and two thicker cases. 50 m is what the project assumes;
# the others bracket it by a factor of two either way so the inverse
# relationship is visible rather than asserted.
THICKNESSES_M = (25.0, 50.0, 100.0, 200.0)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    states = np.load(root / "data" / "states.npy", mmap_mode="r")

    rng = np.random.default_rng(20260816)
    sim_ids = rng.choice(C.simulation_splits()["test"], 15, replace=False)

    # Every timestep, not a sampled few. The schedule is 6 steps per year --
    # three injection, three withdrawal -- so any set of timesteps that shares a
    # common factor with 6 lands on one phase of the cycle. A first attempt used
    # (12, 24, 36, 48, 60), all multiples of 6, which are all the withdrawal
    # trough: pressure is below initial there, the overpressure term clips to
    # zero, and every one of 4,000 flux evaluations came out exactly 0. That is
    # the same aliasing that made the forecast horizon wrong in FINDINGS section
    # 7. Sweeping all 60 steps removes the choice entirely.
    timesteps = tuple(range(1, C.N_TIMESTEPS + 1))
    faults = sample_faults(10, seed=7)

    rows = {t: [] for t in THICKNESSES_M}
    for sim in sim_ids:
        for step in timesteps:
            state = np.asarray(states[sim, step - 1], np.float32)
            # states.npy stores pressure CENTRED (stored = P_bar - P_INIT_BAR) to
            # keep float16 resolution usable. fault_leakage_flux expects absolute
            # bar, and silently produces zero flux for everything if given the
            # centred values, because the overpressure term clips at zero.
            pressure = restore_pressure(state[C.STATE_PRESSURE])
            saturation = state[C.STATE_SATURATION]
            for thickness in THICKNESSES_M:
                cfg = replace(LEAKAGE, caprock_thickness_m=thickness)
                for fault in faults:
                    q = fault_leakage_flux(pressure, saturation, fault, cfg)["q_fault_m3_s"]
                    rows[thickness].append(float(q))

    print(f"Sampled {len(sim_ids)} held-out simulations x {len(timesteps)} timesteps "
          f"x {len(faults)} faults = {len(rows[50.0]):,} flux evaluations per thickness\n")
    print(f"{'caprock m':>10} {'mean Q m3/s':>14} {'p95 Q':>14} {'max Q':>14} "
          f"{'non-zero %':>11} {'vs 50 m':>9}")

    base_mean = None
    summary = {}
    for thickness in THICKNESSES_M:
        q = np.array(rows[thickness])
        nonzero = q > 0
        mean = float(q[nonzero].mean()) if nonzero.any() else 0.0
        if thickness == 50.0:
            base_mean = mean
        summary[thickness] = {
            "mean_nonzero_q_m3_s": mean,
            "p95_q_m3_s": float(np.quantile(q, 0.95)),
            "max_q_m3_s": float(q.max()),
            "nonzero_fraction": float(nonzero.mean()),
        }

    for thickness in THICKNESSES_M:
        s = summary[thickness]
        ratio = s["mean_nonzero_q_m3_s"] / base_mean if base_mean else float("nan")
        print(f"{thickness:>10.0f} {s['mean_nonzero_q_m3_s']:>14.3e} {s['p95_q_m3_s']:>14.3e} "
              f"{s['max_q_m3_s']:>14.3e} {100 * s['nonzero_fraction']:>10.1f}% {ratio:>8.2f}x")

    # The relationship should be exactly inverse, because thickness enters the
    # flux only as a denominator. Checking it is a guard against the sweep
    # silently not varying what it claims to vary.
    expected = {t: 50.0 / t for t in THICKNESSES_M}
    observed = {t: summary[t]["mean_nonzero_q_m3_s"] / base_mean for t in THICKNESSES_M}
    worst = max(abs(observed[t] - expected[t]) for t in THICKNESSES_M)
    print(f"\nInverse-proportionality check: max |observed - expected| = {worst:.2e}"
          f"   {'OK' if worst < 1e-9 else 'UNEXPECTED'}")
    print("Thickness enters T3 only as the denominator, so this must be exact.")

    print("\nWhat this does NOT support: a Module 1 thickness filter. Thickness is one")
    print("assumed constant shared by all 1,000 realisations, so a threshold would")
    print("pass or fail every site together and rank nothing.")

    out = root / "outputs" / "caprock_sensitivity.json"
    out.write_text(json.dumps({
        "thicknesses_m": list(THICKNESSES_M),
        "assumed_default_m": LEAKAGE.caprock_thickness_m,
        "evaluations_per_thickness": len(rows[50.0]),
        "summary": {str(k): v for k, v in summary.items()},
        "relationship": "Q proportional to 1 / caprock_thickness_m (exact; it is the denominator)",
        "not_supported": ("A per-site thickness screening filter. Caprock thickness is a single "
                          "assumed constant across all 1,000 realisations in this dataset, so a "
                          "threshold test cannot discriminate between sites."),
    }, indent=2), encoding="utf-8")
    print(f"\nwrote {out.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
