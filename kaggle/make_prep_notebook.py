"""Assemble a data-prep-only Kaggle notebook: download + convert + verify.

No GPU, no training — just steps 1-3 of getting the Mao et al. dataset onto
Kaggle in the compact memmap form, so a later session can compute
geology/caprock features for site-suitability screening without re-paying the
12.38 GB download. Regenerate with:

    python kaggle/make_prep_notebook.py
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "notebooks" / "kaggle_prep_data.ipynb"


def src(text: str) -> list[str]:
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
    md("""# HyLeakAI — dataset download + conversion only

No GPU needed. This does steps 1-3 of getting the Mao et al. (2025) UHS
dataset ready: fetch the 12.38 GB LMDB from Zenodo, convert it to compact
memmaps, verify the conversion, and discard the raw file. It does **not**
train anything.

**Settings -> Internet -> On.** That's the only setting this needs.

`data/constants.npy` (~131 MB: porosity, permeability) and `data/states.npy`
(~3.9 GB: pressure, saturation) land in `/kaggle/working`, so they persist in
this kernel's output — Quick Save afterwards, then a follow-up
session can `Data -> Add Input` this output and compute features straight
from the memmaps without downloading again."""),

    code('''# Paths.
from pathlib import Path

WORK = Path("/kaggle/working")
SCRATCH = Path("/kaggle/tmp"); SCRATCH.mkdir(exist_ok=True)   # not persisted
DATA = WORK / "data"
RAW = SCRATCH / "data.mdb"                                    # 12.4 GB, deleted after convert
DATA.mkdir(parents=True, exist_ok=True)

print("data:", sorted(p.name for p in DATA.glob("*")) or "none")'''),

    embed("hileak_prep.py"),

    code('''# Fetch and convert. Skipped automatically if already present.
#    Download ~5-15 min on Kaggle's connection; conversion ~3-5 min.
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "lmdb"], check=True)

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
          f"range [{v['min']:.5g}, {v['max']:.5g}]")

print("\\ndone:", sorted(p.name for p in DATA.glob("*")))'''),

    md("""## Before you close the session

Save Version -> **Quick Save** to persist `/kaggle/working/data` as this
kernel's output. Do not pick "Save & Run All" once conversion has finished —
that restarts from cell 1 and re-downloads."""),
]


def main() -> None:
    nb = {
        "cells": CELLS,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python",
                           "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(nb, indent=1), encoding="utf-8")
    print(f"wrote {OUT}  ({OUT.stat().st_size:,} bytes, {len(CELLS)} cells)")


if __name__ == "__main__":
    main()
