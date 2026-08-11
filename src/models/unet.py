"""U-Net surrogate for UHS pressure and H2 saturation.

Reproduces the architecture of Mao et al. (2025), Table 1. The paper cites
milesial/Pytorch-UNet as its reference implementation and states that
"U-Net-Medium maintains the hyperparameters of the original U-Net
architecture" at 31M weights — which is exactly that implementation with a base
embedding of 64 and transposed-convolution upsampling. Halving the embedding to
32 gives the 7.7M-parameter Small variant; doubling it to 128 gives Large at
124M. `assert_paper_parameter_counts()` checks all three against the paper.

    Name            Depth   Embedding   Weights
    U-Net-Small     4       32          7.7M
    U-Net-Medium    4       64          31M
    U-Net-Large     4       128         124M

Deviation from the paper, deliberate: the paper trains one model per state
variable. We emit both from a single two-channel head, which halves training
cost. `SPLIT_HEADS_FALLBACK` in train_unet.py restores the paper's arrangement
if the shared trunk hurts saturation accuracy.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class DoubleConv(nn.Module):
    """(conv 3x3 -> BN -> ReLU) x 2, as in the original U-Net."""

    def __init__(self, in_ch: int, out_ch: int, mid_ch: int | None = None):
        super().__init__()
        mid_ch = mid_ch or out_ch
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, mid_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(mid_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(mid_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class Down(nn.Module):
    """Halve the resolution, then DoubleConv. Embedding doubles at each step."""

    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.op = nn.Sequential(nn.MaxPool2d(2), DoubleConv(in_ch, out_ch))

    def forward(self, x):
        return self.op(x)


class Up(nn.Module):
    """Transposed-conv upsample, concatenate the skip connection, DoubleConv."""

    def __init__(self, in_ch: int, out_ch: int, bilinear: bool = False):
        super().__init__()
        if bilinear:
            self.up = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=True)
            self.conv = DoubleConv(in_ch, out_ch, mid_ch=in_ch // 2)
        else:
            self.up = nn.ConvTranspose2d(in_ch, in_ch // 2, kernel_size=2, stride=2)
            self.conv = DoubleConv(in_ch, out_ch)

    def forward(self, x, skip):
        x = self.up(x)
        # Guard against odd input sizes; a no-op for the 128x128 grid.
        dy = skip.size(-2) - x.size(-2)
        dx = skip.size(-1) - x.size(-1)
        if dy or dx:
            x = F.pad(x, [dx // 2, dx - dx // 2, dy // 2, dy - dy // 2])
        return self.conv(torch.cat([skip, x], dim=1))


class UNet(nn.Module):
    """Depth-4 U-Net. On a 128x128 grid the bottleneck is 8x8."""

    def __init__(
        self,
        in_channels: int = 5,
        out_channels: int = 2,
        embedding: int = 32,
        bilinear: bool = False,
    ):
        super().__init__()
        e = embedding
        factor = 2 if bilinear else 1

        self.inc = DoubleConv(in_channels, e)
        self.down1 = Down(e, e * 2)
        self.down2 = Down(e * 2, e * 4)
        self.down3 = Down(e * 4, e * 8)
        self.down4 = Down(e * 8, e * 16 // factor)

        self.up1 = Up(e * 16, e * 8 // factor, bilinear)
        self.up2 = Up(e * 8, e * 4 // factor, bilinear)
        self.up3 = Up(e * 4, e * 2 // factor, bilinear)
        self.up4 = Up(e * 2, e, bilinear)
        self.outc = nn.Conv2d(e, out_channels, kernel_size=1)

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)
        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)
        return self.outc(x)

    @property
    def n_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


# --------------------------------------------------------------------------
# Loss
# --------------------------------------------------------------------------


def relative_l2(pred: torch.Tensor, target: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
    """Per-sample relative L2 error, averaged over the batch.

    Paper Equation 1: L(T, P) = ||T - P||_2 / ||T||_2, with T and P the
    flattened truth and prediction. The paper notes this relative measure
    benefits performance over an absolute one. Reported test errors are this
    same quantity, so training loss and evaluation metric are directly
    comparable.
    """
    b = pred.shape[0]
    diff = (pred - target).reshape(b, -1).norm(dim=1)
    denom = target.reshape(b, -1).norm(dim=1).clamp_min(eps)
    return (diff / denom).mean()


class MultiHeadRelativeL2(nn.Module):
    """Weighted relative-L2 across the pressure and saturation channels.

    Both terms are scale-free, so equal weights are a reasonable default; the
    weights exist so one head can be favoured if the shared trunk lets the other
    dominate.
    """

    def __init__(
        self,
        lambda_pressure: float = 1.0,
        lambda_saturation: float = 1.0,
        pressure_channel: int = 0,
        saturation_channel: int = 1,
    ):
        super().__init__()
        self.lambda_pressure = lambda_pressure
        self.lambda_saturation = lambda_saturation
        self.pc = pressure_channel
        self.sc = saturation_channel

    def forward(self, pred, target):
        lp = relative_l2(pred[:, self.pc], target[:, self.pc])
        ls = relative_l2(pred[:, self.sc], target[:, self.sc])
        total = self.lambda_pressure * lp + self.lambda_saturation * ls
        return total, {"pressure": lp.detach(), "saturation": ls.detach()}


# --------------------------------------------------------------------------
# Factory / self-check
# --------------------------------------------------------------------------

def load_state_dict_compat(model: nn.Module, state_dict: dict, strict: bool = True):
    """Load weights saved by either this module or `kaggle/hileak_core.py`.

    The Kaggle module is a self-contained copy of this architecture written with
    shorter attribute names, so its checkpoints carry different keys for
    identical tensors:

        inc.b.0.weight          <-> inc.block.0.weight
        d1.op.1.b.0.weight      <-> down1.op.1.block.0.weight
        u1.conv.b.0.weight      <-> up1.conv.block.0.weight

    Same layers, same shapes, same 7,764,674 parameters — only the names differ.
    Rather than force one naming on the other (which would strand the weights
    already trained on Kaggle), translate on load.
    """
    import re

    rules = [
        (re.compile(r"^inc\.b\."), "inc.block."),
        (re.compile(r"^d(\d)\.op\.1\.b\."), r"down\1.op.1.block."),
        (re.compile(r"^u(\d)\.conv\.b\."), r"up\1.conv.block."),
        (re.compile(r"^u(\d)\.up\."), r"up\1.up."),
    ]

    def remap(sd: dict) -> dict:
        out = {}
        for key, value in sd.items():
            for pattern, replacement in rules:
                if pattern.match(key):
                    key = pattern.sub(replacement, key)
                    break
            out[key] = value
        return out

    expected = set(model.state_dict().keys())
    remapped = remap(state_dict)

    # Decide by which naming actually matches more of the model's own keys.
    # A simple "do any keys overlap?" test is not enough: `outc.weight` and
    # `outc.bias` are identical in both namings, so the overlap is never empty.
    native_hits = len(expected & set(state_dict.keys()))
    remapped_hits = len(expected & set(remapped.keys()))

    if remapped_hits > native_hits:
        print(f"   remapped Kaggle-style keys ({remapped_hits}/{len(expected)} matched, "
              f"native naming matched only {native_hits})")
        return model.load_state_dict(remapped, strict=strict)
    return model.load_state_dict(state_dict, strict=strict)


PAPER_SIZES = {"small": 32, "medium": 64, "large": 128}
# Paper Table 1, in millions of weights.
PAPER_PARAM_COUNTS_M = {"small": 7.7, "medium": 31.0, "large": 124.0}


def build_unet(size: str = "small", in_channels: int = 5, out_channels: int = 2) -> UNet:
    if size not in PAPER_SIZES:
        raise ValueError(f"size must be one of {sorted(PAPER_SIZES)}, got {size!r}")
    return UNet(in_channels, out_channels, embedding=PAPER_SIZES[size])


def assert_paper_parameter_counts(tolerance: float = 0.03) -> dict[str, int]:
    """Confirm our implementation matches the paper's reported weight counts.

    A mismatch means the architecture is wrong — wrong depth, bilinear instead
    of transposed convolutions, or a different embedding progression — and any
    accuracy comparison against the paper would be meaningless.
    """
    counts = {}
    for size, expected_m in PAPER_PARAM_COUNTS_M.items():
        # The paper's counts are for the 3-input, 1-output configuration of its
        # single-variable models; the head and stem contribute negligibly.
        n = build_unet(size, in_channels=3, out_channels=1).n_parameters
        counts[size] = n
        rel = abs(n / 1e6 - expected_m) / expected_m
        status = "OK  " if rel <= tolerance else "FAIL"
        print(
            f"{status} U-Net-{size:6s} embedding {PAPER_SIZES[size]:3d}  "
            f"{n / 1e6:7.2f}M  paper {expected_m:6.1f}M  ({rel * 100:.1f}% off)"
        )
        if rel > tolerance:
            raise AssertionError(
                f"U-Net-{size}: {n / 1e6:.2f}M parameters, paper reports {expected_m}M"
            )
    return counts


if __name__ == "__main__":
    print("Checking architecture against Mao et al. (2025) Table 1:\n")
    assert_paper_parameter_counts()

    model = build_unet("small", in_channels=5, out_channels=2)
    x = torch.randn(2, 5, 128, 128)
    y = model(x)
    print(f"\nOK forward pass: {tuple(x.shape)} -> {tuple(y.shape)}")
    print(f"   as configured (5 in, 2 out): {model.n_parameters / 1e6:.2f}M parameters")

    loss_fn = MultiHeadRelativeL2()
    total, parts = loss_fn(y, torch.rand(2, 2, 128, 128))
    print(
        f"OK loss: total {total.item():.4f} "
        f"(pressure {parts['pressure'].item():.4f}, "
        f"saturation {parts['saturation'].item():.4f})"
    )
