"""Leakage targets derived from the UHS simulations.

READ THIS BEFORE USING ANY NUMBER OUT OF THIS MODULE.

The Mao et al. dataset contains porosity, permeability, pressure and H2
saturation. It contains no faults, no caprock properties, no fluxes and no
leakage labels. We have no reservoir simulator, so we cannot produce true
simulated leakage flux. Rather than invent one and call it ground truth, this
module produces three targets and labels each one for what it actually is:

  T1  lateral containment loss   REAL SIGNAL IN THE DATA
      The paper states the simulation has "no-flow boundaries at the top and
      bottom, and outflow boundaries on the sides". H2 that reaches the lateral
      boundary genuinely leaves the model domain. Nothing is assumed here
      beyond where we draw the boundary ring.

  T2  caprock breach margin      PHYSICS CRITERION, NOT A FLUX
      Pressure-based screening of the kind used routinely in CO2 and H2 storage
      risk assessment, applied to the simulated pressure field. It says
      "pressure exceeded a fracture threshold", not "hydrogen leaked". The
      caprock is a sealed no-flow boundary in these simulations, so no vertical
      leakage was ever simulated.

  T3  fault conduit leakage      SEMI-ANALYTICAL MODEL, DERIVED LABEL
      Darcy flux through a HYPOTHETICAL fault overlaid on the simulated
      pressure and saturation fields. This is the primary XGBoost target
      because it is the only one where fault features are causally connected to
      the label, which SHAP attributions require in order to mean anything.

Why overlaying a fault is not circular: the fault is not an input to the U-Net.
The U-Net predicts the flow field from geology alone; the fault is introduced
afterwards. The system therefore answers "given this fault hypothesis, how bad
is it?", which supports Monte-Carlo over unknown fault properties in
milliseconds. That is a real capability, not a restatement of the simulator.

Every assumed constant lives in `config.LeakageConfig` and is swept in
`sensitivity.py`. None of them come from the dataset.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np

from src import config as C
from src.config import LeakageConfig, LEAKAGE


# ==========================================================================
# T1 — Lateral containment loss  (the one real signal)
# ==========================================================================


def boundary_ring_mask(grid: int = C.GRID, ring_cells: int = None) -> np.ndarray:
    """Cells within `ring_cells` of the open lateral boundary."""
    ring_cells = ring_cells if ring_cells is not None else LEAKAGE.boundary_ring_cells
    mask = np.zeros((grid, grid), dtype=bool)
    mask[:ring_cells, :] = True
    mask[-ring_cells:, :] = True
    mask[:, :ring_cells] = True
    mask[:, -ring_cells:] = True
    return mask


def h2_pore_volume(porosity: np.ndarray, saturation: np.ndarray) -> np.ndarray:
    """H2 pore volume per cell, m^3.

    Deliberately a pore volume rather than a mass: converting to mass needs an
    H2 density from a real-gas equation of state at a reservoir temperature the
    paper never states. Pore volume is exact given the data; mass would smuggle
    in another assumption for no analytical gain.
    """
    return porosity * saturation * C.CELL_VOLUME_M3


def lateral_containment(
    porosity: np.ndarray,
    saturation: np.ndarray,
    cfg: LeakageConfig = LEAKAGE,
    ring: np.ndarray | None = None,
) -> dict:
    """T1: how much H2 has migrated into the open-boundary ring."""
    ring = boundary_ring_mask(saturation.shape[-1], cfg.boundary_ring_cells) if ring is None else ring
    hpv = h2_pore_volume(porosity, saturation)
    total = float(hpv.sum())
    in_ring = float(hpv[ring].sum())
    s_ring_max = float(saturation[ring].max())
    return {
        "hpv_total_m3": total,
        "hpv_ring_m3": in_ring,
        "hpv_ring_fraction": in_ring / total if total > 0 else 0.0,
        "boundary_saturation_max": s_ring_max,
        "lateral_breach": bool(s_ring_max > cfg.plume_saturation_threshold),
    }


def t1_viability_scan(
    constants: np.ndarray,
    states: np.ndarray,
    cfg: LeakageConfig = LEAKAGE,
    progress: bool = True,
) -> dict:
    """GO / NO-GO for T1.

    With one central well in a 7,680 m domain, the plume may never reach the
    outflow boundary within 10 years. If it does not, T1 is identically zero
    everywhere and is useless as a label. This must be run and reported before
    T1 is used for anything; the honest outcome may well be "T1 is dropped".
    """
    from src.data.lmdb_convert import restore_pressure  # noqa: F401  (kept for symmetry)

    n_sims, n_steps = states.shape[0], states.shape[1]
    ring = boundary_ring_mask(states.shape[-1], cfg.boundary_ring_cells)

    per_sim_max = np.zeros(n_sims, dtype=np.float64)
    max_ring_fraction = 0.0
    first_breach_step = np.full(n_sims, -1, dtype=np.int32)

    for sim in range(n_sims):
        poro = np.asarray(constants[sim, C.CONST_POROSITY], np.float32)
        sat = np.asarray(states[sim, :, C.STATE_SATURATION], np.float32)  # (T, H, W)
        ring_sat = sat[:, ring]                      # (T, n_ring_cells)
        step_max = ring_sat.max(axis=1)              # (T,)
        per_sim_max[sim] = float(step_max.max())

        breached = np.nonzero(step_max > cfg.plume_saturation_threshold)[0]
        if breached.size:
            first_breach_step[sim] = int(breached[0]) + 1  # timesteps are 1-based
            hpv = poro[None] * sat * C.CELL_VOLUME_M3
            frac = hpv[:, ring].sum(axis=1) / np.maximum(
                hpv.reshape(n_steps, -1).sum(axis=1), 1e-30
            )
            max_ring_fraction = max(max_ring_fraction, float(frac.max()))

        if progress and (sim + 1) % 100 == 0:
            print(f"  scanned {sim + 1}/{n_sims} simulations", flush=True)

    n_breach = int((first_breach_step > 0).sum())
    viable = n_breach >= max(10, int(0.01 * n_sims))
    return {
        "n_sims": n_sims,
        "threshold": cfg.plume_saturation_threshold,
        "ring_cells": cfg.boundary_ring_cells,
        "n_sims_with_breach": n_breach,
        "breach_rate": n_breach / n_sims,
        "boundary_saturation_max_overall": float(per_sim_max.max()),
        "boundary_saturation_mean_of_sim_max": float(per_sim_max.mean()),
        "max_ring_hpv_fraction": max_ring_fraction,
        "earliest_breach_timestep": (
            int(first_breach_step[first_breach_step > 0].min()) if n_breach else None
        ),
        "T1_VIABLE": bool(viable),
        "verdict": (
            f"T1 usable: {n_breach}/{n_sims} simulations reach the open boundary."
            if viable
            else (
                f"T1 NOT usable: only {n_breach}/{n_sims} simulations show boundary "
                f"saturation above {cfg.plume_saturation_threshold}. The plume stays "
                f"well inside the 7,680 m domain, so lateral containment loss carries "
                f"no signal. Drop T1 and say so; T2 and T3 carry the project."
            )
        ),
    }


# ==========================================================================
# T2 — Caprock breach margin  (criterion, not a flux)
# ==========================================================================


def caprock_margin(pressure_bar: np.ndarray, cfg: LeakageConfig = LEAKAGE) -> dict:
    """T2: how close the field is to the assumed caprock fracture pressure.

    margin = (P_max - P_initial) / (P_frac - P_initial)

    0 means "at the initial reservoir pressure", 1 means "at the fracture
    pressure". P_frac comes from an ASSUMED depth and fracture gradient; sweep
    `frac_gradient_bar_per_m` before reporting anything from this.
    """
    p_frac = cfg.frac_pressure_bar
    p_max = float(np.max(pressure_bar))
    denom = p_frac - C.P_INIT_BAR
    margin = (p_max - C.P_INIT_BAR) / denom if denom > 0 else np.inf
    return {
        "p_max_bar": p_max,
        "p_frac_bar": p_frac,
        "caprock_margin": margin,
        "caprock_exceeded": bool(margin > 1.0),
    }


# ==========================================================================
# T3 — Semi-analytical fault conduit leakage  (primary target)
# ==========================================================================


@dataclass
class Fault:
    """A hypothetical vertical fault cutting the caprock, as a surface trace."""

    fault_id: int
    x_m: float           # trace centre, metres from the domain's lower-left corner
    y_m: float
    length_m: float
    width_m: float       # damage-zone width; sets the conduit's cross-section
    permeability_m2: float
    orientation_rad: float

    @property
    def area_m2(self) -> float:
        """Conduit cross-section presented to vertical flow."""
        return self.length_m * self.width_m

    def as_dict(self) -> dict:
        d = asdict(self)
        d["area_m2"] = self.area_m2
        return d


def sample_faults(
    n: int, cfg: LeakageConfig = LEAKAGE, seed: int | None = None
) -> list[Fault]:
    """Monte-Carlo fault realisations.

    Permeability is log-uniform because it spans three orders of magnitude
    (~1 to ~1000 mD) and a uniform draw would put almost all mass at the
    high end. Faults are placed on a radial band around the central well so the
    sample spans "cutting straight through the plume" to "well outside it" —
    without that spread, plume-to-fault distance would carry no information and
    the whole feature set would collapse.
    """
    rng = np.random.default_rng(cfg.rng_seed if seed is None else seed)
    faults = []
    for i in range(n):
        radius = rng.uniform(*cfg.fault_radius_m_range)
        bearing = rng.uniform(0, 2 * np.pi)
        centre = C.DOMAIN_M / 2.0
        faults.append(
            Fault(
                fault_id=i,
                x_m=centre + radius * np.cos(bearing),
                y_m=centre + radius * np.sin(bearing),
                length_m=rng.uniform(*cfg.fault_length_m_range),
                width_m=rng.uniform(*cfg.fault_width_m_range),
                permeability_m2=float(
                    10 ** rng.uniform(*np.log10(cfg.fault_perm_m2_range))
                ),
                orientation_rad=rng.uniform(0, np.pi),
            )
        )
    return faults


def distance_to_fault_field(fault: Fault, grid: int = C.GRID) -> np.ndarray:
    """Distance in metres from every cell centre to the fault trace segment.

    Standard point-to-segment distance, vectorised over the grid. Computed once
    per fault and reused across all 60 timesteps.
    """
    coords = (np.arange(grid) + 0.5) * C.CELL_M
    yy, xx = np.meshgrid(coords, coords, indexing="ij")

    half = fault.length_m / 2.0
    dx, dy = np.cos(fault.orientation_rad), np.sin(fault.orientation_rad)
    ax, ay = fault.x_m - half * dx, fault.y_m - half * dy
    bx, by = fault.x_m + half * dx, fault.y_m + half * dy

    vx, vy = bx - ax, by - ay
    seg_len_sq = vx * vx + vy * vy
    if seg_len_sq <= 0:
        return np.hypot(xx - ax, yy - ay)

    t = np.clip(((xx - ax) * vx + (yy - ay) * vy) / seg_len_sq, 0.0, 1.0)
    return np.hypot(xx - (ax + t * vx), yy - (ay + t * vy))


def fault_cell_mask(distance_field: np.ndarray) -> np.ndarray:
    """Cells the trace passes through. The 0.75-cell radius keeps the rasterised
    trace connected at any orientation."""
    mask = distance_field <= C.CELL_M * 0.75
    if not mask.any():  # a very short trace can miss every cell centre
        mask = distance_field == distance_field.min()
    return mask


def corey_krg(saturation, cfg: LeakageConfig = LEAKAGE):
    """Corey gas relative permeability.

    k_rg = ((S_g - S_gr) / (1 - S_wr - S_gr)) ** n_g, clipped to [0, 1].

    This is what makes the label physically sensible rather than a pressure
    proxy: below residual gas saturation the H2 is immobile and cannot leak at
    all, no matter how high the pressure. Without it, a fault far from the plume
    would still "leak" whenever the field pressurised.
    """
    sg = np.asarray(saturation, dtype=np.float64)
    denom = 1.0 - cfg.corey_swr - cfg.corey_sgr
    if denom <= 0:
        raise ValueError("corey_swr + corey_sgr must be < 1")
    se = np.clip((sg - cfg.corey_sgr) / denom, 0.0, 1.0)
    return se**cfg.corey_ng


def fault_leakage_flux(
    pressure_bar: np.ndarray,
    saturation: np.ndarray,
    fault: Fault,
    cfg: LeakageConfig = LEAKAGE,
    fault_mask: np.ndarray | None = None,
    distance_field: np.ndarray | None = None,
) -> dict:
    """T3: Darcy flux of H2 up a hypothetical fault, m^3/s.

        Q = (k_f * k_rg * A_f / mu_H2) * dP / L_caprock

    The driving force `dP` is the overpressure above the initial reservoir
    pressure, which we take to be hydrostatic. Two consequences, both intended:

      * During withdrawal the field drops below its initial pressure, dP is
        clipped to zero and no upward leakage occurs. Fluid would flow the other
        way, which is not leakage.
      * Leakage requires BOTH overpressure and mobile H2 at the fault. A
        pressurised fault with no plume on it leaks nothing.

    Units: m^2 * m^2 * Pa / (Pa.s * m) = m^3/s.
    """
    if distance_field is None:
        distance_field = distance_to_fault_field(fault, pressure_bar.shape[-1])
    if fault_mask is None:
        fault_mask = fault_cell_mask(distance_field)

    p_fault = float(np.mean(pressure_bar[fault_mask]))
    s_fault = float(np.mean(saturation[fault_mask]))
    krg = float(corey_krg(s_fault, cfg))

    overpressure_pa = max(p_fault - C.P_INIT_BAR, 0.0) * C.BAR_TO_PA
    q = (
        fault.permeability_m2
        * krg
        * fault.area_m2
        / cfg.h2_viscosity_pa_s
        * overpressure_pa
        / cfg.caprock_thickness_m
    )

    plume = saturation > cfg.plume_saturation_threshold
    d_plume = float(distance_field[plume].min()) if plume.any() else np.nan

    return {
        "q_fault_m3_s": q,
        "p_fault_bar": p_fault,
        "s_fault": s_fault,
        "krg_fault": krg,
        "overpressure_bar": overpressure_pa / C.BAR_TO_PA,
        "distance_plume_to_fault_m": d_plume,
        "fault_perm_m2": fault.permeability_m2,
        "fault_area_m2": fault.area_m2,
        "fault_length_m": fault.length_m,
    }


# ==========================================================================
# Self-checks
# ==========================================================================


def check_monotonicity(cfg: LeakageConfig = LEAKAGE) -> bool:
    """The label must respond to its drivers in the physically correct
    direction. If it does not, every SHAP attribution built on it is noise."""
    grid = C.GRID
    ok = True

    # A pressurised field with a plume covering the middle of the domain.
    pressure = np.full((grid, grid), C.P_INIT_BAR + 30.0, np.float32)
    saturation = np.zeros((grid, grid), np.float32)
    saturation[40:88, 40:88] = 0.6

    base = Fault(0, C.DOMAIN_M / 2, C.DOMAIN_M / 2, 1000.0, 5.0, 1e-13, 0.0)

    # 1. Higher fault permeability must not reduce flux.
    qs = [
        fault_leakage_flux(
            pressure, saturation,
            Fault(0, base.x_m, base.y_m, base.length_m, base.width_m, k, 0.0), cfg
        )["q_fault_m3_s"]
        for k in (1e-15, 1e-14, 1e-13, 1e-12)
    ]
    mono_k = all(b >= a for a, b in zip(qs, qs[1:]))
    print(f"{'OK  ' if mono_k else 'FAIL'} flux increases with fault permeability: "
          f"{[f'{q:.3e}' for q in qs]}")
    ok &= mono_k

    # 2. Higher overpressure must not reduce flux.
    qs = [
        fault_leakage_flux(np.full((grid, grid), C.P_INIT_BAR + dp, np.float32),
                           saturation, base, cfg)["q_fault_m3_s"]
        for dp in (0.0, 10.0, 30.0, 60.0)
    ]
    mono_p = all(b >= a for a, b in zip(qs, qs[1:]))
    print(f"{'OK  ' if mono_p else 'FAIL'} flux increases with overpressure: "
          f"{[f'{q:.3e}' for q in qs]}")
    ok &= mono_p

    # 3. Withdrawal (pressure below initial) must produce exactly zero.
    q_draw = fault_leakage_flux(
        np.full((grid, grid), C.P_INIT_BAR - 40.0, np.float32), saturation, base, cfg
    )["q_fault_m3_s"]
    zero_draw = q_draw == 0.0
    print(f"{'OK  ' if zero_draw else 'FAIL'} no upward leakage during withdrawal: "
          f"Q = {q_draw:.3e}")
    ok &= zero_draw

    # 4. Immobile H2 (below residual saturation) must produce exactly zero.
    q_immobile = fault_leakage_flux(
        pressure, np.full((grid, grid), cfg.corey_sgr * 0.5, np.float32), base, cfg
    )["q_fault_m3_s"]
    zero_immobile = q_immobile == 0.0
    print(f"{'OK  ' if zero_immobile else 'FAIL'} no leakage below residual gas "
          f"saturation: Q = {q_immobile:.3e}")
    ok &= zero_immobile

    # 5. A fault far from the plume must leak less than one cutting through it.
    q_near = fault_leakage_flux(pressure, saturation, base, cfg)
    far = Fault(1, C.DOMAIN_M * 0.06, C.DOMAIN_M * 0.06, 1000.0, 5.0, 1e-13, 0.0)
    q_far = fault_leakage_flux(pressure, saturation, far, cfg)
    ordered = q_far["q_fault_m3_s"] < q_near["q_fault_m3_s"]
    print(f"{'OK  ' if ordered else 'FAIL'} fault on the plume leaks more than one "
          f"outside it: {q_near['q_fault_m3_s']:.3e} vs {q_far['q_fault_m3_s']:.3e} "
          f"(distances {q_near['distance_plume_to_fault_m']:.0f} m vs "
          f"{q_far['distance_plume_to_fault_m']:.0f} m)")
    ok &= ordered

    # 6. Corey curve endpoints.
    krg_lo, krg_hi = corey_krg(cfg.corey_sgr, cfg), corey_krg(1.0 - cfg.corey_swr, cfg)
    endpoints = np.isclose(krg_lo, 0.0) and np.isclose(krg_hi, 1.0)
    print(f"{'OK  ' if endpoints else 'FAIL'} Corey endpoints: "
          f"krg(S_gr)={krg_lo:.4f}, krg(1-S_wr)={krg_hi:.4f}")
    ok &= endpoints

    return bool(ok)


if __name__ == "__main__":
    print(f"Caprock fracture pressure (assumed depth {C.RESERVOIR_DEPTH_M:.0f} m, "
          f"gradient {LEAKAGE.frac_gradient_bar_per_m} bar/m): "
          f"{LEAKAGE.frac_pressure_bar:.1f} bar")
    print(f"Initial reservoir pressure: {C.P_INIT_BAR} bar\n")
    print("Monotonicity checks on the T3 leakage model:")
    ok = check_monotonicity()
    print(f"\n{'ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED'}")
    raise SystemExit(0 if ok else 1)
