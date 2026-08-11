"""Assemble the Kaggle notebook from the tested modules in this directory.

The three hileak_*.py files are real, importable, locally tested modules. This
script embeds them into %%writefile cells so the notebook is fully
self-contained on Kaggle — no repo checkout, no manual uploads. Regenerate with:

    python kaggle/make_notebook.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "notebooks" / "kaggle_train_unet.ipynb"


def src(text: str) -> list[str]:
    """Notebook source is a list of lines, all but the last newline-terminated."""
    lines = text.strip("\n").split("\n")
    return [ln + "\n" for ln in lines[:-1]] + [lines[-1]]


def code(text: str, magic: str | None = None) -> dict:
    body = src(text)
    if magic:
        body = [magic + "\n"] + body
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": body}


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": src(text)}


def embed(name: str) -> dict:
    return code((HERE / name).read_text(encoding="utf-8"), f"%%writefile {name}")


CELLS = [
md("""# HyLeakAI — U-Net surrogate training on Kaggle

Trains the U-Net surrogate mapping geology and operating stage to H2 saturation
and reservoir pressure fields, reproducing **Mao, Carbonero & Mehana (2025)**,
*JGR: Machine Learning and Computation*, `10.1029/2024JH000401`.

---

## Set these two things before running

1. **Settings → Accelerator → GPU T4 ×2.** Cell 1 refuses to run otherwise.
2. **Settings → Internet → On.** Required to fetch the dataset from Zenodo.

> **Do not pick P100.** Kaggle still offers it, but the P100 is compute
> capability 6.0 (Pascal) and recent PyTorch builds ship no Pascal kernels.
> `torch.cuda.is_available()` returns `True`, the run starts normally, and then
> dies on the first convolution with *"CUDA error: no kernel image is available
> for execution on the device"*. Cell 1 now checks the compute capability
> against the kernels actually compiled into this PyTorch build, and launches a
> real convolution to prove it works, so this fails in seconds instead of after
> the download. **T4 ×2 (sm_75) and L4 (sm_89) both work.**

## What this does

Fully self-contained — no repository, no manual uploads. It writes its own
source files, pulls the 12.38 GB dataset from Zenodo directly (Kaggle's
connection is fast, and the download is parallelised across 16 range requests),
converts it to ~3.9 GB of memmaps, verifies the conversion, deletes the raw
file, and trains.

## Sessions and resuming — read this before starting

A Kaggle GPU session is capped around 9 hours and the full 120-epoch run may not
fit in one. That is handled:

- Checkpoints are written **every epoch** to `/kaggle/working/checkpoints`,
  **atomically** (to `.tmp`, then moved), so being interrupted mid-save cannot
  destroy the checkpoint that exists to protect against interruption.
- **Three tiers are kept:** `_best.pt` (lowest validation loss), `_last.pt`
  (exact resume: model + optimizer + scheduler + history), and numbered
  `_epochNNN.pt` archival snapshots every 10 epochs (last 4 retained).
- Resume falls back through the snapshots newest-first, so a corrupt `_last.pt`
  costs you a few epochs rather than the whole run.

**To continue in a new session:** *Save Version → Save & Run All*, then in the
new session *Data → Add Input →* this notebook's output, set `PREV_OUTPUT` in
cell 2 to that path, and run all. Cell 9 detects the restored checkpoint and
resumes at the next epoch.

## Why U-Net-Small and not Large

The paper reports U-Net-Small **with the cyclic and distance channels** at 8.6%
pressure test error — level with U-Net-Large's 8.61% at 124M parameters and
35 GB. Without those channels Small collapses to 32.7%. The input
representation, not the parameter count, carries the accuracy. So this trains a
7.7M-parameter model on a free GPU and gives up almost nothing."""),

code('''# 1. Hardware check.
#
#    Two separate things can go wrong, and only the first is obvious:
#      (a) no GPU selected at all;
#      (b) a GPU is present but this PyTorch build has no kernels compiled for
#          its architecture. `torch.cuda.is_available()` returns True in that
#          case and the run dies on the first conv, ~30 minutes in.
#
#    (b) is live on Kaggle right now: the P100 is compute capability 6.0
#    (Pascal), and recent PyTorch builds dropped Pascal. Selecting P100 gives
#    "CUDA error: no kernel image is available for execution on the device".
#    Both are checked here, before anything expensive happens.
import subprocess

import torch

assert torch.cuda.is_available(), (
    "No GPU selected. Settings -> Accelerator -> GPU T4 x2, then re-run. "
    "Measured on CPU this model needs ~4 hours per epoch versus ~3-5 minutes on a T4."
)

name = torch.cuda.get_device_name(0)
major, minor = torch.cuda.get_device_capability(0)
vram = torch.cuda.get_device_properties(0).total_memory / 2**30
arch_list = torch.cuda.get_arch_list()
print(f"GPU: {name}  compute capability sm_{major}{minor}  ({vram:.1f} GiB)")
print(f"torch {torch.__version__}, CUDA {torch.version.cuda}")
print(f"this build has kernels for: {arch_list}")

if f"sm_{major}{minor}" not in arch_list:
    raise SystemExit(
        f"\\nThis PyTorch build has NO kernels for sm_{major}{minor} ({name}).\\n"
        f"It has: {arch_list}\\n\\n"
        f"FIX: Settings -> Accelerator -> GPU T4 x2 (sm_75), then re-run.\\n"
        f"     L4 (sm_89) also works. Avoid P100 (sm_60): recent PyTorch builds\\n"
        f"     dropped Pascal support, and the failure only surfaces on the first\\n"
        f"     convolution, long after training appears to have started.\\n\\n"
        f"Already-converted data in /kaggle/working survives the restart, so the\\n"
        f"download and conversion cells will skip themselves."
    )

# Confirm end to end that a real kernel launches on this device.
try:
    _probe = torch.nn.Conv2d(2, 2, 3, padding=1).cuda()
    _ = _probe(torch.zeros(1, 2, 8, 8, device="cuda"))
    torch.cuda.synchronize()
    del _probe
    print("OK a convolution actually executes on this GPU.")
except Exception as exc:
    raise SystemExit(f"GPU present but unusable: {exc}\\n"
                     f"FIX: Settings -> Accelerator -> GPU T4 x2, then re-run.")

# The paper used batch 128 at ~7.5 GB for U-Net-Small on a 40 GB A100.
# T4 is ~14.7 GiB, so 48 leaves comfortable headroom.
BATCH_SIZE = 96 if vram >= 20 else 48
print(f"Batch size: {BATCH_SIZE}")
print(subprocess.run(["df", "-h", "/kaggle/working"], capture_output=True, text=True).stdout)'''),

code('''# 2. Paths. Set PREV_OUTPUT when resuming from a previous session.
from pathlib import Path

WORK = Path("/kaggle/working")
SCRATCH = Path("/kaggle/tmp"); SCRATCH.mkdir(exist_ok=True)   # not persisted
DATA = WORK / "data"                                          # converted arrays
CKPT = WORK / "checkpoints"                                   # checkpoints
RAW = SCRATCH / "data.mdb"                                    # 12.4 GB, deleted after convert

# Continuing a run: Data -> Add Input -> this notebook's previous output, then
# set the path below, e.g. "/kaggle/input/hileak-unet-training".
PREV_OUTPUT = None

for d in (DATA, CKPT):
    d.mkdir(parents=True, exist_ok=True)

if PREV_OUTPUT:
    import shutil
    prev = Path(PREV_OUTPUT)
    for sub, dst in (("checkpoints", CKPT), ("data", DATA)):
        s = prev / sub
        if s.exists():
            for f in s.iterdir():
                if not (dst / f.name).exists():
                    shutil.copy(f, dst / f.name)
                    print(f"restored {sub}/{f.name}")

print("checkpoints:", sorted(p.name for p in CKPT.glob("*.pt")) or "none")
print("data:", sorted(p.name for p in DATA.glob("*")) or "none")'''),

embed("hileak_core.py"),
embed("hileak_prep.py"),
embed("hileak_train.py"),

code('''# 6. Architecture check against the paper's Table 1.
#    A mismatch means wrong depth, bilinear instead of transposed convolutions,
#    or a different embedding progression -- and any accuracy comparison to the
#    paper would be meaningless. So this runs before a single training step.
import sys

sys.path.insert(0, "/kaggle/working")
from hileak_core import assert_paper_parameter_counts

assert_paper_parameter_counts()'''),

code('''# 7. Fetch and convert the dataset. Skipped automatically if already present.
#    Download ~5-15 min on Kaggle's connection; conversion ~3-5 min.
!pip install -q lmdb 2>/dev/null

import json

import hileak_prep

if not (DATA / "states.npy").exists():
    hileak_prep.download(RAW, connections=16)
    print("\\nConverting...")
    summary = hileak_prep.convert(RAW, DATA)
    print("\\nVerifying...")
    hileak_prep.verify(RAW, DATA)
    RAW.unlink(missing_ok=True)          # reclaim 12.4 GB
    print("Raw LMDB deleted after verification.")
else:
    summary = json.loads((DATA / "stats.json").read_text())
    print("Using existing converted arrays.")

print()
for k, v in summary["stats"].items():
    print(f"  {k:20s} mean {v['mean']:12.5g}  std {v['std']:11.5g}  "
          f"range [{v['min']:.5g}, {v['max']:.5g}]")'''),

code('''# 8. Overfit test: 4 simulations, expect both losses to fall toward 0.
#    Catches channel-ordering, normalisation and architecture bugs in minutes,
#    before committing hours to the real run. Do not skip this.
from hileak_train import train_unet

_ = train_unet(DATA, CKPT, size="small", epochs=40, batch_size=16,
               overfit=4, workers=2, snapshot_every=0, resume=False)'''),

code('''# 9. Full training. Re-run this cell verbatim in a new session to resume.
history = train_unet(
    DATA, CKPT,
    size="small",          # 7.7M params; matches Large WITH cyclic+distance
    epochs=120,
    batch_size=BATCH_SIZE,
    lr=1e-4,               # paper Appendix Table A1
    weight_decay=1e-5,
    lr_halve_every=50,     # "halved every 50 epochs"
    workers=2,
    amp=True,
    snapshot_every=10,
    keep_snapshots=4,
    resume=True,
)'''),

code('''# 10. Held-out TEST error. Run once, at the end.
import torch
from torch.utils.data import DataLoader

from hileak_core import (Normalizer, UHSDataset, build_unet, evaluate,
                         simulation_splits)

device = torch.device("cuda")
ck = torch.load(CKPT / "unet_small_best.pt", map_location=device, weights_only=False)
norm = Normalizer.from_file(DATA / "stats.json")
splits = simulation_splits()

# The single most damaging possible bug in this project -- assert, do not assume.
for other in ("train", "val"):
    assert not set(splits["test"]) & set(splits[other]), f"test/{other} overlap"
print(f"OK splits disjoint. Test simulations: {len(splits['test'])}")

test = UHSDataset(DATA, splits["test"], norm)
model = build_unet("small", test.in_channels, 2).to(device)
model.load_state_dict(ck["model"])
m = evaluate(model, DataLoader(test, batch_size=BATCH_SIZE, num_workers=2), device)

print(f"\\nTEST relative L2   pressure {m['pressure']:.4f}   saturation {m['saturation']:.4f}")
print("Paper (U-Net-Large, 124M params, A100): pressure 0.0861, saturation 0.0577")
print(f"Best checkpoint was epoch {ck['epoch']}")'''),

code('''# 11. Training curves.
import json

import matplotlib.pyplot as plt

hist = json.loads((CKPT / "unet_small_history.json").read_text())
ep = [h["epoch"] for h in hist]
fig, ax = plt.subplots(1, 2, figsize=(12, 4))
for a, key, paper in ((ax[0], "pressure", 0.0861), (ax[1], "saturation", 0.0577)):
    a.plot(ep, [h[f"train_{key}"] for h in hist], label="train")
    a.plot(ep, [h[f"val_{key}"] for h in hist], label="val")
    a.axhline(paper, ls="--", c="k", lw=1, label="paper U-Net-Large")
    a.set_title(f"{key} relative L2"); a.set_xlabel("epoch")
    a.set_yscale("log"); a.legend(); a.grid(alpha=0.3)
plt.tight_layout(); plt.show()'''),

code('''# 12. The two qualitative signatures from the paper.
#     If these are absent the model is wrong regardless of its headline number:
#       - pressure error SPIKES at each injection -> withdrawal transition (Fig. 8)
#       - saturation error concentrates at the PLUME FRONT (Fig. 10)
import numpy as np

from hileak_core import N_TIMESTEPS, cycle_index, relative_l2

ids = splits["test"][:40]
ds = UHSDataset(DATA, ids, norm)
err_p, err_s = np.zeros(N_TIMESTEPS), np.zeros(N_TIMESTEPS)
model.eval()
with torch.no_grad():
    for t in range(1, N_TIMESTEPS + 1):
        x = torch.stack([ds.build_input_tensor(s, t) for s in ids]).to(device)
        y = torch.stack([torch.from_numpy(ds.build_target(s, t)) for s in ids]).to(device)
        p = model(x)
        err_p[t - 1] = relative_l2(p[:, 0], y[:, 0]).item()
        err_s[t - 1] = relative_l2(p[:, 1], y[:, 1]).item()

steps = np.arange(1, N_TIMESTEPS + 1)
trans = [t for t in steps if t > 1 and cycle_index(t) == -1 and cycle_index(t - 1) == 1]
fig, ax = plt.subplots(figsize=(12, 4))
ax.plot(steps, err_p, marker="o", ms=3, label="pressure")
ax.plot(steps, err_s, marker="s", ms=3, label="saturation")
for i, t in enumerate(trans):
    ax.axvline(t, c="r", ls=":", lw=1,
               label="injection -> withdrawal" if i == 0 else None)
ax.set_xlabel("timestep (2 months each)"); ax.set_ylabel("relative L2")
ax.set_title("Temporal coherence (paper Fig. 8)"); ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout(); plt.show()

at = err_p[[t - 1 for t in trans]].mean()
elsewhere = err_p[[t - 1 for t in steps if t not in trans]].mean()
print(f"pressure error at transitions {at:.4f} vs elsewhere {elsewhere:.4f} "
      f"({at / elsewhere:.2f}x)")
print("PASS: reproduces the paper" if at > elsewhere else
      "CHECK: the paper reports a clear spike here; its absence is suspicious")'''),

code('''# 13. Field comparison for one held-out simulation (paper Fig. 10).
sim = splits["test"][0]
show = [1, 3, 6, 12, 30, 60]
fig, axes = plt.subplots(4, len(show), figsize=(3 * len(show), 11))
with torch.no_grad():
    for j, t in enumerate(show):
        x = ds.build_input_tensor(sim, t)[None].to(device)
        y = ds.build_target(sim, t)
        p = model(x)[0].cpu().numpy()
        for r, (truth, pred, lab) in enumerate([(y[1], p[1], "saturation"),
                                                (y[0], p[0], "pressure")]):
            axes[2 * r, j].imshow(truth, cmap="viridis")
            axes[2 * r, j].set_title(f"{lab} truth  t={t}", fontsize=9)
            im = axes[2 * r + 1, j].imshow(truth - pred, cmap="RdBu_r")
            axes[2 * r + 1, j].set_title(f"{lab} error", fontsize=9)
            plt.colorbar(im, ax=axes[2 * r + 1, j], fraction=0.046)
for a in axes.ravel():
    a.set_xticks([]); a.set_yticks([])
plt.suptitle(f"Simulation {sim} (held out) - saturation error should ring the plume front")
plt.tight_layout(); plt.show()'''),

md("""## Optional experiment — two single-head models

Cells 9-13 train ONE model with two output channels, covering pressure and
saturation together. That halves training cost, but it is a deviation: the paper
trains a **separate model per state variable**.

The two targets genuinely conflict. Pressure is smooth, global, and flips sign
between injection and withdrawal; saturation is local with a sharp plume front.
A shared trunk must compromise between them, and that is the leading suspect for
our test error being ~1.9x the paper's at the same model size (0.1640 pressure
against the paper's 0.086).

The cells below test that directly. Each trains a one-headed model, so together
they cost two more full runs — but they reuse the converted data, so there is no
re-download. Checkpoints are named separately (`unet_small_pressure_*`,
`unet_small_saturation_*`) and cannot overwrite the two-head run.

**Worth knowing before you spend the GPU hours:** for leakage screening the
two-head model already retains **99% of the simulator's PR-AUC**, so this
experiment matters mainly for the reproduction claim and for flux-magnitude
accuracy, not for the risk ranking.

**How to read the result:** if single-head pressure lands near 0.09-0.10, the
shared trunk was the limiter. If it stays near 0.16, the cause is elsewhere
(batch 48 vs the paper's 128, or mixed precision) and the cheaper two-head model
should be kept."""),

code('''# Single-head PRESSURE model.
hist_p = train_unet(
    DATA, CKPT, size="small", target="pressure",
    epochs=120, batch_size=BATCH_SIZE, lr=1e-4, weight_decay=1e-5,
    lr_halve_every=50, workers=2, amp=True,
    snapshot_every=10, keep_snapshots=4, resume=True,
)'''),

code('''# Single-head SATURATION model.
hist_s = train_unet(
    DATA, CKPT, size="small", target="saturation",
    epochs=120, batch_size=BATCH_SIZE, lr=1e-4, weight_decay=1e-5,
    lr_halve_every=50, workers=2, amp=True,
    snapshot_every=10, keep_snapshots=4, resume=True,
)'''),

code('''# Verdict: do two single-head models beat one two-head model?
import torch
from torch.utils.data import DataLoader

from hileak_core import (STATE_PRESSURE, STATE_SATURATION, Normalizer,
                         UHSDataset, build_unet, simulation_splits)
from hileak_train import evaluate_single

device = torch.device("cuda")
norm = Normalizer.from_file(DATA / "stats.json")
splits = simulation_splits()
test_ds = UHSDataset(DATA, splits["test"], norm)
loader = DataLoader(test_ds, batch_size=BATCH_SIZE, num_workers=2)

scores = {}
for target, channel in (("pressure", STATE_PRESSURE), ("saturation", STATE_SATURATION)):
    ck = torch.load(CKPT / f"unet_small_{target}_best.pt", map_location=device,
                    weights_only=False)
    m = build_unet("small", test_ds.in_channels, 1).to(device)
    m.load_state_dict(ck["model"])
    scores[target] = evaluate_single(m, loader, device, channel)
    print(f"single-head {target:11s} test relative L2 {scores[target]:.4f}  "
          f"(best epoch {ck['epoch']})")

two_head = {"pressure": 0.1640, "saturation": 0.1101}   # measured in this project
paper = {"pressure": 0.086, "saturation": 0.0577}
print(f"\\n{'variable':12s} {'two-head':>9} {'single-head':>12} {'change':>9} {'paper':>8}")
for k in ("pressure", "saturation"):
    print(f"{k:12s} {two_head[k]:>9.4f} {scores[k]:>12.4f} "
          f"{scores[k] - two_head[k]:>+9.4f} {paper[k]:>8.4f}")

if scores["pressure"] < two_head["pressure"] - 0.01:
    print("\\nVERDICT: the shared trunk was the limiter — use separate models.")
else:
    print("\\nVERDICT: splitting the heads did NOT help. The limiter is batch size "
          "or precision, and the cheaper two-head model should be kept.")'''),

md("""## Before you close the session

Running cells interactively persists **nothing**. `/kaggle/working` exists only
inside the live session. Close the tab or let it time out and the checkpoints
*and* the converted dataset are gone.

### Save Version → **Quick Save**

Quick Save commits the current session's `/kaggle/working` **without
re-executing anything** — which is exactly what you want once training has
already finished.

> **Do NOT choose "Save & Run All" here.** It restarts the notebook from cell 1
> — another 12.4 GB download and a full retrain — discarding the run you are
> trying to keep. "Save & Run All" is only for an unattended run you are
> deliberately launching.

Belt and braces: the editor's right-hand file browser also lets you download
`checkpoints/unet_small_best.pt` (~93 MB) directly. Do both; it costs nothing.

To continue training later: new session → *Data → Add Input* → this notebook's
output → set `PREV_OUTPUT` in cell 2 → run all.

## What to expect

Roughly 3–5 min per epoch on a T4, so 120 epochs is about 7–10 hours, i.e.
two sessions. Target is relative L2 near **0.06–0.10 saturation** and
**0.09–0.13 pressure**.

The paper's best (U-Net-Large, 124M parameters, A100) is **0.0577** and
**0.0861**. Landing near 0.10 with a 7.7M-parameter model on a free GPU is a
legitimate reproduction and should be reported as exactly that — not rounded up
to the paper's numbers."""),
]


def main() -> None:
    nb = {
        "cells": CELLS,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python",
                           "name": "python3"},
            "language_info": {"name": "python"},
            "accelerator": "GPU",
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(nb, indent=1), encoding="utf-8")
    print(f"wrote {OUT}  ({OUT.stat().st_size:,} bytes, {len(CELLS)} cells)")


if __name__ == "__main__":
    main()
