"""Assemble the site-suitability feature-extraction + clustering notebook.

Reads constants.npy / states.npy from the prep kernel's OUTPUT (attached as a
kernel input, no re-download), computes the geology + caprock-margin features
that already exist in src/leakage/{features,labels}.py, clusters the 1000
realisations, and writes a small CSV back as this kernel's output.

No GPU, no internet needed -- everything it reads is already local to Kaggle.
Regenerate with:

    python kaggle/make_suitability_notebook.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "notebooks" / "kaggle_site_suitability.ipynb"

# The two __init__.py files are empty, and Jupyter's %%writefile errors on an
# empty cell body, so they're created with a plain touch() instead of embedded.
FILES = [
    ("src/config.py", REPO / "src" / "config.py"),
    ("src/leakage/labels.py", REPO / "src" / "leakage" / "labels.py"),
    ("src/leakage/features.py", REPO / "src" / "leakage" / "features.py"),
]


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


def embed_file(rel_path: str, real_path: Path) -> dict:
    return code(real_path.read_text(encoding="utf-8"), f"%%writefile {rel_path}")


CELLS = [
    md("""# HyLeakAI — subsurface site-suitability screening

No GPU, no internet. Reads `constants.npy` / `states.npy` from the
**hyleakai-dataset-download-conversion** kernel's output (attached below as
an input, so nothing is re-downloaded), computes per-realisation geology and
caprock-margin features using the same code already tested in
`src/leakage/`, and clusters the 1,000 realisations into suitability groups.

**Before running:** *Add Input -> Notebook Output Files ->
sonilnegi/hyleakai-dataset-download-conversion*, so `/kaggle/input/` has the
converted arrays."""),

    code('''# Locate the converted arrays wherever Kaggle mounted the input kernel.
from pathlib import Path

candidates = list(Path("/kaggle/input").rglob("constants.npy"))
assert candidates, (
    "constants.npy not found under /kaggle/input. Add Input -> Notebook Output "
    "Files -> sonilnegi/hyleakai-dataset-download-conversion, then re-run.\\n"
    f"Currently mounted: {list(Path('/kaggle/input').iterdir())}"
)
DATA = candidates[0].parent
print("Using data from:", DATA)
print("contents:", sorted(p.name for p in DATA.iterdir()))'''),

    code('''# Recreate the src/ package layout this notebook needs (mirrors src/leakage/
# in the repo -- these are the exact tested files, embedded verbatim).
from pathlib import Path
Path("src/leakage").mkdir(parents=True, exist_ok=True)
Path("src/__init__.py").touch()
Path("src/leakage/__init__.py").touch()'''),

    *[embed_file(rel, path) for rel, path in FILES],

    code('''# Per-simulation geology + caprock-margin features, using the real
# src.leakage functions -- no reimplementation.
import sys
sys.path.insert(0, "/kaggle/working")

import numpy as np
import pandas as pd

from src import config as C
from src.config import LEAKAGE
from src.leakage.labels import caprock_margin
from src.leakage.features import geology_features

constants = np.load(DATA / "constants.npy", mmap_mode="r")   # (1000, 2, 128, 128) float32
states = np.load(DATA / "states.npy", mmap_mode="r")         # (1000, 60, 2, 128, 128) float16
n_sims = constants.shape[0]
print(f"{n_sims} simulations")

rows = []
for sim in range(n_sims):
    poro = np.asarray(constants[sim, C.CONST_POROSITY], np.float32)
    perm = np.asarray(constants[sim, C.CONST_PERMEABILITY], np.float32)
    geo = geology_features(poro, perm)

    # states stores pressure CENTRED (P_bar - P_INIT_BAR); the max centred
    # value across all 60 timesteps is exactly (P_max_bar - P_INIT_BAR), so
    # this is the peak pressure ever reached anywhere in this realisation.
    p_centred_peak = float(np.asarray(states[sim, :, C.STATE_PRESSURE], np.float32).max())
    p_max_bar = p_centred_peak + C.P_INIT_BAR
    margin = caprock_margin(np.array([p_max_bar], dtype=np.float32), LEAKAGE)

    rows.append({
        "sim_id": sim,
        **geo,
        "p_max_bar": margin["p_max_bar"],
        "caprock_margin_peak": margin["caprock_margin"],
    })
    if (sim + 1) % 200 == 0:
        print(f"  {sim + 1}/{n_sims}")

df = pd.DataFrame(rows)
df.to_csv("/kaggle/working/site_features.csv", index=False)
print(df.describe())'''),

    code('''# Cluster the 1000 realisations on geology + caprock margin only --
# deliberately NOT mixing in the fault-conditional leakage-risk model, so
# this stays a pure geological-suitability screen (module 1), separate from
# the fault-hypothesis risk model (module 2).
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

FEATURE_COLS = ["poro_mean", "poro_std", "logk_mean", "logk_std", "caprock_margin_peak"]
X = StandardScaler().fit_transform(df[FEATURE_COLS].values)

best_k, best_score, best_model = None, -1.0, None
for k in range(2, 7):
    km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(X)
    score = silhouette_score(X, km.labels_)
    print(f"k={k}  silhouette={score:.4f}")
    if score > best_score:
        best_k, best_score, best_model = k, score, km

print(f"\\nChosen k={best_k} (silhouette {best_score:.4f})")
df["cluster"] = best_model.labels_

summary = df.groupby("cluster")[FEATURE_COLS].agg(["mean", "count"])
print(summary)

df.to_csv("/kaggle/working/site_clusters.csv", index=False)
summary.to_csv("/kaggle/working/cluster_summary.csv")
print("\\nwrote site_clusters.csv, cluster_summary.csv")'''),

    md("""## Before you close the session

Save Version -> **Quick Save** to persist `site_clusters.csv` and
`cluster_summary.csv` as this kernel's output — small files, no large data to
keep around this time."""),
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
