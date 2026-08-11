"""HyLeakAI dashboard.

Given a geological realisation, run the U-Net surrogate across all ten years of
operation, extract physics features, and score leakage risk with the XGBoost
model — in about a second, versus hours for a reservoir simulation.

Run:
    streamlit run app/dashboard.py

The banner at the top is not decoration. Every risk number shown here rests on
a leakage label we DERIVED, because the source dataset contains no leakage
ground truth and we have no reservoir simulator. Anyone reading a number off
this screen needs to know that, so it is stated on the screen.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as C
from src.config import LEAKAGE
from src.data.lmdb_convert import restore_pressure
from src.leakage.features import (
    fault_features,
    geology_features,
    global_features,
    operational_features,
)
from src.leakage.labels import (
    distance_to_fault_field,
    fault_cell_mask,
    sample_faults,
)

st.set_page_config(page_title="HyLeakAI", page_icon="H", layout="wide")


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


@st.cache_resource
def load_fields(data_dir: str):
    d = Path(data_dir)
    if not (d / "states.npy").exists():
        return None, None
    return (
        np.load(d / "constants.npy", mmap_mode="r"),
        np.load(d / "states.npy", mmap_mode="r"),
    )


@st.cache_resource
def load_surrogate(ckpt_path: str, data_dir: str):
    """Returns (predict_fn, description) or (None, reason)."""
    p = Path(ckpt_path)
    if not p.exists():
        return None, f"no checkpoint at {ckpt_path}"
    import torch

    from src.data.dataset import Normalizer, UHSDataset
    from src.models.unet import build_unet, load_state_dict_compat

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt = torch.load(p, map_location=device, weights_only=False)
    meta = ckpt.get("meta", {})
    normalizer = Normalizer.from_file(Path(data_dir) / "stats.json")
    probe = UHSDataset("test", data_dir=Path(data_dir), normalizer=normalizer,
                       use_cyclic=meta.get("use_cyclic", True),
                       use_distance=meta.get("use_distance", True), sim_ids=[0])
    model = build_unet(meta.get("size", "small"),
                       in_channels=probe.in_channels, out_channels=2).to(device)
    load_state_dict_compat(model, ckpt["model"])
    model.eval()

    @torch.no_grad()
    def predict(sim: int):
        ds = UHSDataset("test", data_dir=Path(data_dir), normalizer=normalizer,
                        use_cyclic=probe.use_cyclic, use_distance=probe.use_distance,
                        sim_ids=[sim])
        x = torch.stack([ds.build_input_tensor(sim, t)
                         for t in range(1, C.N_TIMESTEPS + 1)]).to(device)
        out = model(x).cpu().numpy()
        return (
            normalizer.pressure_inverse(out[:, 0]).astype(np.float32),
            np.clip(out[:, 1], 0.0, 1.0).astype(np.float32),
        )

    return predict, f"U-Net-{meta.get('size', 'small')} on {device.type}"


@st.cache_resource
def load_risk_model(out_dir: str):
    """Returns (classifier, feature names, horizon in timesteps).

    The horizon is read from the saved results rather than hard-coded: the
    shipped model is selected by largest gain over a persistence baseline, so
    which horizon it is depends on the sweep, not on a constant in this file.
    """
    out = Path(out_dir)
    p = out / "xgb_classifier.ubj"
    if not p.exists():
        return None, None, None
    import xgboost as xgb

    clf = xgb.XGBClassifier()
    clf.load_model(p)
    feats = json.loads((out / "shap_features.json").read_text())
    horizon = None
    results = out / "xgb_results.json"
    if results.exists():
        horizon = json.loads(results.read_text()).get("report_horizon")
    return clf, feats, horizon


def truth_fields(states, sim: int):
    return (
        restore_pressure(states[sim, :, C.STATE_PRESSURE]),
        np.asarray(states[sim, :, C.STATE_SATURATION], np.float32),
    )


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------

st.title("HyLeakAI — predictive leakage risk for underground hydrogen storage")

st.warning(
    "**What these numbers are.** The source dataset (Mao et al. 2025) contains "
    "porosity, permeability, pressure and H2 saturation. It contains no faults, "
    "no caprock properties and **no leakage ground truth**, and we have no "
    "reservoir simulator. Risk here is computed against a **derived** target: a "
    "semi-analytical Darcy flux through a *hypothetical* fault overlaid on the "
    "predicted fields. Fault location, permeability and caprock thickness are "
    "sampled assumptions, not measurements. Treat the output as a physics-guided "
    "screening tool, not a calibrated leak-rate prediction."
)

with st.sidebar:
    st.header("Configuration")
    data_dir = st.text_input("Data directory", str(C.DATA_DIR))
    ckpt_path = st.text_input("U-Net checkpoint",
                              str(C.CHECKPOINT_DIR / "unet_small_best.pt"))
    out_dir = st.text_input("Model outputs", str(C.OUTPUT_DIR))

    constants, states = load_fields(data_dir)
    if states is None:
        st.error("No converted data found. Run `python -m src.data.lmdb_convert` first.")
        st.stop()

    test_ids = C.simulation_splits()["test"]
    sim = st.selectbox(
        "Simulation (held-out test set)", test_ids,
        format_func=lambda s: f"#{s}",
        help="Only test-set simulations are offered — the surrogate never saw these.",
    )

    predict_fn, surrogate_note = load_surrogate(ckpt_path, data_dir)
    source = st.radio(
        "Field source",
        ["Simulator (ground truth)", "U-Net surrogate"],
        help="Compare them to see how much surrogate error propagates into risk.",
        index=0 if predict_fn is None else 1,
    )
    if predict_fn is None:
        st.info(f"Surrogate unavailable ({surrogate_note}); showing simulator fields.")
        source = "Simulator (ground truth)"
    else:
        st.caption(f"Surrogate: {surrogate_note}")

    st.divider()
    st.subheader("Fault hypothesis")
    st.caption("The fault is not part of the simulation. It is overlaid on the "
               "fields, which is what lets us sweep unknown fault properties fast.")
    n_faults = st.slider("Monte-Carlo fault realisations", 5, 100, 25, step=5)
    fault_seed = st.number_input("Sampling seed", value=int(LEAKAGE.rng_seed), step=1)

# ---- fields ----
with st.spinner("Computing fields..."):
    if source.startswith("U-Net"):
        pressure, saturation = predict_fn(sim)
    else:
        pressure, saturation = truth_fields(states, sim)
    poro = np.asarray(constants[sim, C.CONST_POROSITY], np.float32)
    perm = np.asarray(constants[sim, C.CONST_PERMEABILITY], np.float32)

timestep = st.slider("Timestep (2 months each; 60 steps = 10 years)",
                     1, C.N_TIMESTEPS, 30)
i = timestep - 1
stage = "INJECTION" if C.cycle_index(timestep) == 1 else "WITHDRAWAL"
st.caption(f"Cycle {C.cycle_number(timestep)} of {C.N_CYCLES} — **{stage}** — "
           f"month {timestep * C.MONTHS_PER_STEP} of {C.N_CYCLES * 12}")

# ---- maps ----
c1, c2, c3 = st.columns(3)
extent = [0, C.DOMAIN_M / 1000, 0, C.DOMAIN_M / 1000]
for col, (field, title, cmap) in zip(
    (c1, c2, c3),
    [
        (saturation[i], "H2 saturation", "viridis"),
        (pressure[i], "Pressure (bar)", "inferno"),
        (np.log10(np.maximum(perm, 1e-3)), "log10 permeability (mD)", "cividis"),
    ],
):
    fig, ax = plt.subplots(figsize=(4, 3.4))
    im = ax.imshow(field, cmap=cmap, extent=extent, origin="lower")
    ax.plot(C.DOMAIN_M / 2000, C.DOMAIN_M / 2000, "w*", ms=13, mec="k", label="well")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("km")
    plt.colorbar(im, ax=ax, fraction=0.046)
    col.pyplot(fig, use_container_width=True)
    plt.close(fig)

# ---- risk ----
faults = sample_faults(n_faults, LEAKAGE, seed=int(fault_seed))
geo = geology_features(poro, perm)
glob = global_features(pressure[i], saturation[i], poro,
                       pressure[i - 1] if i > 0 else None,
                       saturation[i - 1] if i > 0 else None)

rows, q_now = [], []
for f in faults:
    dist = distance_to_fault_field(f)
    mask = fault_cell_mask(dist)
    ff = fault_features(pressure[i], saturation[i], poro, perm, f, dist, mask)
    q_now.append(ff.pop("_q_now_m3_s"))
    rows.append({**glob, **geo, **ff, **operational_features(timestep)})

q_now = np.array(q_now)
clf, feat_names, horizon = load_risk_model(out_dir)
horizon_months = horizon * C.MONTHS_PER_STEP if horizon else None

st.divider()
st.subheader("Leakage risk across the fault ensemble")
if horizon:
    target_t = min(timestep + horizon, C.N_TIMESTEPS)
    target_stage = "INJECTION" if C.cycle_index(target_t) == 1 else "WITHDRAWAL"
    st.caption(
        f"Forecast **{horizon_months} months ahead** (timestep {target_t}, "
        f"a **{target_stage}** stage). This horizon is half a storage cycle, "
        f"chosen because it is where the model most outperforms a persistence "
        f"baseline — at a whole number of cycles the fields simply repeat and "
        f"copying today's value already scores ~0.99, so a high score there "
        f"would measure periodicity rather than skill."
    )

m1, m2, m3, m4 = st.columns(4)
m1.metric("Peak pressure", f"{glob['p_max_bar']:.1f} bar",
          f"{glob['delta_p_bar']:+.1f} vs initial")
m2.metric("Plume area", f"{glob['plume_area_m2'] / 1e6:.2f} km²")
m3.metric("Caprock margin", f"{glob['caprock_margin']:.3f}",
          help="(P_max - P_init) / (P_frac - P_init). P_frac uses an ASSUMED "
               "fracture gradient; >1 would mean exceedance.")
m4.metric("Faults with non-zero flux", f"{int((q_now > 0).sum())} / {n_faults}")

if clf is not None and feat_names:
    X = np.array([[r.get(k, 0.0) for k in feat_names] for r in rows], np.float32)
    proba = clf.predict_proba(X)[:, 1]
    ml, mr = st.columns([2, 1])
    with ml:
        fig, ax = plt.subplots(figsize=(7, 3.2))
        ax.hist(proba, bins=20, range=(0, 1), color="#c44", edgecolor="k", alpha=0.8)
        ax.set_xlabel(f"P(elevated leakage in {horizon_months} months)")
        ax.set_ylabel("fault realisations")
        ax.set_yscale("log")
        ax.set_title("Risk across sampled fault hypotheses")
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
    with mr:
        # Only ~2% of fault-timestep combinations are positive by construction,
        # so the median is almost always 0 and says nothing. The tail is the
        # decision-relevant part.
        st.metric("Worst-case fault", f"{proba.max():.3f}")
        st.metric("Faults above 0.5", f"{int((proba > 0.5).sum())} / {n_faults}")
        worst = faults[int(np.argmax(proba))]
        st.caption(
            f"Worst case: fault {worst.length_m:,.0f} m long, "
            f"{worst.permeability_m2:.2e} m² permeable, "
            f"{np.hypot(worst.x_m - C.DOMAIN_M / 2, worst.y_m - C.DOMAIN_M / 2):,.0f} m "
            f"from the well."
        )
else:
    st.info(
        "Risk model not trained yet. Run `python -m src.build_features` then "
        "`python -m src.train_xgb` to enable the probability panel. The physics "
        "flux below is available regardless."
    )
    fig, ax = plt.subplots(figsize=(7, 3.2))
    positive = q_now[q_now > 0]
    if positive.size:
        ax.hist(np.log10(positive), bins=20, color="#c44", edgecolor="k", alpha=0.8)
        ax.set_xlabel("log10 fault flux (m³/s)")
    else:
        ax.text(0.5, 0.5, "No fault carries flux at this timestep\n"
                          "(withdrawal stage, or no mobile H2 on any fault)",
                ha="center", va="center")
        ax.set_xticks([])
    ax.set_ylabel("fault realisations")
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

# ---- trajectory ----
st.divider()
st.subheader("Ten-year risk trajectory")
st.caption("The point of the surrogate: this whole trajectory is produced in "
           "about a second, where a reservoir simulation would take hours.")

worst_idx = int(np.argmax(q_now)) if q_now.max() > 0 else 0
f = faults[worst_idx]
dist = distance_to_fault_field(f)
mask = fault_cell_mask(dist)
traj = [
    fault_features(pressure[k], saturation[k], poro, perm, f, dist, mask)["_q_now_m3_s"]
    for k in range(C.N_TIMESTEPS)
]

fig, ax = plt.subplots(figsize=(11, 3.4))
steps = np.arange(1, C.N_TIMESTEPS + 1)
ax.plot(steps, traj, lw=1.6, color="#c44")
ax.fill_between(steps, 0, traj, alpha=0.25, color="#c44")
for cyc in range(C.N_CYCLES):
    ax.axvspan(cyc * C.STEPS_PER_CYCLE + 0.5,
               cyc * C.STEPS_PER_CYCLE + C.INJECTION_STEPS_PER_CYCLE + 0.5,
               color="#59f", alpha=0.10)
ax.axvline(timestep, color="k", ls="--", lw=1)
ax.set_xlabel("timestep (2 months each)")
ax.set_ylabel("fault flux (m³/s)")
ax.set_title("Highest-flux fault in the ensemble — blue bands are injection stages")
st.pyplot(fig, use_container_width=True)
plt.close(fig)
st.caption("Flux is zero throughout every withdrawal stage by construction: "
           "below the initial reservoir pressure there is no upward driving "
           "force, so hydrogen does not migrate up the fault.")
