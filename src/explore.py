"""Dataset validation and the T1 go/no-go decision.

Three questions this answers, all of which must be settled before any modelling:

1. Is the well actually at the grid centre? The paper says "a central well" and
   nothing more. We locate it empirically from the pressure field: during
   injection the maximum pressure sits at the well.

2. Does the H2 plume ever reach the open lateral boundary? This decides whether
   T1 (lateral containment loss) — the only leakage signal genuinely present in
   the data — carries any information at all. If it does not, T1 is dropped and
   we say so.

3. Do the fields behave as the paper describes? Pressure highest at the well
   during injection and lowest there during withdrawal, plume growing over
   cycles, pressure straddling the 197.2 bar initial value.

Usage:
    python -m src.explore
    python -m src.explore --figures       # also write plots to outputs/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src import config as C
from src.config import LEAKAGE
from src.data.lmdb_convert import restore_pressure
from src.leakage.labels import t1_viability_scan


def load_arrays(data_dir: Path):
    constants = np.load(data_dir / "constants.npy", mmap_mode="r")
    states = np.load(data_dir / "states.npy", mmap_mode="r")
    return constants, states


# --------------------------------------------------------------------------
# 1. Well location
# --------------------------------------------------------------------------


def validate_well_location(states, n_sims: int = 50) -> dict:
    """Locate the well from the pressure field rather than trusting a guess.

    During injection the well is the pressure maximum; during withdrawal it is
    the minimum. If both land on the grid centre, `config.WELL_BLOCK` is right
    and every well-relative feature (distance channel, P_well) is anchored
    correctly. If they do not, the distance channel — which the paper shows is
    worth 24 percentage points of pressure accuracy — would be centred on the
    wrong place.
    """
    inj_t = next(t for t in range(1, 10) if C.cycle_index(t) == 1)
    wd_t = next(t for t in range(1, 10) if C.cycle_index(t) == -1)

    inj_rc, wd_rc = [], []
    for sim in range(min(n_sims, states.shape[0])):
        p_inj = restore_pressure(states[sim, inj_t - 1, C.STATE_PRESSURE])
        p_wd = restore_pressure(states[sim, wd_t - 1, C.STATE_PRESSURE])
        inj_rc.append(np.unravel_index(np.argmax(p_inj), p_inj.shape))
        wd_rc.append(np.unravel_index(np.argmin(p_wd), p_wd.shape))

    inj_rc, wd_rc = np.array(inj_rc), np.array(wd_rc)
    med_inj = np.median(inj_rc, axis=0)
    med_wd = np.median(wd_rc, axis=0)
    dist_inj = float(np.hypot(*(med_inj - C.GRID_CENTER)))
    dist_wd = float(np.hypot(*(med_wd - C.GRID_CENTER)))
    agrees = dist_inj <= 1.5 and dist_wd <= 1.5

    print("\n1. WELL LOCATION")
    print(f"   injection  (t={inj_t}): pressure max at median cell "
          f"({med_inj[0]:.1f}, {med_inj[1]:.1f})")
    print(f"   withdrawal (t={wd_t}): pressure min at median cell "
          f"({med_wd[0]:.1f}, {med_wd[1]:.1f})")
    print(f"   grid centre is ({C.GRID_CENTER}, {C.GRID_CENTER}); "
          f"config.WELL_BLOCK = rows 63:65, cols 63:65")
    print(f"   {'OK  ' if agrees else 'FAIL'} well is at the grid centre "
          f"(offset {dist_inj:.2f} / {dist_wd:.2f} cells)")
    if agrees:
        print("   -> the distance-to-well channel and P_well are correctly anchored")
    else:
        print("   -> WELL IS NOT CENTRED. Fix config.WELL_BLOCK and the distance "
              "map before training; the paper attributes 24 points of pressure "
              "accuracy to that channel.")

    return {
        "injection_median_cell": med_inj.tolist(),
        "withdrawal_median_cell": med_wd.tolist(),
        "offset_cells_injection": dist_inj,
        "offset_cells_withdrawal": dist_wd,
        "well_is_centred": bool(agrees),
    }


# --------------------------------------------------------------------------
# 2. Cyclic behaviour
# --------------------------------------------------------------------------


def validate_cyclic_behaviour(states, n_sims: int = 50) -> dict:
    """Confirm our injection/withdrawal indexing matches the simulations.

    Paper section 5.8: during injection the highest pressure in the field is at
    the well; during withdrawal the well holds the lowest. If `cycle_index()`
    were off by even one timestep, the cyclic channel would be actively
    misleading and pressure accuracy would suffer badly.
    """
    n = min(n_sims, states.shape[0])
    well_is_max, well_is_min = [], []
    for sim in range(n):
        for t in range(1, C.N_TIMESTEPS + 1):
            p = restore_pressure(states[sim, t - 1, C.STATE_PRESSURE])
            at_well = float(p[C.WELL_BLOCK].mean())
            rank = float((p < at_well).mean())  # fraction of the field below the well
            (well_is_max if C.cycle_index(t) == 1 else well_is_min).append(rank)

    inj_rank = float(np.mean(well_is_max))
    wd_rank = float(np.mean(well_is_min))
    ok = inj_rank > 0.9 and wd_rank < 0.1

    print("\n2. CYCLIC INDEXING")
    print(f"   injection  steps: well pressure exceeds {inj_rank:.1%} of the field "
          f"(expect ~100%)")
    print(f"   withdrawal steps: well pressure exceeds {wd_rank:.1%} of the field "
          f"(expect ~0%)")
    print(f"   {'OK  ' if ok else 'FAIL'} config.cycle_index() matches the simulations")
    if not ok:
        print("   -> the +1/-1 cyclic channel is misaligned with the actual stages; "
              "check INJECTION_STEPS_PER_CYCLE and STEPS_PER_CYCLE")

    return {
        "injection_well_rank": inj_rank,
        "withdrawal_well_rank": wd_rank,
        "cyclic_index_correct": bool(ok),
    }


# --------------------------------------------------------------------------
# 3. Field summary
# --------------------------------------------------------------------------


def field_summary(constants, states, n_sims: int = 100) -> dict:
    n = min(n_sims, states.shape[0])
    p = restore_pressure(states[:n, :, C.STATE_PRESSURE])
    s = np.asarray(states[:n, :, C.STATE_SATURATION], np.float32)

    plume_cells = (s > LEAKAGE.plume_saturation_threshold).sum(axis=(2, 3))  # (n, T)
    per_step = plume_cells.mean(axis=0)
    max_radius_m = float(np.sqrt(per_step.max() / np.pi) * C.CELL_M)

    print(f"\n3. FIELD SUMMARY ({n} simulations)")
    print(f"   pressure   {p.min():.1f} to {p.max():.1f} bar "
          f"(initial {C.P_INIT_BAR} bar)")
    print(f"   saturation {s.min():.4g} to {s.max():.4f}")
    print(f"   plume area grows {per_step[0] * C.CELL_AREA_M2 / 1e6:.2f} -> "
          f"{per_step[-1] * C.CELL_AREA_M2 / 1e6:.2f} km^2 over 10 years")
    print(f"   equivalent plume radius at its largest: ~{max_radius_m:,.0f} m, "
          f"in a {C.DOMAIN_M:,.0f} m domain "
          f"({100 * max_radius_m / (C.DOMAIN_M / 2):.1f}% of the way to the boundary)")

    p_frac = LEAKAGE.frac_pressure_bar
    margin = (float(p.max()) - C.P_INIT_BAR) / (p_frac - C.P_INIT_BAR)
    print(f"\n   caprock check: peak pressure {p.max():.1f} bar vs assumed fracture "
          f"pressure {p_frac:.1f} bar")
    print(f"   peak T2 margin = {margin:.3f}"
          + ("  -> caprock IS exceeded somewhere" if margin > 1
             else "  -> caprock is NEVER exceeded at this gradient"))
    if margin <= 1:
        print("   -> T2's BINARY breach label would be identically zero. Use the "
              "continuous margin as a feature and do not report a binary caprock "
              "label; it is an artifact of an assumed fracture gradient.")
    print("   sensitivity of that conclusion to the assumed gradient:")
    for grad in LEAKAGE.frac_gradient_sweep:
        pf = C.RESERVOIR_DEPTH_M * grad
        m = (float(p.max()) - C.P_INIT_BAR) / (pf - C.P_INIT_BAR)
        print(f"      {grad:.2f} bar/m -> P_frac {pf:6.1f} bar, peak margin {m:5.3f}"
              f"{'  (exceeded)' if m > 1 else ''}")

    return {
        "n_sims_sampled": n,
        "pressure_min_bar": float(p.min()),
        "pressure_max_bar": float(p.max()),
        "saturation_max": float(s.max()),
        "plume_area_first_km2": float(per_step[0] * C.CELL_AREA_M2 / 1e6),
        "plume_area_last_km2": float(per_step[-1] * C.CELL_AREA_M2 / 1e6),
        "max_equivalent_plume_radius_m": max_radius_m,
        "domain_half_width_m": C.DOMAIN_M / 2,
        "peak_caprock_margin": margin,
        "caprock_exceeded_at_default_gradient": bool(margin > 1),
    }


# --------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=C.DATA_DIR)
    ap.add_argument("--out-dir", type=Path, default=C.OUTPUT_DIR)
    ap.add_argument("--scan-sims", type=int, default=None,
                    help="limit the T1 scan (default: all simulations)")
    args = ap.parse_args()

    constants, states = load_arrays(args.data_dir)
    print(f"constants {constants.shape} {constants.dtype}")
    print(f"states    {states.shape} {states.dtype}")

    report = {
        "well": validate_well_location(states),
        "cyclic": validate_cyclic_behaviour(states),
        "fields": field_summary(constants, states),
    }

    print("\n4. T1 GO / NO-GO — does the plume reach the open lateral boundary?")
    n = args.scan_sims or states.shape[0]
    t1 = t1_viability_scan(constants, states[:n], LEAKAGE, progress=True)
    report["t1"] = t1
    print(f"\n   simulations reaching the boundary: {t1['n_sims_with_breach']}/{t1['n_sims']}")
    print(f"   highest boundary saturation seen anywhere: "
          f"{t1['boundary_saturation_max_overall']:.6g} "
          f"(threshold {t1['threshold']})")
    print(f"\n   VERDICT: {t1['verdict']}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "explore_report.json").write_text(json.dumps(report, indent=2))
    print(f"\nWrote {args.out_dir / 'explore_report.json'}")

    blocking = [
        ("well not centred", not report["well"]["well_is_centred"]),
        ("cyclic index misaligned", not report["cyclic"]["cyclic_index_correct"]),
    ]
    failed = [name for name, bad in blocking if bad]
    if failed:
        print(f"\nBLOCKING ISSUES: {', '.join(failed)} — fix before training.")
        return 1
    print("\nNo blocking issues. Safe to train.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
