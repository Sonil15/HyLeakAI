"""PyTorch dataset over the converted UHS memmaps.

Assembles the paper's input representation (section 3.2 and 3.4):

    channel 0  porosity            standardised
    channel 1  permeability        standardised (optionally log10 first)
    channel 2  time                scalar t/60 broadcast to a uniform channel
    channel 3  cyclic index        +1 injection, -1 withdrawal
    channel 4  distance to well    normalised, 1 nearest -> 0 farthest

and the two prediction targets:

    channel 0  pressure            standardised
    channel 1  saturation          left raw in [0, 1]

Saturation is deliberately not standardised. The paper found the zero-mean /
unit-variance transform gives no benefit for saturation because its
distribution is strongly non-Gaussian — most of the field is exactly zero.

Splits are by SIMULATION, never by sample. A simulation's 60 timesteps are
near-duplicates of each other; splitting by sample would place timestep t in
train and t+1 in test and make the reported error meaningless.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from src import config as C


# --------------------------------------------------------------------------
# Static channels
# --------------------------------------------------------------------------


def distance_to_well_map(grid: int = C.GRID) -> np.ndarray:
    """Normalised distance to the central well: 1 at the well, 0 at the farthest
    corner (paper section 3.4).

    This channel is what makes U-Net-Small viable for us: the paper reports the
    small pressure model going from 32.7% error without cyclic+distance to 8.6%
    with them, which is level with U-Net-Large.
    """
    yy, xx = np.mgrid[0:grid, 0:grid].astype(np.float64)
    d = np.hypot(yy - C.GRID_CENTER, xx - C.GRID_CENTER)
    return (1.0 - d / d.max()).astype(np.float32)


def time_channel_value(t: int, n_steps: int = C.N_TIMESTEPS) -> float:
    """Time normalised to (0, 1] (paper section 3.2)."""
    return t / n_steps


# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------


class Normalizer:
    """Standardisation constants derived from stats.json.

    `log_permeability` defaults to None, meaning "decide from the data": if the
    permeability field spans more than two orders of magnitude, standardising
    the raw values leaves a long right tail that dominates the input, so we take
    log10 first. The paper standardises raw permeability, and its SGSIM fields
    may be narrow enough for that; this keeps the choice explicit and logged
    rather than silent.
    """

    def __init__(self, stats: dict, log_permeability: bool | None = None):
        s = stats["stats"]
        self.poro_mean = s["porosity"]["mean"]
        self.poro_std = s["porosity"]["std"]

        perm = s["permeability"]
        if log_permeability is None:
            spread = perm["max"] / max(perm["min"], 1e-30)
            log_permeability = spread > 100.0
        self.log_permeability = bool(log_permeability)

        if self.log_permeability:
            self.perm_mean = s["log10_permeability"]["mean"]
            self.perm_std = s["log10_permeability"]["std"]
        else:
            self.perm_mean = perm["mean"]
            self.perm_std = perm["std"]

        self.pres_mean = s["pressure_bar"]["mean"]
        self.pres_std = s["pressure_bar"]["std"]

        for name in ("poro_std", "perm_std", "pres_std"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} is not positive; stats.json looks wrong")

    @classmethod
    def from_file(cls, path: Path = C.STATS_JSON, **kw) -> "Normalizer":
        return cls(json.loads(Path(path).read_text()), **kw)

    def porosity(self, a):
        return (a - self.poro_mean) / self.poro_std

    def permeability(self, a):
        if self.log_permeability:
            a = np.log10(np.maximum(a, 1e-30))
        return (a - self.perm_mean) / self.perm_std

    def pressure(self, p_centred):
        """Input is CENTRED pressure as stored (P_bar - P_INIT_BAR)."""
        return (p_centred + C.P_INIT_BAR - self.pres_mean) / self.pres_std

    def pressure_inverse(self, p_std) -> np.ndarray:
        """Standardised pressure back to physical bar."""
        return np.asarray(p_std) * self.pres_std + self.pres_mean

    def describe(self) -> str:
        return (
            f"Normalizer(log_permeability={self.log_permeability}, "
            f"poro={self.poro_mean:.4g}+/-{self.poro_std:.4g}, "
            f"perm={self.perm_mean:.4g}+/-{self.perm_std:.4g}, "
            f"pressure={self.pres_mean:.5g}+/-{self.pres_std:.4g} bar)"
        )


# --------------------------------------------------------------------------
# Dataset
# --------------------------------------------------------------------------


class UHSDataset(Dataset):
    """One item = one (simulation, timestep) pair.

    Memmaps are opened lazily so DataLoader workers (spawned processes on
    Windows) each get their own handle rather than inheriting one.
    """

    def __init__(
        self,
        split: str,
        data_dir: Path = C.DATA_DIR,
        normalizer: Normalizer | None = None,
        use_cyclic: bool = True,
        use_distance: bool = True,
        sim_ids: list[int] | None = None,
        n_timesteps: int = C.N_TIMESTEPS,
        augment: bool = False,
    ):
        self.data_dir = Path(data_dir)
        self.split = split
        self.use_cyclic = use_cyclic
        self.use_distance = use_distance
        self.n_timesteps = n_timesteps
        # Defaults to False here, unlike the Kaggle trainer: this class also
        # backs the inference service, which must never see a transformed input.
        self.augment = augment

        self.sim_ids = (
            list(sim_ids) if sim_ids is not None else C.simulation_splits()[split]
        )
        self.normalizer = normalizer or Normalizer.from_file(self.data_dir / "stats.json")
        self._distance = distance_to_well_map()
        self._constants: np.ndarray | None = None
        self._states: np.ndarray | None = None

        # Flat index -> (simulation id, timestep 1..n)
        self.index: list[tuple[int, int]] = [
            (sim, t) for sim in self.sim_ids for t in range(1, n_timesteps + 1)
        ]

    # -- lazy memmaps ------------------------------------------------------

    @property
    def constants(self) -> np.ndarray:
        if self._constants is None:
            self._constants = np.load(self.data_dir / "constants.npy", mmap_mode="r")
        return self._constants

    @property
    def states(self) -> np.ndarray:
        if self._states is None:
            self._states = np.load(self.data_dir / "states.npy", mmap_mode="r")
        return self._states

    def __len__(self) -> int:
        return len(self.index)

    @property
    def in_channels(self) -> int:
        return 3 + int(self.use_cyclic) + int(self.use_distance)

    # -- item --------------------------------------------------------------

    def build_input(self, sim: int, t: int) -> np.ndarray:
        const = np.asarray(self.constants[sim], dtype=np.float32)
        channels = [
            self.normalizer.porosity(const[C.CONST_POROSITY]),
            self.normalizer.permeability(const[C.CONST_PERMEABILITY]),
            np.full((C.GRID, C.GRID), time_channel_value(t, self.n_timesteps), np.float32),
        ]
        if self.use_cyclic:
            channels.append(
                np.full((C.GRID, C.GRID), float(C.cycle_index(t)), np.float32)
            )
        if self.use_distance:
            channels.append(self._distance)
        return np.stack(channels).astype(np.float32)

    def build_input_tensor(self, sim: int, t: int) -> torch.Tensor:
        """Model input for one (simulation, timestep) as a tensor, without going
        through __getitem__. Used for whole-trajectory inference, where we need
        all 60 timesteps of one simulation rather than a shuffled batch."""
        return torch.from_numpy(self.build_input(sim, t))

    def build_target(self, sim: int, t: int) -> np.ndarray:
        state = np.asarray(self.states[sim, t - 1], dtype=np.float32)
        return np.stack(
            [
                self.normalizer.pressure(state[C.STATE_PRESSURE]),
                state[C.STATE_SATURATION],
            ]
        ).astype(np.float32)

    def __getitem__(self, i: int):
        sim, t = self.index[i]
        x = self.build_input(sim, t)
        y = self.build_target(sim, t)
        if self.augment:
            x, y = d4_transform(x, y)
        return torch.from_numpy(x), torch.from_numpy(y)


def d4_transform(x: np.ndarray, y: np.ndarray, op: int | None = None):
    """Apply one of the 8 dihedral symmetries to input and target together.

    Kept byte-identical in behaviour to kaggle/hileak_core.d4_transform — the
    two module trees have diverged before, and a checkpoint trained under one
    augmentation scheme evaluated under another would report a number that
    means nothing. See that copy for why D4 is physically valid on this
    dataset; the short version is that the well is exactly central, the
    distance channel is invariant to machine precision, all four boundaries
    are outflow, and the measured geology anisotropy is 0.6%.

    torch's RNG, not numpy's: PyTorch reseeds torch per DataLoader worker but
    not numpy, which would otherwise give every worker the same stream.
    """
    if op is None:
        op = int(torch.randint(0, 8, (1,)).item())
    k, flip = op % 4, op // 4
    if k:
        x = np.rot90(x, k, axes=(1, 2))
        y = np.rot90(y, k, axes=(1, 2))
    if flip:
        x = x[:, :, ::-1]
        y = y[:, :, ::-1]
    return np.ascontiguousarray(x), np.ascontiguousarray(y)


def make_datasets(
    data_dir: Path = C.DATA_DIR,
    use_cyclic: bool = True,
    use_distance: bool = True,
    sim_limit: int | None = None,
) -> dict[str, UHSDataset]:
    """Train/val/test datasets sharing one Normalizer.

    `sim_limit` caps the number of simulations per split for CPU-only smoke
    tests and the reduced-data fallback described in the plan.
    """
    normalizer = Normalizer.from_file(Path(data_dir) / "stats.json")
    splits = C.simulation_splits()
    out = {}
    for name, ids in splits.items():
        if sim_limit is not None:
            ids = ids[: max(1, sim_limit * len(ids) // C.N_SIMS)] or ids[:1]
        out[name] = UHSDataset(
            name,
            data_dir=data_dir,
            normalizer=normalizer,
            use_cyclic=use_cyclic,
            use_distance=use_distance,
            sim_ids=ids,
        )
    return out
