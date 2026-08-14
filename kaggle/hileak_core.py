"""HyLeakAI core: U-Net surrogate for underground hydrogen storage.

Self-contained single file for Kaggle — no repo checkout, no package install.
Mirrors src/config.py, src/models/unet.py and src/data/dataset.py.

Reproduces Mao, Carbonero & Mehana (2025), JGR: Machine Learning and
Computation, 10.1029/2024JH000401.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset

# ---------------------------------------------------------------- constants

GRID = 128
DOMAIN_M = 7680.0                    # paper: 7,680 m length and width
CELL_M = DOMAIN_M / GRID             # 60 m
GRID_CENTER = (GRID - 1) / 2.0       # 63.5 — the central well
N_SIMS = 1000
N_TIMESTEPS = 60                     # t = 1..60; t=0 is pre-injection, identical
STEPS_PER_CYCLE = 6                  # 12 months / 2-month output interval
INJECTION_STEPS_PER_CYCLE = 3        # 6-month injection stage
P_INIT_BAR = 197.2                   # initial reservoir pressure
STATE_PRESSURE, STATE_SATURATION = 0, 1
SPLIT_SEED = 20260809
SPLIT_SIZES = {"train": 700, "val": 150, "test": 150}


def cycle_index(t: int) -> int:
    """+1 during injection, -1 during withdrawal (paper section 3.4).

    Verified against the simulations: on injection steps the well pressure
    exceeds 100.0% of the field, on withdrawal steps 0.0%.
    """
    return 1 if ((t - 1) % STEPS_PER_CYCLE) < INJECTION_STEPS_PER_CYCLE else -1


def cycle_number(t: int) -> int:
    return (t - 1) // STEPS_PER_CYCLE + 1


def simulation_splits(seed: int = SPLIT_SEED) -> dict[str, list[int]]:
    """Split BY SIMULATION (paper section 3.3: 700/150/150).

    A simulation's 60 timesteps are near-duplicates of one another. Splitting by
    sample would place timestep t in train and t+1 in test, leaking almost
    everything and inflating the reported error.
    """
    rng = np.random.default_rng(seed)
    ids = rng.permutation(N_SIMS)
    a, b = SPLIT_SIZES["train"], SPLIT_SIZES["val"]
    return {
        "train": sorted(ids[:a].tolist()),
        "val": sorted(ids[a : a + b].tolist()),
        "test": sorted(ids[a + b :].tolist()),
    }


# ---------------------------------------------------------------- model


class DoubleConv(nn.Module):
    """(conv 3x3 -> BN -> ReLU) x 2, as in the original U-Net."""

    def __init__(self, i: int, o: int, mid: int | None = None):
        super().__init__()
        mid = mid or o
        self.b = nn.Sequential(
            nn.Conv2d(i, mid, 3, padding=1, bias=False), nn.BatchNorm2d(mid), nn.ReLU(True),
            nn.Conv2d(mid, o, 3, padding=1, bias=False), nn.BatchNorm2d(o), nn.ReLU(True),
        )

    def forward(self, x):
        return self.b(x)


class Down(nn.Module):
    def __init__(self, i: int, o: int):
        super().__init__()
        self.op = nn.Sequential(nn.MaxPool2d(2), DoubleConv(i, o))

    def forward(self, x):
        return self.op(x)


class Up(nn.Module):
    """Transposed-conv upsample, concatenate skip, DoubleConv."""

    def __init__(self, i: int, o: int):
        super().__init__()
        self.up = nn.ConvTranspose2d(i, i // 2, 2, stride=2)
        self.conv = DoubleConv(i, o)

    def forward(self, x, skip):
        x = self.up(x)
        dy, dx = skip.size(-2) - x.size(-2), skip.size(-1) - x.size(-1)
        if dy or dx:
            x = F.pad(x, [dx // 2, dx - dx // 2, dy // 2, dy - dy // 2])
        return self.conv(torch.cat([skip, x], dim=1))


class UNet(nn.Module):
    """Depth-4 U-Net. Embedding 32/64/128 gives the paper's Small/Medium/Large.

    On the 128x128 grid the bottleneck is 8x8.
    """

    def __init__(self, in_channels: int = 5, out_channels: int = 2, embedding: int = 32):
        super().__init__()
        e = embedding
        self.inc = DoubleConv(in_channels, e)
        self.d1, self.d2 = Down(e, e * 2), Down(e * 2, e * 4)
        self.d3, self.d4 = Down(e * 4, e * 8), Down(e * 8, e * 16)
        self.u1, self.u2 = Up(e * 16, e * 8), Up(e * 8, e * 4)
        self.u3, self.u4 = Up(e * 4, e * 2), Up(e * 2, e)
        self.outc = nn.Conv2d(e, out_channels, 1)

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.d1(x1)
        x3 = self.d2(x2)
        x4 = self.d3(x3)
        x5 = self.d4(x4)
        x = self.u1(x5, x4)
        x = self.u2(x, x3)
        x = self.u3(x, x2)
        x = self.u4(x, x1)
        return self.outc(x)

    @property
    def n_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


PAPER_SIZES = {"small": 32, "medium": 64, "large": 128}
PAPER_PARAMS_M = {"small": 7.7, "medium": 31.0, "large": 124.0}   # paper Table 1


def build_unet(size: str = "small", in_channels: int = 5, out_channels: int = 2) -> UNet:
    return UNet(in_channels, out_channels, PAPER_SIZES[size])


def assert_paper_parameter_counts(tol: float = 0.03) -> None:
    """Confirm the architecture matches the paper's reported weight counts.

    A mismatch means wrong depth, bilinear instead of transposed convolutions,
    or a different embedding progression — and any accuracy comparison to the
    paper would be meaningless. Runs before a single training step.
    """
    for s, want in PAPER_PARAMS_M.items():
        n = build_unet(s, 3, 1).n_parameters      # paper's 3-in/1-out configuration
        rel = abs(n / 1e6 - want) / want
        print(f"{'OK  ' if rel <= tol else 'FAIL'} U-Net-{s:6s} emb {PAPER_SIZES[s]:3d}  "
              f"{n / 1e6:7.2f}M  paper {want:6.1f}M  ({rel * 100:.1f}% off)")
        assert rel <= tol, f"U-Net-{s}: {n / 1e6:.2f}M vs paper {want}M"


# ---------------------------------------------------------------- loss


def relative_l2(pred: torch.Tensor, target: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
    """Paper Eq. 1: ||T - P||_2 / ||T||_2, per sample, averaged over the batch.

    Training loss and reported test error are the same quantity, so the numbers
    compare directly with the paper's Table 4.
    """
    b = pred.shape[0]
    diff = (pred - target).reshape(b, -1).norm(dim=1)
    denom = target.reshape(b, -1).norm(dim=1).clamp_min(eps)
    return (diff / denom).mean()


class MultiHeadRelativeL2(nn.Module):
    """Weighted relative-L2 across pressure and saturation.

    The paper trains one model per state variable; we emit both from one
    two-channel head, which halves training cost. Both terms are scale-free so
    equal weights are a sound default.
    """

    def __init__(self, lambda_pressure: float = 1.0, lambda_saturation: float = 1.0):
        super().__init__()
        self.lp, self.ls = lambda_pressure, lambda_saturation

    def forward(self, pred, target):
        p = relative_l2(pred[:, STATE_PRESSURE], target[:, STATE_PRESSURE])
        s = relative_l2(pred[:, STATE_SATURATION], target[:, STATE_SATURATION])
        return self.lp * p + self.ls * s, {"pressure": p.detach(), "saturation": s.detach()}


# ---------------------------------------------------------------- data


def distance_to_well_map(grid: int = GRID) -> np.ndarray:
    """1 at the central well, 0 at the farthest corner (paper section 3.4).

    This channel is what makes U-Net-Small viable: the paper reports the small
    pressure model going from 32.7% error without cyclic+distance to 8.6% with
    them, level with U-Net-Large.
    """
    yy, xx = np.mgrid[0:grid, 0:grid].astype(np.float64)
    d = np.hypot(yy - GRID_CENTER, xx - GRID_CENTER)
    return (1.0 - d / d.max()).astype(np.float32)


class Normalizer:
    """Standardisation constants from stats.json.

    `log_permeability` defaults to deciding from the data: the measured field
    spans 1.03-738.8 mD (716x), so raw standardisation would leave a long right
    tail dominating the input. The paper standardises raw permeability; we make
    the choice explicit and logged rather than silent.
    """

    def __init__(self, stats: dict, log_permeability: bool | None = None):
        s = stats["stats"]
        self.poro_mean, self.poro_std = s["porosity"]["mean"], s["porosity"]["std"]
        perm = s["permeability"]
        if log_permeability is None:
            log_permeability = perm["max"] / max(perm["min"], 1e-30) > 100.0
        self.log_permeability = bool(log_permeability)
        src = s["log10_permeability"] if self.log_permeability else perm
        self.perm_mean, self.perm_std = src["mean"], src["std"]
        self.pres_mean, self.pres_std = s["pressure_bar"]["mean"], s["pressure_bar"]["std"]
        for n in ("poro_std", "perm_std", "pres_std"):
            if getattr(self, n) <= 0:
                raise ValueError(f"{n} is not positive; stats.json looks wrong")

    @classmethod
    def from_file(cls, path) -> "Normalizer":
        return cls(json.loads(Path(path).read_text()))

    def porosity(self, a):
        return (a - self.poro_mean) / self.poro_std

    def permeability(self, a):
        if self.log_permeability:
            a = np.log10(np.maximum(a, 1e-30))
        return (a - self.perm_mean) / self.perm_std

    def pressure(self, p_centred):
        """Input is CENTRED pressure as stored (P_bar - P_INIT_BAR)."""
        return (p_centred + P_INIT_BAR - self.pres_mean) / self.pres_std

    def pressure_inverse(self, p_std):
        return np.asarray(p_std) * self.pres_std + self.pres_mean

    def describe(self) -> str:
        return (f"Normalizer(log_permeability={self.log_permeability}, "
                f"pressure={self.pres_mean:.5g}+/-{self.pres_std:.4g} bar)")


class UHSDataset(Dataset):
    """One item = one (simulation, timestep) pair.

    Inputs  (5 ch): porosity, permeability, time, cyclic index, distance to well
    Targets (2 ch): pressure (standardised), saturation (raw, in [0,1])

    Saturation is deliberately not standardised — the paper found the transform
    gives no benefit because most of the field is exactly zero.

    Memmaps open lazily so each DataLoader worker gets its own handle.
    """

    def __init__(self, data_dir, sim_ids, normalizer: Normalizer,
                 use_cyclic: bool = True, use_distance: bool = True,
                 augment: bool = False):
        self.data_dir = Path(data_dir)
        self.sim_ids = list(sim_ids)
        self.normalizer = normalizer
        self.use_cyclic, self.use_distance = use_cyclic, use_distance
        self.augment = augment
        self._distance = distance_to_well_map()
        self._c = None
        self._s = None
        self.index = [(s, t) for s in self.sim_ids for t in range(1, N_TIMESTEPS + 1)]

    @property
    def constants(self):
        if self._c is None:
            self._c = np.load(self.data_dir / "constants.npy", mmap_mode="r")
        return self._c

    @property
    def states(self):
        if self._s is None:
            self._s = np.load(self.data_dir / "states.npy", mmap_mode="r")
        return self._s

    def __len__(self):
        return len(self.index)

    @property
    def in_channels(self) -> int:
        return 3 + int(self.use_cyclic) + int(self.use_distance)

    def build_input(self, sim: int, t: int) -> np.ndarray:
        c = np.asarray(self.constants[sim], np.float32)
        ch = [
            self.normalizer.porosity(c[0]),
            self.normalizer.permeability(c[1]),
            np.full((GRID, GRID), t / N_TIMESTEPS, np.float32),
        ]
        if self.use_cyclic:
            ch.append(np.full((GRID, GRID), float(cycle_index(t)), np.float32))
        if self.use_distance:
            ch.append(self._distance)
        return np.stack(ch).astype(np.float32)

    def build_target(self, sim: int, t: int) -> np.ndarray:
        st = np.asarray(self.states[sim, t - 1], np.float32)
        return np.stack([
            self.normalizer.pressure(st[STATE_PRESSURE]),
            st[STATE_SATURATION],
        ]).astype(np.float32)

    def build_input_tensor(self, sim: int, t: int) -> torch.Tensor:
        return torch.from_numpy(self.build_input(sim, t))

    def __getitem__(self, i: int):
        s, t = self.index[i]
        x = self.build_input(s, t)
        y = self.build_target(s, t)
        if self.augment:
            x, y = d4_transform(x, y)
        return torch.from_numpy(x), torch.from_numpy(y)


# ---------------------------------------------------------------- augmentation


def d4_transform(x: np.ndarray, y: np.ndarray, op: int | None = None):
    """Apply one of the 8 dihedral (D4) symmetries to input and target together.

    Why this is physically valid here, and not a generic image-augmentation
    reflex — every one of these has to hold, and all were measured:

      * The well sits at the exact grid centre (the 2x2 block at 63:65 on a
        128 axis), so it maps onto itself under all 8 operations.
      * The distance-to-well channel is D4-invariant to machine precision
        (verified: max |rot90(d) - d| = 0). The time and cyclic channels are
        uniform fields, so they are trivially invariant.
      * All four lateral boundaries are outflow, so no direction is special.
      * Permeability is a scalar per cell on a square grid, and the measured
        geology anisotropy is 0.6% (row-vs-column autocorrelation, 200 sims,
        lags 1-32) - i.e. the fields are isotropic, so a rotated realisation is
        still a plausible one rather than an off-distribution invention.
      * Rotational deviation of the ensemble-mean state field sits AT the
        finite-ensemble noise floor (pressure 0.0699 vs 0.0708), so the flow
        solution is rotation-equivariant within measurement error.

    Had the permeability been generated with a directional variogram, this
    would manufacture geology that never occurs and make things worse. It was
    not, so the 8x expansion is free.

    Uses torch's RNG rather than numpy's: PyTorch reseeds torch per DataLoader
    worker but does NOT reseed numpy, so numpy would hand every worker the
    same augmentation stream.
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
    # rot90/slicing return views with negative strides; torch.from_numpy needs
    # a contiguous, positively-strided buffer.
    return np.ascontiguousarray(x), np.ascontiguousarray(y)


# ---------------------------------------------------------------- checkpoints


def save_checkpoint(path, model, opt, sched, epoch: int, history: list, meta: dict) -> None:
    """Write atomically: to a .tmp file, then move into place.

    An interruption mid-write — a session kill, a disconnect — must not be able
    to destroy the checkpoint that exists to protect against interruption.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save({"epoch": epoch, "model": model.state_dict(),
                "optimizer": opt.state_dict(), "scheduler": sched.state_dict(),
                "history": history, "meta": meta}, tmp)
    tmp.replace(path)


def load_checkpoint(path, model, opt=None, sched=None, device="cpu"):
    ck = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(ck["model"])
    if opt is not None and "optimizer" in ck:
        opt.load_state_dict(ck["optimizer"])
    if sched is not None and "scheduler" in ck:
        sched.load_state_dict(ck["scheduler"])
    return ck


@torch.no_grad()
def evaluate(model, loader, device, amp: bool = False) -> dict[str, float]:
    """Mean per-sample relative L2 per state variable — the paper's metric."""
    model.eval()
    tot = {"pressure": 0.0, "saturation": 0.0}
    n = 0
    for x, y in loader:
        x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
        with torch.autocast(device_type=device.type, enabled=amp and device.type == "cuda"):
            p = model(x)
        tot["pressure"] += relative_l2(p[:, 0], y[:, 0]).item()
        tot["saturation"] += relative_l2(p[:, 1], y[:, 1]).item()
        n += 1
    return {k: v / max(n, 1) for k, v in tot.items()}
