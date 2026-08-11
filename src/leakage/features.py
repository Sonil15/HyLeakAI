"""Physics feature extraction: 128x128 fields -> a compact tabular row.

Two rules govern this module.

1. Never feed raw maps to XGBoost. Two 128x128 fields would be 32,768 columns,
   which destroys the interpretability that is the entire reason for using a
   gradient-boosted model here. We extract ~30 physically meaningful scalars
   instead.

2. The target is a FORECAST, not a description of the present. Each row carries
   features observed at timestep t and is labelled with the leakage flux at
   t + FORECAST_HORIZON (one full storage cycle, one year). Labelling a row with
   its own timestep's flux would let XGBoost rediscover the arithmetic of the
   label from `p_fault` and `s_fault` and score near-perfectly while predicting
   nothing. The forecast framing is what makes the number mean something.

Features can be built either from the simulator's own fields (for training) or
from U-Net predictions (for deployment, and to measure how much surrogate error
propagates into the risk estimate). `--source` selects which.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from src import config as C
from src.config import LeakageConfig, LEAKAGE
from src.leakage.labels import (  # noqa: F401  (corey_krg re-exported for callers)
    Fault,
    boundary_ring_mask,
    caprock_margin,
    corey_krg,
    distance_to_fault_field,
    fault_cell_mask,
    fault_leakage_flux,
    h2_pore_volume,
    sample_faults,
)

# One storage cycle = 6 timesteps of 2 months = 1 year.
FORECAST_HORIZON = C.STEPS_PER_CYCLE

# Horizons emitted in a single pass, in timesteps (2 months each).
#
# The choice matters more than any hyperparameter, because the T3 label is a
# closed-form function of quantities that appear in the feature vector
# (fault permeability, area, and the pressure and saturation at the fault).
# At the same timestep the label is pure algebra. The ONLY genuine learning
# content is how the fields evolve between t and t+h, so the horizon decides
# how much of a task is left at all:
#
#     1   two months, part-cycle
#     3   half a cycle -> injection and withdrawal swap
#     6   one full cycle -> SAME phase, fields nearly repeat (near-trivial)
#    12   two cycles
#    30   five years -> genuine early warning, and where persistence should fail
#
# Emitting them together costs one pass, and lets the sweep in train_xgb show
# where the model stops being a restatement of the label formula.
FORECAST_HORIZONS = (1, 3, 6, 12, 30)


# --------------------------------------------------------------------------
# Per-timestep, fault-independent features
# --------------------------------------------------------------------------


def global_features(
    pressure_bar: np.ndarray,
    saturation: np.ndarray,
    porosity: np.ndarray,
    prev_pressure_bar: np.ndarray | None,
    prev_saturation: np.ndarray | None,
    cfg: LeakageConfig = LEAKAGE,
    ring: np.ndarray | None = None,
) -> dict[str, float]:
    """Pressure and plume descriptors that do not depend on any fault."""
    dt_years = C.MONTHS_PER_STEP / 12.0

    # -- pressure --
    gy, gx = np.gradient(pressure_bar.astype(np.float64), C.CELL_M)
    feats = {
        "p_max_bar": float(pressure_bar.max()),
        "p_min_bar": float(pressure_bar.min()),
        "p_mean_bar": float(pressure_bar.mean()),
        "p_p95_bar": float(np.percentile(pressure_bar, 95)),
        "p_well_bar": float(pressure_bar[C.WELL_BLOCK].mean()),
        "delta_p_bar": float(pressure_bar.max() - C.P_INIT_BAR),
        "p_grad_max_bar_per_m": float(np.hypot(gy, gx).max()),
    }
    feats["dp_dt_bar_per_year"] = (
        float((pressure_bar.mean() - prev_pressure_bar.mean()) / dt_years)
        if prev_pressure_bar is not None
        else 0.0
    )

    # -- plume --
    plume = saturation > cfg.plume_saturation_threshold
    hpv = h2_pore_volume(porosity, saturation)
    n_plume = int(plume.sum())
    feats.update(
        {
            "s_max": float(saturation.max()),
            "s_mean": float(saturation.mean()),
            "hpv_total_m3": float(hpv.sum()),
            "plume_area_m2": n_plume * C.CELL_AREA_M2,
            "plume_cell_count": float(n_plume),
        }
    )

    if n_plume:
        yy, xx = np.nonzero(plume)
        cy, cx = yy.mean(), xx.mean()
        feats["plume_centroid_offset_m"] = float(
            np.hypot(cy - C.GRID_CENTER, cx - C.GRID_CENTER) * C.CELL_M
        )
        feats["plume_max_radius_m"] = float(
            np.hypot(yy - C.GRID_CENTER, xx - C.GRID_CENTER).max() * C.CELL_M
        )
    else:
        feats["plume_centroid_offset_m"] = 0.0
        feats["plume_max_radius_m"] = 0.0

    if prev_saturation is not None:
        prev_plume = prev_saturation > cfg.plume_saturation_threshold
        if prev_plume.any():
            pyy, pxx = np.nonzero(prev_plume)
            prev_radius = np.hypot(pyy - C.GRID_CENTER, pxx - C.GRID_CENTER).max() * C.CELL_M
        else:
            prev_radius = 0.0
        feats["plume_front_speed_m_per_year"] = float(
            (feats["plume_max_radius_m"] - prev_radius) / dt_years
        )
        feats["hpv_rate_m3_per_year"] = float(
            (hpv.sum() - h2_pore_volume(porosity, prev_saturation).sum()) / dt_years
        )
    else:
        feats["plume_front_speed_m_per_year"] = 0.0
        feats["hpv_rate_m3_per_year"] = 0.0

    # -- T1 and T2, carried as features as well as secondary labels --
    ring = boundary_ring_mask() if ring is None else ring
    feats["boundary_saturation_max"] = float(saturation[ring].max())
    feats["boundary_hpv_fraction"] = float(
        hpv[ring].sum() / max(hpv.sum(), 1e-30)
    )
    feats["caprock_margin"] = caprock_margin(pressure_bar, cfg)["caprock_margin"]

    return feats


def geology_features(porosity: np.ndarray, permeability: np.ndarray) -> dict[str, float]:
    """Static descriptors of the realisation. Constant across a simulation's 60
    timesteps, but XGBoost has no notion of a simulation, so each row carries
    its own copy."""
    with np.errstate(divide="ignore"):
        logk = np.log10(np.maximum(permeability.astype(np.float64), 1e-30))
    return {
        "poro_mean": float(porosity.mean()),
        "poro_std": float(porosity.std()),
        "logk_mean": float(logk.mean()),
        "logk_std": float(logk.std()),
    }


def fault_features(
    pressure_bar: np.ndarray,
    saturation: np.ndarray,
    porosity: np.ndarray,
    permeability: np.ndarray,
    fault: Fault,
    distance_field: np.ndarray,
    mask: np.ndarray,
    cfg: LeakageConfig = LEAKAGE,
) -> dict[str, float]:
    """Fault-conditional features, plus the fault's own sampled properties.

    The sampled properties matter: without `fault_perm_m2` in the feature set
    the model cannot possibly separate "large plume on a sealed fault" from
    "small plume on an open one", and SHAP would attribute the difference to
    whatever proxy happens to correlate with it.
    """
    flux = fault_leakage_flux(
        pressure_bar, saturation, fault, cfg,
        fault_mask=mask, distance_field=distance_field,
    )
    with np.errstate(divide="ignore"):
        logk_fault = float(
            np.log10(np.maximum(permeability[mask].astype(np.float64), 1e-30)).mean()
        )
    d = flux["distance_plume_to_fault_m"]
    return {
        "fault_p_bar": flux["p_fault_bar"],
        "fault_s": flux["s_fault"],
        "fault_krg": flux["krg_fault"],
        "fault_overpressure_bar": flux["overpressure_bar"],
        "fault_delta_p_bar": flux["p_fault_bar"] - C.P_INIT_BAR,
        # Faults with no plume anywhere get the domain diagonal, a finite value
        # meaning "as far as it is possible to be", rather than NaN.
        "distance_plume_to_fault_m": float(d) if np.isfinite(d) else C.DOMAIN_M * 1.5,
        "fault_poro": float(porosity[mask].mean()),
        "fault_logk": logk_fault,
        "fault_log10_perm_m2": float(np.log10(fault.permeability_m2)),
        "fault_length_m": fault.length_m,
        "fault_width_m": fault.width_m,
        "fault_area_m2": fault.area_m2,
        "fault_radius_from_well_m": float(
            np.hypot(fault.x_m - C.DOMAIN_M / 2, fault.y_m - C.DOMAIN_M / 2)
        ),
        "_q_now_m3_s": flux["q_fault_m3_s"],  # label source; dropped from X
    }


def operational_features(t: int) -> dict[str, float]:
    return {
        "timestep": float(t),
        "cycle_number": float(C.cycle_number(t)),
        "cycle_index": float(C.cycle_index(t)),
        "step_in_cycle": float((t - 1) % C.STEPS_PER_CYCLE),
    }


# --------------------------------------------------------------------------
# Table construction
# --------------------------------------------------------------------------

# Columns that are labels or identifiers, never model inputs.
ID_COLUMNS = ("sim_id", "fault_id", "timestep_observed")
# Leaks the answer: the same physical quantity at the observed timestep. Kept in
# the table because the persistence baseline needs it, but never a model input.
EXCLUDED_FROM_X = ("_q_now_m3_s",)

LABEL_PREFIXES = ("q_future_h", "log_q_future_h", "leak_future_h")


def label_columns(h: int) -> dict[str, str]:
    return {"q": f"q_future_h{h}", "log_q": f"log_q_future_h{h}",
            "leak": f"leak_future_h{h}"}


def feature_columns(all_columns: list[str]) -> list[str]:
    """Model inputs: everything that is not an identifier, a label at ANY
    horizon, or the present-time flux."""
    drop = set(ID_COLUMNS) | set(EXCLUDED_FROM_X)
    return [
        c for c in all_columns
        if c not in drop and not any(c.startswith(p) for p in LABEL_PREFIXES)
    ]


def build_feature_table(
    constants: np.ndarray,
    states_pressure_bar,
    states_saturation,
    sim_ids: list[int],
    cfg: LeakageConfig = LEAKAGE,
    horizons: tuple[int, ...] = FORECAST_HORIZONS,
    n_faults: int | None = None,
    progress_every: int = 25,
    label_pressure_bar=None,
    label_saturation=None,
) -> tuple[np.ndarray, list[str]]:
    """Build the tabular dataset.

    `states_pressure_bar` and `states_saturation` are callables
    `(sim) -> (T, 128, 128)` in physical units, so the same code path serves
    both simulator fields and U-Net predictions.

    `label_pressure_bar` / `label_saturation` optionally supply a DIFFERENT
    field source for computing the labels. This matters:

      * Both from the simulator -> the training table.
      * Features from the U-Net, labels from the SIMULATOR -> the deployment
        question, "using surrogate-predicted fields, can we predict the TRUE
        leakage?" This is what measures how much surrogate error propagates
        into the risk estimate.

    Taking labels from the U-Net as well would only measure the surrogate's
    self-consistency: the errors would cancel and the score would look fine
    however wrong the fields were. Defaults to the feature source.

    Returns a float32 array plus its column names.
    """
    label_pressure_bar = label_pressure_bar or states_pressure_bar
    label_saturation = label_saturation or states_saturation
    labels_from_same_source = (
        label_pressure_bar is states_pressure_bar
        and label_saturation is states_saturation
    )
    n_faults = n_faults if n_faults is not None else cfg.n_faults_per_sim
    ring = boundary_ring_mask(C.GRID, cfg.boundary_ring_cells)

    rows: list[list[float]] = []
    columns: list[str] | None = None

    for n_done, sim in enumerate(sim_ids, start=1):
        poro = np.asarray(constants[sim, C.CONST_POROSITY], np.float32)
        perm = np.asarray(constants[sim, C.CONST_PERMEABILITY], np.float32)
        pressure = np.asarray(states_pressure_bar(sim), np.float32)   # (T, H, W)
        saturation = np.asarray(states_saturation(sim), np.float32)
        n_steps = pressure.shape[0]
        if labels_from_same_source:
            label_p, label_s = pressure, saturation
        else:
            label_p = np.asarray(label_pressure_bar(sim), np.float32)
            label_s = np.asarray(label_saturation(sim), np.float32)

        geo = geology_features(poro, perm)

        # Fault-independent features, once per timestep.
        glob = [
            global_features(
                pressure[i], saturation[i], poro,
                pressure[i - 1] if i > 0 else None,
                saturation[i - 1] if i > 0 else None,
                cfg, ring,
            )
            for i in range(n_steps)
        ]

        # Per-simulation fault realisations, seeded by sim so the whole table is
        # reproducible from the config alone.
        faults = sample_faults(n_faults, cfg, seed=cfg.rng_seed + sim)

        for fault in faults:
            dist = distance_to_fault_field(fault)
            mask = fault_cell_mask(dist)

            per_t = [
                fault_features(
                    pressure[i], saturation[i], poro, perm, fault, dist, mask, cfg
                )
                for i in range(n_steps)
            ]
            # Labels come from their own field source, which may differ.
            if labels_from_same_source:
                label_q = [p["_q_now_m3_s"] for p in per_t]
            else:
                label_q = [
                    fault_leakage_flux(
                        label_p[i], label_s[i], fault, cfg,
                        fault_mask=mask, distance_field=dist,
                    )["q_fault_m3_s"]
                    for i in range(n_steps)
                ]

            shortest = min(horizons)
            for i in range(n_steps - shortest):
                t = i + 1                      # timesteps are 1-based
                row = {
                    "sim_id": float(sim),
                    "fault_id": float(fault.fault_id),
                    "timestep_observed": float(t),
                    **glob[i],
                    **geo,
                    **per_t[i],
                    **operational_features(t),
                }
                # A label per horizon; NaN where t+h runs past the simulation.
                # train_xgb drops those rows for the horizon it selects, so each
                # horizon uses every row it legitimately can.
                for h in horizons:
                    j = i + h
                    names = label_columns(h)
                    if j < n_steps:
                        q = label_q[j]
                        row[names["q"]] = q
                        row[names["log_q"]] = float(np.log10(q + 1e-12))
                    else:
                        row[names["q"]] = np.nan
                        row[names["log_q"]] = np.nan
                    row[names["leak"]] = np.nan   # thresholded once the table exists

                if columns is None:
                    columns = list(row.keys())
                rows.append([row[c] for c in columns])

        if progress_every and n_done % progress_every == 0:
            print(
                f"  {n_done}/{len(sim_ids)} simulations, {len(rows):,} rows",
                flush=True,
            )

    table = np.asarray(rows, dtype=np.float32)
    return table, (columns or [])


def apply_leak_threshold(
    table: np.ndarray,
    columns: list[str],
    quantile: float = 0.90,
    horizons: tuple[int, ...] = FORECAST_HORIZONS,
) -> tuple[np.ndarray, dict[int, float]]:
    """Binarise the forecast target, once per horizon.

    The threshold is a quantile of the NON-ZERO fluxes rather than an absolute
    m^3/s value, because the absolute scale is set by the assumed fault
    permeability and caprock thickness and so carries no independent meaning.
    Reported as a concrete flux alongside every result.

    Each horizon gets its OWN threshold from its own flux distribution, so the
    positive-class rate stays comparable across the sweep and differences in
    score reflect difficulty rather than shifting class balance.
    """
    thresholds: dict[int, float] = {}
    for h in horizons:
        names = label_columns(h)
        qi, li = columns.index(names["q"]), columns.index(names["leak"])
        q = table[:, qi]
        valid = np.isfinite(q)
        positive = q[valid & (q > 0)]
        thr = float(np.quantile(positive, quantile)) if positive.size else 0.0
        thresholds[h] = thr
        table[:, li] = np.where(valid, (q > thr).astype(np.float32), np.nan)
    return table, thresholds


def save_table(path: Path, table: np.ndarray, columns: list[str], meta: dict) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, table)
    path.with_suffix(".columns.json").write_text(
        json.dumps({"columns": columns, "meta": meta}, indent=2)
    )


def load_table(path: Path) -> tuple[np.ndarray, list[str], dict]:
    import json

    table = np.load(path)
    payload = json.loads(Path(path).with_suffix(".columns.json").read_text())
    return table, payload["columns"], payload.get("meta", {})
