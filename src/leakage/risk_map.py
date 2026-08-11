"""Spatial leakage-risk map: "where would a fault be dangerous here?"

The rest of the pipeline scores ONE hypothesised fault at a time and returns a
number. That answers "is this fault dangerous?" but not "where?". This module
sweeps a fault across a grid of candidate positions, scores each with the
trained risk model, and returns a map — the leakage-probability heatmap the
original HyLeakAI proposal asked for.

What the map does and does not mean
-----------------------------------
Each cell answers: *if a fault existed at this location, how likely is elevated
leakage one horizon ahead?* It is a **conditional** risk surface, not a
prediction that faults exist anywhere in particular — the simulations contain
no faults at all (see docs/FINDINGS.md). Read it as "where would a fault
matter most", which is exactly the question site screening asks.

Fault properties are marginalised, not fixed
--------------------------------------------
Permeability, length, width and orientation are all unknown. Holding them
fixed would produce a map of one arbitrary fault, and a fixed orientation in
particular streaks the result along that direction. So each cell is scored over
`n_samples` random property draws and reduced (mean by default, or a high
quantile for a worst-case view). The reduction is stated in the output.

Cost is dominated by the per-position distance field, so the grid is coarser
than the 128x128 simulation grid by default; 32x32 renders in about a second
and is well below the scale at which the risk surface varies.
"""

from __future__ import annotations

import numpy as np

from src import config as C
from src.config import LEAKAGE, LeakageConfig
from src.leakage.features import (
    fault_features,
    geology_features,
    global_features,
    operational_features,
)
from src.leakage.labels import Fault, distance_to_fault_field, fault_cell_mask


def _sample_properties(rng, cfg: LeakageConfig, n: int) -> list[tuple]:
    """(length, width, permeability, orientation) draws shared by every cell.

    Shared deliberately: using the SAME property draws at every position means
    differences across the map come from location alone, not from sampling
    noise. Without this, a coarse grid looks speckled and the speckle is
    mistaken for structure.
    """
    lo, hi = np.log10(cfg.fault_perm_m2_range)
    return [
        (
            float(rng.uniform(*cfg.fault_length_m_range)),
            float(rng.uniform(*cfg.fault_width_m_range)),
            float(10 ** rng.uniform(lo, hi)),
            float(rng.uniform(0, np.pi)),
        )
        for _ in range(n)
    ]


def leakage_risk_map(
    pressure_bar: np.ndarray,
    saturation: np.ndarray,
    porosity: np.ndarray,
    permeability: np.ndarray,
    timestep: int,
    classifier,
    feature_names: list[str],
    grid: int = 32,
    n_samples: int = 8,
    reduce: str = "mean",
    prev_pressure_bar: np.ndarray | None = None,
    prev_saturation: np.ndarray | None = None,
    cfg: LeakageConfig = LEAKAGE,
    seed: int | None = None,
) -> dict:
    """Risk surface over candidate fault positions.

    `pressure_bar` / `saturation` are single-timestep 128x128 fields, from
    either the simulator or the U-Net. Returns the map plus the metadata needed
    to describe how it was produced.
    """
    if reduce not in ("mean", "max", "p90"):
        raise ValueError(f"reduce must be mean/max/p90, got {reduce!r}")

    rng = np.random.default_rng(cfg.rng_seed if seed is None else seed)
    props = _sample_properties(rng, cfg, n_samples)

    # Fault-independent parts: computed once, reused for every position.
    glob = global_features(pressure_bar, saturation, porosity,
                           prev_pressure_bar, prev_saturation, cfg)
    geo = geology_features(porosity, permeability)
    op = operational_features(timestep)
    base = {**glob, **geo, **op}

    # Candidate positions on a coarse grid spanning the domain.
    centres = (np.arange(grid) + 0.5) * (C.DOMAIN_M / grid)
    rows: list[list[float]] = []
    for y in centres:
        for x in centres:
            for length, width, perm, orient in props:
                fault = Fault(0, float(x), float(y), length, width, perm, orient)
                dist = distance_to_fault_field(fault)
                mask = fault_cell_mask(dist)
                ff = fault_features(pressure_bar, saturation, porosity,
                                    permeability, fault, dist, mask, cfg)
                ff.pop("_q_now_m3_s", None)
                row = {**base, **ff}
                rows.append([row[k] for k in feature_names])

    X = np.asarray(rows, dtype=np.float32)
    proba = classifier.predict_proba(X)[:, 1].reshape(grid, grid, n_samples)

    if reduce == "mean":
        risk = proba.mean(axis=2)
    elif reduce == "max":
        risk = proba.max(axis=2)
    else:
        risk = np.quantile(proba, 0.9, axis=2)

    return {
        "risk": risk,                      # (grid, grid), rows = y, cols = x
        "grid": grid,
        "n_samples": n_samples,
        "reduce": reduce,
        "extent_km": [0, C.DOMAIN_M / 1000, 0, C.DOMAIN_M / 1000],
        "cell_size_m": C.DOMAIN_M / grid,
        "timestep": timestep,
        "stage": "injection" if C.cycle_index(timestep) == 1 else "withdrawal",
        "risk_max": float(risk.max()),
        "risk_mean": float(risk.mean()),
        "hotspot_xy_m": _hotspot(risk, grid),
    }


def _hotspot(risk: np.ndarray, grid: int) -> tuple[float, float]:
    """Centre of the highest-risk cell, in metres from the domain corner."""
    j, i = np.unravel_index(int(np.argmax(risk)), risk.shape)
    step = C.DOMAIN_M / grid
    return (float((i + 0.5) * step), float((j + 0.5) * step))


def distance_from_well_km(x_m: float, y_m: float) -> float:
    return float(np.hypot(x_m - C.DOMAIN_M / 2, y_m - C.DOMAIN_M / 2) / 1000)
