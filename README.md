# HyLeakAI

Physics-guided leakage-risk screening for **underground hydrogen storage (UHS)**.

A U-Net surrogate learns reservoir flow from geology, physics features are
extracted from its predicted fields, and a gradient-boosted model scores leakage
risk against a hypothesised fault — turning a multi-hour reservoir simulation
into a sub-second screening pass that can be Monte-Carlo'd over unknown fault
properties.

```
geology (phi, k)  ->  U-Net surrogate  ->  pressure + H2 saturation fields
                                                    |
                                        physics feature extraction (41)
                                                    |
                                      + hypothesised fault realisation
                                                    |
                                    XGBoost -> P(elevated leakage in 6 months)
                                                    |
                                              SHAP attribution
```

---

## Read this before quoting any number

The source dataset contains **porosity, permeability, pressure and H2
saturation** — nothing else. No faults, no caprock properties, **no leakage**.
We have no reservoir simulator.

So the split is:

- **Features are real.** From Mao et al.'s 1,000 tNavigator physics simulations.
- **Leakage labels are ours.** A semi-analytical Darcy flux through a
  *hypothetical* fault whose position, permeability, length and width we sample.

This is a **physics-guided screening tool, not a calibrated leak-rate
predictor**. `docs/FINDINGS.md` records every measurement behind that statement,
including the two targets we tried and dropped. Read it before writing anything
up.

---

## Status vs. the original scope, and what's next

`Document 9.pdf` (the original pitch) proposed four modules. Here's what
actually exists today and what doesn't:

| # | Module | Status | What's built |
|---|---|---|---|
| 1 | **Geological / subsurface intelligence** — screen candidate sites for storage suitability (caprock stability, fault zones) | 🟡 **Prototype built** | `src/site_suitability.py` ranks all 1,000 realisations by a weighted composite of storage capacity, caprock seal risk, and heterogeneity — see `docs/SITE_SUITABILITY.md`. Clustering was tried first and dropped (weak silhouette, geology features are collinear — a continuum, not discrete site types). **Frontend built** — the Storage Atlas panel in `app/web/index.html` plots all 1,000 sites on real output, with live re-weighting. |
| 2 | **AI leakage prediction engine** | ✅ **Built, narrower scope** | U-Net surrogate + XGBoost risk model + SHAP, described above. Predicts leakage risk for a hypothesised fault, not the full original list (no explicit "safe injection pressure limit" output yet, though the caprock margin feature it would come from already exists). |
| 3 | **Digital twin & visualisation dashboard** | 🟡 **Partial** | Two frontends, for two purposes. `app/dashboard.py` (Streamlit) is the local research tool — risk trajectory, fault-ensemble sweep, SHAP attribution — and needs the full 12.38 GB dataset, so it cannot be deployed. `app/web/index.html` is the deployable one: a self-contained page with a 2.5D reservoir slab, spatial fault swarm and cycle-ribbon timeline, plus a **Live model** mode that calls the deployed FastAPI service (`api/`, see `docs/PRODUCT_API_PLAN.md`) for real U-Net + XGBoost risk numbers — the risk panel and its SHAP attribution are genuine in that mode. Preview mode's reservoir and risk panels remain procedural mockups. The visual field render itself is illustrative even in Live mode; only the numbers underneath it are real. See `docs/FRONTEND.md`. |
| 4 | **Economic & operational optimisation** | ✅ **Built, reframed** | `src/economics/` — and it deliberately reports **no ROI**. An ROI needs a leak rate, and no leakage ground truth exists anywhere in the world (that absence is the project's premise), so pricing our own uncalibrated label would be a guess wearing a currency symbol. Instead `voi.py` computes **Value of Information** — what the screen is worth in *decisions changed* — whose headline output is dimensionless. Result: 20,000 screened fault hypotheses capture **0.9974** of the available decision value; **two exact simulator runs capture 0.00**, and so do twenty. Coverage is what is scarce, not accuracy. Also reports the regime where the screen would be worth **less than nothing** (below a mitigation/loss ratio of 6.2e-5) — which sits *below* the plausible range, so across every credible ratio it never destroys value. Supporting modules: `fluids.py` (CoolProp evidence for the CH₄-next / not-CO₂ claim), `assumptions.py` (provenance register that refuses to give an UNVERIFIED quantity a point value), `unit_cost.py` (0.652 vCPU-seconds per pass, marginal cost per hypothesis indistinguishable from zero). Full explanation in `Economics_and_impact.md`; slide-ready version in `docs/COMMERCIAL.md`. Supersedes the differential-ROI spec in `Build_Plan.md`. |

**Path ahead, in order:**

1. ~~**Site-suitability frontend.**~~ **Done** — the Storage Atlas panel in
   `app/web/index.html`, on real output from
   `outputs/site_suitability_ranking.csv`.
2. ~~**Wire the web frontend's risk panel to real model output.**~~ **Done** —
   a FastAPI service (`api/`, deployed at `hyleak-api-demo.onrender.com`)
   serves live U-Net + XGBoost assessments, and the frontend's **Live model**
   mode calls it end-to-end. See `docs/PRODUCT_API_PLAN.md` and
   `test_results/` for the production smoke tests. The reservoir *visual*
   is still a procedural illustration in both modes — only the demo-pack
   export (below) would make that real too.
3. **Demo-pack export for the reservoir visual.** ~24 held-out simulations
   exported from Kaggle as quantised PNG sprite sheets, ≈2 MB per simulation,
   so the field render itself (not just the risk numbers) can be real without
   the 12.38 GB dependency. Full plan, arithmetic and open questions in
   `docs/FRONTEND.md`.
4. **Safe injection pressure limit.** Derive an explicit max-safe-pressure
   number from the caprock margin feature that already exists, and surface
   it on the dashboard — closes most of the gap in module 2.
5. ~~**Economics module.**~~ **Done, and deliberately not as specced.**
   `src/economics/` — the differential-ROI spec in `Build_Plan.md` was
   dropped because every route to a currency figure runs through a leak rate
   nobody can calibrate. `voi.py` computes **Value of Information** instead,
   whose headline output is dimensionless. See `Economics_and_impact.md`.
6. **Dashboard: geology/fault-zone map.** Add a plan-view panel (porosity,
   permeability, fault-activation zones) to close the gap toward an actual
   "digital twin" view, rather than just the risk-trajectory charts it has
   now.

---

## Results

**U-Net surrogate** — architecture verified against the paper's Table 1:

| Variant | Embedding | Our params | Paper |
|---|---|---|---|
| Small (in use) | 32 | 7,764,674 | 7.7M |
| Medium | 64 | 31,043,586 | 31M |
| Large | 128 | 124,120,706 | 124M |

Training runs on Kaggle (`notebooks/kaggle_train_unet.ipynb`). Target is
relative L2 ~0.06–0.10 saturation, ~0.09–0.13 pressure; the paper's best
(U-Net-Large on an A100) is 0.0577 / 0.0861.

**Leakage risk** — horizon sweep on the held-out test split, 1,000 simulations:

| Horizon | Months | Cycle phase | Model PR-AUC | Persistence | Gain |
|---|---|---|---|---|---|
| 1 | 2 | different | 0.9949 | 0.4224 | +0.5725 |
| **3** | **6** | **different** | **0.9931** | **0.0218** | **+0.9714** |
| 6 | 12 | same | 0.9975 | 0.9918 | +0.0057 |
| 12 | 24 | same | 0.9960 | 0.9758 | +0.0202 |
| 30 | 60 | same | 0.9918 | 0.9125 | +0.0792 |

**Does the surrogate's error matter?** The risk model is trained once on
simulator features and never retrained, then scored on both field sources over
150 held-out simulations:

| Field source | PR-AUC | log-flux R² | RMSE |
|---|---|---|---|
| Simulator | 0.9941 | +0.9714 | 0.739 |
| **U-Net surrogate** | **0.9842** | +0.9200 | 1.236 |

**The surrogate retains 99.0% of the simulator's PR-AUC** — so risk *screening*
survives a ~16% pressure error almost intact, which is what justifies using a
surrogate at all. Magnitude estimation degrades more (flux predicted within
~17x rather than ~5.5x), which is why the claim here is screening, not
quantitative leak-rate prediction.

**The persistence column is the one that matters.** At any horizon that is a
whole number of storage cycles, the fields repeat and simply copying today's
value already scores ~0.99 — a high model score there measures the reservoir's
annual periodicity, not forecasting skill. Horizon 3 (half a cycle) is the
reported task because persistence collapses there to 0.0218, *below* the 2.3%
base rate.

---

## Setup

```bash
pip install -r requirements.txt
```

## Pipeline

```bash
# 1. Data: download 12.38 GB from Zenodo (resumable, parallel), then convert
python -m src.data.download                  # verifies against the published MD5
python -m src.data.lmdb_convert              # -> constants.npy, states.npy, stats.json

# 2. Validate the dataset and settle the T1 go/no-go question
python -m src.explore

# 3. Leakage physics self-checks (monotonicity of the T3 model)
python -m src.leakage.labels

# 4. Feature table: 1.18M rows x 41 features, all horizons in one pass (~2 min)
python -m src.build_features --workers 12

# 5. Risk model: horizon sweep vs persistence, then SHAP (~10 min)
python -m src.train_xgb --table data/features.npy --n-jobs 12

# 6. Local research dashboard (needs the converted dataset from step 1)
streamlit run app/dashboard.py
```

## Frontend

`app/web/index.html` is the deployable frontend: one self-contained file, no
server, no build step, and **no dataset** — open it directly, or serve it
anywhere static.

```bash
open app/web/index.html
```

Its Storage Atlas panel runs on real output (all 1,000 sites from
`outputs/site_suitability_ranking.csv`). Its reservoir and risk panels are
labelled mockups using procedural stand-in fields — **nothing on those two
panels is model output, and the page says so on itself.** `docs/FRONTEND.md`
records the design direction, exactly what is real, and the plan to make the
rest real.

Pushing to `main` deploys it to GitHub Pages via `.github/workflows/pages.yml`,
which needs Settings → Pages → Source → GitHub Actions set once by hand.

**U-Net training** goes on Kaggle — see below. There is no local GPU path worth
taking: measured at ~4 hours per epoch on a 16-core CPU versus ~3–5 minutes on
a T4.

## Training the surrogate on Kaggle

Upload `notebooks/kaggle_train_unet.ipynb` (File → Import Notebook). It is
self-contained: it writes its own sources, fetches the dataset from Zenodo,
converts, verifies, and trains.

1. **Settings → Accelerator → GPU T4 ×2.** Not P100 — it is compute capability
   6.0 (Pascal) and current PyTorch builds ship no Pascal kernels. Cell 1 checks
   this explicitly and fails in seconds rather than 30 minutes in.
2. **Settings → Internet → On.**
3. Run all. Expect ~3–5 min/epoch, so 120 epochs ≈ two sessions.
4. **Save Version → Save & Run All** before closing, or the session is discarded.
5. To resume: new session → *Data → Add Input* → previous output → set
   `PREV_OUTPUT` in cell 2 → run all.

Checkpoints are written **every epoch**, **atomically** (`.tmp` then move), in
three tiers: `_best.pt` (lowest validation loss), `_last.pt` (exact resume —
model + optimizer + scheduler + history), and numbered `_epochNNN.pt` archival
snapshots every 10 epochs. Resume falls back through the snapshots newest-first,
so a damaged `_last.pt` costs a few epochs rather than the run.

## Layout

```
src/
  config.py                 all constants, tagged [DATASET] / [DERIVED] / [ASSUMED]
  explore.py                dataset validation + T1 go/no-go
  build_features.py         multi-horizon feature table (parallel)
  train_unet.py             surrogate training (local / CPU fallback)
  train_xgb.py              horizon sweep, persistence baseline, SHAP
  data/                     download, LMDB conversion, PyTorch dataset
  models/unet.py            U-Net + relative-L2 loss + paper parameter check
  leakage/
    labels.py               T1/T2/T3 targets + physics self-checks
    features.py             41 physics features, multi-horizon labels
kaggle/                     self-contained modules + notebook generator
notebooks/                  kaggle_train_unet.ipynb
app/dashboard.py            Streamlit dashboard (local only — needs the dataset)
app/web/index.html          deployable frontend, self-contained, no dataset
docs/FINDINGS.md            every measurement, including the negative results
docs/SITE_SUITABILITY.md    the site-ranking module, including what didn't work
docs/FRONTEND.md            frontend direction, what's real vs. mocked, next steps
```

## Verification built into the pipeline

Each of these is an assertion in the code, not a manual step:

- **Download** checked against the Zenodo MD5.
- **Conversion** round-tripped against the LMDB, with tolerances *derived from
  float16 resolution* rather than chosen to pass.
- **Architecture** checked against the paper's reported weight counts before any
  training step.
- **Overfit test** on 4 simulations, to catch channel-ordering and normalisation
  bugs before committing hours.
- **Split disjointness** asserted by simulation ID at both the U-Net and XGBoost
  stages — a simulation is never in one stage's training set and another's test
  set.
- **Leakage physics** monotonicity: flux must rise with fault permeability and
  overpressure, and be exactly zero during withdrawal and below residual gas
  saturation.
- **Persistence baseline** reported alongside every risk score, with horizons
  where persistence exceeds 0.9 PR-AUC flagged as "not a forecasting task".

## Source

Mao, S., Carbonero, A., & Mehana, M. (2025). *Deep learning for subsurface flow:
A comparative study of U-Net, Fourier neural operators, and transformers in
underground hydrogen storage.* JGR: Machine Learning and Computation, 2,
e2024JH000401. <https://doi.org/10.1029/2024JH000401>

Dataset: <https://zenodo.org/records/14029514> (CC-BY-4.0 / MIT)
