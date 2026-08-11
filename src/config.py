"""Central configuration for HyLeakAI.

Every constant here is tagged with its provenance:

  [DATASET]  Read directly from the Mao et al. (2025) dataset or stated in the paper.
             These are facts.
  [DERIVED]  Computed from a [DATASET] value by an explicit, stated calculation.
  [ASSUMED]  Not present in the paper or dataset. Our choice, with a justification.
             Every one of these must be sweepable and must be disclosed in any writeup.

Reference:
  Mao, S., Carbonero, A., & Mehana, M. (2025). Deep learning for subsurface flow:
  A comparative study of U-Net, Fourier neural operators, and transformers in
  underground hydrogen storage. JGR: Machine Learning and Computation, 2,
  e2024JH000401. https://doi.org/10.1029/2024JH000401
  Dataset: https://zenodo.org/records/14029514 (CC-BY-4.0 / MIT)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
RAW_LMDB = DATA_DIR / "data.mdb"          # 12.38 GB download from Zenodo
CONSTANTS_NPY = DATA_DIR / "constants.npy"  # (1000, 2, 128, 128) float16
STATES_NPY = DATA_DIR / "states.npy"        # (1000, 60, 2, 128, 128) float16
STATS_JSON = DATA_DIR / "stats.json"
CHECKPOINT_DIR = REPO_ROOT / "checkpoints"
OUTPUT_DIR = REPO_ROOT / "outputs"

# Channel ordering, used consistently everywhere.
CONST_POROSITY, CONST_PERMEABILITY = 0, 1
STATE_PRESSURE, STATE_SATURATION, STATE_AUX = 0, 1, 2
N_STATE_CHANNELS = 3

# [DATASET, undocumented] The Zenodo record and the repository README both
# describe the per-timestep value as a 2-tuple (pressure, H2 saturation). It is
# actually a 3-tuple. We measured the third channel across timesteps and
# simulations:
#
#     corr(aux, pressure) = -0.993 to -0.999 at every timestep
#     aux / (P - P_init)  = -1.17e-4 per bar, constant across time
#
# That coefficient is a compressibility (1.17e-9 /Pa), the right order for
# brine plus pore compressibility, so the field is most consistent with a
# saturation- or volume-deviation driven by pressure. Roughly 10% of its
# variance is not explained by pressure and tracks the H2 plume.
#
# We cannot name it definitively, so we do not pretend to. It is preserved in
# the converted arrays under a neutral name, and it is NOT used as a model
# target: the paper predicts pressure and H2 saturation, and those are what we
# reproduce. Being ~99% collinear with pressure, it carries little independent
# information anyway.
STATE_CHANNEL_NAMES = ("pressure", "saturation", "aux_undocumented")


# --------------------------------------------------------------------------
# Grid and reservoir geometry
# --------------------------------------------------------------------------

GRID = 128                      # [DATASET] 128 x 128 x 1 cells
DOMAIN_M = 7680.0               # [DATASET] 7,680 m length and width
THICKNESS_M = 100.0             # [DATASET] 100 m reservoir thickness
CELL_M = DOMAIN_M / GRID        # [DERIVED] 60.0 m cell edge
CELL_AREA_M2 = CELL_M**2        # [DERIVED] 3,600 m^2
CELL_VOLUME_M3 = CELL_AREA_M2 * THICKNESS_M  # [DERIVED] 3.6e5 m^3

# [DATASET] "no-flow boundaries at the top and bottom, and outflow boundaries on
# the sides". Top/bottom = caprock/baserock (sealed). The SIDES are open, so
# lateral H2 migration to the domain edge is genuine escape from the model.
# This is the only leakage signal actually present in the simulation.
LATERAL_BOUNDARY_IS_OUTFLOW = True
CAPROCK_IS_SEALED_IN_SIM = True

# [ASSUMED] Well is described only as "a central well". On a 128-cell axis the
# centre falls between indices 63 and 64, so we take the 2x2 central block.
# validate_well_location() in src/data/explore.py confirms this empirically by
# locating the pressure maximum during an injection step.
WELL_IJ = (63, 63)              # top-left of the central 2x2 block
WELL_BLOCK = (slice(63, 65), slice(63, 65))
GRID_CENTER = (GRID - 1) / 2.0  # 63.5, used for the symmetric distance map


# --------------------------------------------------------------------------
# Temporal structure
# --------------------------------------------------------------------------

N_SIMS = 1000                   # [DATASET]
N_TIMESTEPS = 60                # [DATASET] usable steps; stored t=1..60
MONTHS_PER_STEP = 2             # [DATASET] output every two months
STEPS_PER_CYCLE = 6             # [DERIVED] 12 months / 2
N_CYCLES = 10                   # [DATASET] 10 annual storage cycles
INJECTION_STEPS_PER_CYCLE = 3   # [DERIVED] 6-month injection stage
# [DATASET] t=0 is the pre-injection state and is byte-identical across all
# 1,000 simulations. We drop it during conversion; keeping it would add 1,000
# duplicate samples that teach the model nothing.
DROP_TIMESTEP_ZERO = True


def cycle_index(t: int) -> int:
    """Cyclic index for timestep t (1-based): +1 injection, -1 withdrawal.

    [DATASET] Paper section 3.4: "the model receives a value of 1 during the
    injection stage and -1 during the withdrawal stage". Each annual cycle is a
    6-month injection followed by a 6-month withdrawal, i.e. 3 steps of each.
    """
    return 1 if ((t - 1) % STEPS_PER_CYCLE) < INJECTION_STEPS_PER_CYCLE else -1


def cycle_number(t: int) -> int:
    """1-based storage-cycle number (1..10) for timestep t (1-based)."""
    return (t - 1) // STEPS_PER_CYCLE + 1


def is_injection(t: int) -> bool:
    return cycle_index(t) == 1


# --------------------------------------------------------------------------
# Pressure regime
# --------------------------------------------------------------------------

P_INIT_BAR = 197.2              # [DATASET] "initial reservoir pressure (197.2e5 Pa)"
BAR_TO_PA = 1.0e5

# [ASSUMED] Reservoir depth is never stated. We infer it by assuming the
# reservoir is initially at hydrostatic pressure, which is standard for a
# depleted-then-repressurised gas reservoir, using a brine gradient of
# 0.105 bar/m (~1,050 kg/m^3). This yields ~1,878 m, a typical depleted gas
# reservoir depth. Only used for the caprock fracture-pressure criterion (T2).
HYDROSTATIC_GRADIENT_BAR_PER_M = 0.105
RESERVOIR_DEPTH_M = P_INIT_BAR / HYDROSTATIC_GRADIENT_BAR_PER_M  # ~1878 m


# --------------------------------------------------------------------------
# Leakage-label physics  (Phase 3)
# --------------------------------------------------------------------------


@dataclass
class LeakageConfig:
    """Physical constants for the derived leakage labels.

    None of these come from the dataset. They are documented modelling choices,
    and the defaults are mid-range values from the UHS / CO2-storage literature.
    Everything here should be swept in a sensitivity analysis before any number
    from it is reported as a result.
    """

    # --- T1: lateral containment loss (the one REAL signal) ---
    # Width in cells of the outer ring treated as "at the outflow boundary".
    # 4 cells = 240 m.
    boundary_ring_cells: int = 4
    # Saturation above which a cell counts as containing mobile H2.
    plume_saturation_threshold: float = 0.05

    # --- T2: caprock breach criterion (physics criterion, not a flux) ---
    # [ASSUMED] Fracture gradient. Typical sedimentary basin range is
    # 0.15-0.20 bar/m; 0.17 is a common screening default.
    frac_gradient_bar_per_m: float = 0.17
    frac_gradient_sweep: tuple[float, ...] = (0.15, 0.17, 0.20)

    # --- T3: semi-analytical fault conduit leakage (primary XGBoost target) ---
    # [ASSUMED] Caprock thickness — the vertical path length of the conduit.
    caprock_thickness_m: float = 50.0
    # [ASSUMED] H2 dynamic viscosity at ~200 bar and reservoir temperature.
    # Hydrogen is ~0.9-1.1e-5 Pa.s over this range; we take 9.5e-6 Pa.s.
    h2_viscosity_pa_s: float = 9.5e-6
    # [ASSUMED] Corey relative-permeability parameters for the gas phase.
    corey_swr: float = 0.20     # irreducible water saturation
    corey_sgr: float = 0.05     # residual (immobile) gas saturation
    corey_ng: float = 2.0       # Corey exponent

    # Monte-Carlo fault sampling. Log-uniform on permeability because it spans
    # three orders of magnitude.
    n_faults_per_sim: int = 20
    fault_perm_m2_range: tuple[float, float] = (1e-15, 1e-12)   # ~1-1000 mD
    fault_length_m_range: tuple[float, float] = (200.0, 2000.0)
    fault_width_m_range: tuple[float, float] = (1.0, 10.0)      # damage-zone width
    # Faults are placed within this radial band around the well, in metres, so
    # that the sample spans "right at the plume" to "far outside it".
    fault_radius_m_range: tuple[float, float] = (200.0, 3000.0)
    rng_seed: int = 20260809

    @property
    def frac_pressure_bar(self) -> float:
        """[DERIVED] Caprock fracture pressure at reservoir depth."""
        return RESERVOIR_DEPTH_M * self.frac_gradient_bar_per_m


LEAKAGE = LeakageConfig()


# --------------------------------------------------------------------------
# Model / training  (Phase 2)
# --------------------------------------------------------------------------


@dataclass
class UNetConfig:
    """U-Net-Small from the paper, Table 1: depth 4, embedding 32, ~7.7M params.

    Rationale for Small over Large: the paper reports U-Net-Small WITH cyclic and
    distance information reaching 8.6% pressure test error, level with
    U-Net-Large's 8.61% at 124M parameters and 35 GB. Without those two inputs
    Small degrades to 32.7%. So the extra input channels, not the parameter
    count, are what buy the accuracy here.
    """

    depth: int = 4
    embedding: int = 32
    in_channels: int = 5     # porosity, permeability, time, cyclic, distance
    out_channels: int = 2    # pressure, saturation
    use_cyclic: bool = True
    use_distance: bool = True


@dataclass
class TrainConfig:
    """Optimiser settings from the paper's Appendix Table A1."""

    batch_size: int = 32          # paper used 128 on a 40 GB A100; 32 fits a T4
    learning_rate: float = 1e-4
    weight_decay: float = 1e-5
    lr_halve_every: int = 50      # "halved every 50 epochs"
    epochs: int = 120
    # Multi-head loss weights. The paper trains separate models per state
    # variable; we use one two-headed model to halve training cost. Saturation
    # lives in [0,1] and pressure is standardised, so relative-L2 on each head
    # is already scale-free and equal weights are a sound starting point.
    lambda_saturation: float = 1.0
    lambda_pressure: float = 1.0
    num_workers: int = 4
    seed: int = 20260809


# --------------------------------------------------------------------------
# Data splits — BY SIMULATION, never by sample
# --------------------------------------------------------------------------

# [DATASET] Paper section 3.3: 700 train / 150 validation / 150 test, assigned by
# randomly shuffling the 1,000 simulations. All 60 timesteps of a simulation
# follow its simulation into the same split. Splitting by sample instead would
# put timestep t of a simulation in train and t+1 in test, which leaks almost
# everything and inflates accuracy.
SPLIT_SIZES = {"train": 700, "val": 150, "test": 150}
SPLIT_SEED = 20260809


def simulation_splits(seed: int = SPLIT_SEED) -> dict[str, list[int]]:
    """Deterministic simulation-level split. Used by BOTH the U-Net and XGBoost
    stages so a simulation never appears in one stage's training set and
    another's test set."""
    import numpy as np

    rng = np.random.default_rng(seed)
    ids = rng.permutation(N_SIMS)
    n_tr, n_va = SPLIT_SIZES["train"], SPLIT_SIZES["val"]
    return {
        "train": sorted(ids[:n_tr].tolist()),
        "val": sorted(ids[n_tr : n_tr + n_va].tolist()),
        "test": sorted(ids[n_tr + n_va :].tolist()),
    }
