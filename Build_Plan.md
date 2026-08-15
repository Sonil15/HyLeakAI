# HyLeakAI — Build Plan & Compute Analysis

> **Superseded.** This plans the custom Volve-based VE/IMPES simulator and
> its hackathon schedule, including the Economics module spec below. Neither
> the simulator nor the dashboard-as-planned was built, and **the economics
> module was built for the finals but not as specced below** — the
> differential-ROI design was dropped because every route to a currency figure
> runs through a leak rate nobody can calibrate. `src/economics/voi.py`
> computes Value of Information instead, whose headline output is
> dimensionless; see [`Economics_and_impact.md`](Economics_and_impact.md). The
> assumption register in §Economics below **did** survive, and is now enforced
> in code by `src/economics/assumptions.py`. The project pivoted to Mao et
> al.'s published UHS dataset
> (Zenodo 14029514) with a U-Net surrogate + XGBoost risk model. See
> [`README.md`](README.md) for what actually shipped, what's still missing
> against the original 4-module scope in `Document 9.pdf`, and the current
> path ahead. Kept here as historical record — the compute benchmarks (Part
> I) and the Economics section's reasoning still hold if that module gets
> built later.

**Written:** 2026-08-09 · **Deadlines:** basic prototype 2026-08-11, improved 2026-08-14
**Supersedes:** §4–§6 of `Data_sources_research.md` (physics and data sources in §1–§3 there still stand)
**Team:** 3 people — 1× MacBook Air M1 (8 GB, fanless), 2× Windows laptops with entry-level GPUs
**Companion doc:** `Feasibility_assessment.md` — same benchmarks, evidence-first framing

---

## 0. What this document is

Part I explains the compute analysis: what was measured, on what hardware, and which numbers changed the plan. Part II is the resulting phase-wise build plan with time budgets grounded in those measurements.

The one-line summary: **the original 2-day plan was ~300× over budget on its single largest task**, for a reason that is fixable in an afternoon. After the fix, compute stops being the constraint anywhere in the project, and the schedule is limited by writing code and building UI.

---

# Part I — Compute & Timing Analysis

## 1. Method

Everything below was **measured on the actual M1 Air**, not estimated from specs. Four benchmark scripts were written and run:

| Script | Measures |
|---|---|
| `bench2.py` | Per-timestep cost of a 2D IMPES solver vs grid size and linear solver; CFL step counts |
| `bench3.py` | Cost of each candidate fix; CoolProp call cost |
| `bench_par2.py` | Parallel scaling with realistic multi-second jobs; sustained-load throttling |
| `real_sim.py` | A complete 2D IMPES H₂/brine solver (gravity, adaptive CFL, upwind fractional flow) run end to end |

Scripts are in the session scratchpad:
`/private/tmp/claude-501/-Users-sonil-Desktop-HyLeakAI/cec8609d-1959-473b-aefd-45904c323cab/`

## 2. The error in the original plan

`Data_sources_research.md` §3 correctly concludes that **hydrogen escapes by buoyancy, not by viscous flow** — H₂ is only 1.3–2.1× less viscous than methane, but ~9–10× less dense. §4 then costs the simulator (60×80 cells, "2–10 s per run") without carrying that conclusion into the numerics.

That is exactly where it breaks. Buoyancy is what makes explicit timestepping expensive.

**The derivation.** Buoyancy-driven Darcy velocity:

```
v = k · Δρ · g / μ_H₂
  = (200 mD = 1.97e-13 m²)(980 kg/m³)(9.81 m/s²) / (1.05e-5 Pa·s)
  = 16.6 m/day
```

An explicit saturation update is stable only under the CFL condition `dt ≤ φ·dz / (v · df/dS)`. With `dz = 100 m / 80 = 1.25 m`, `φ = 0.22`, and `df/dS ≈ 4`:

```
dt ≤ 0.22 × 1.25 / (16.6 × 4) = 0.0041 days ≈ 0.1 hours
```

Three years of injection/withdrawal cycling therefore needs **~265,000 timesteps**, each requiring a sparse pressure solve.

**Measured cost of one timestep** (assemble + solve + transport):

| Grid | Cells | spsolve | splu | CG |
|---|---:|---:|---:|---:|
| 30×40 | 1,200 | 3.4 ms | 2.9 ms | 23.6 ms |
| **60×80** | **4,800** | **12.5 ms** | **12.3 ms** | 49.4 ms |
| 100×120 | 12,000 | 38.7 ms | 38.7 ms | 182.0 ms |
| 150×200 | 30,000 | 144.2 ms | 135.0 ms | 825.3 ms |

`265,000 × 12.3 ms` = **54 minutes per run** — against a claimed 2–10 s. In 1 D permeability rock it is **4.5 hours**.

Note also that **CG is 4–6× slower than a direct solve** at these sizes. Don't reach for an iterative solver here; the matrices are too small for it to pay off.

**Confirmed end to end.** A complete IMPES solver, run for the full 3-year schedule:

| Grid | Cells | Steps (3 yr) | Measured runtime |
|---|---:|---:|---:|
| 40×12 | 480 | 11,518 | **12.2 s** ✅ |
| 60×20 | 1,200 | 24,799 | **68.8 s** ⚠️ |
| 60×80 | 4,800 | — | **did not finish in 20 min** ❌ |

Scaling is worse than linear in cell count: halving `dz` both doubles the step count *and* raises per-step cost. This is why grid refinement is punishingly expensive here and why the fix below works so well.

**Consequence for the schedule:** 300 runs × 54 min = **11 days**, for a task budgeted at 1 hour.

## 3. The three fixes

### Fix 1 — Grid 60×80 → 40×12 (dz = 8.3 m, not 1.25 m)

Vertical cell size drives the CFL limit linearly, so coarsening `dz` by 6.7× buys back 6.7× in step count *and* ~4× in per-step cost.

- **Measured: 12.2 s per 3-year run.** Holds under stress: 15.4 s at 500 mD, 26.6 s at 1 D.
- 300 runs = 61 min serial → **~23 min on 6 cores**.
- Cost: vertical plume resolution. For four scalar labels (% lost, breakthrough day, plume extent, peak pressure) that is acceptable — **state it in the limitations slide.**

### Fix 2 — Tabulate CoolProp; never call it inside the solver loop

Measured `PropsSI` scalar call: **280–300 µs**. Roughly 25,000× slower than an equivalent NumPy array operation.

| Usage pattern | Cost per run |
|---|---|
| Per cell, per timestep | **99 CPU-hours** ☠️ |
| Once per timestep | 74 s — still 6× the entire per-run budget |
| **Precomputed 40×40 (T,p) table + interpolation** | **0.45 s once, ~1 µs per lookup** ✅ |

Build the table at startup; use `np.interp` or `RegularGridInterpolator` thereafter. This is a silent project-killer — it doesn't error, it just makes everything 100× slower than expected.

### Fix 3 — Build the vertical-equilibrium model first, IMPES second

A vertical-equilibrium (VE) / sharp-interface model — the standard reduced-order approach for buoyancy-dominated CO₂ and H₂ storage — integrates vertically and solves for plume thickness `h(x,t)` instead of a full 2D saturation field.

| Model | Per run | 300 runs |
|---|---:|---:|
| **VE, nx=200, dt=1 d** | **0.043 s** | **13 s** |
| VE, nx=400, dt=0.25 d | 0.153 s | 46 s |
| IMPES 40×12 | 12.2 s | 61 min |

**280× faster**, ~100 lines, and hard to get catastrophically wrong. The original plan lists this as the panic fallback for if you're stuck by lunch. Promoting it to the *first* deliverable inverts the project's risk profile: right now every downstream component — dataset, model, dashboard, demo — is blocked behind the single hardest piece of code.

Build VE → lock the full pipeline end to end → upgrade the simulator with time remaining.

## 4. Hardware reality

### Parallel scaling on the M1 (measured, realistic multi-second jobs)

| Workers | Speedup | Efficiency |
|---:|---:|---:|
| 1 | 0.99× | 99% |
| 2 | 1.75× | 88% |
| 4 | 2.33× | 58% |
| 8 | **3.13×** | 39% |

**Plan for ~3×, not 8×.** The M1 has 4 performance + 4 efficiency cores and the E-cores contribute little. Use `multiprocessing.Pool(6)`; beyond 6 you pay scheduling cost for negligible gain.

An earlier quick test suggested only 2.15×, but that was contaminated by `Pool` spawn overhead on short jobs — with realistic multi-second jobs the true figure is 3.13×.

### Thermal throttling (measured, 6 min sustained load, 8 workers)

Throughput settles at **80–90% of cold-start**, with occasional dips to ~68%. This is **milder than the 30–40% previously assumed** — roughly a 15% haircut.

**Combined planning factor: ~2.6× effective speedup on the M1.**

### Teammates' Windows laptops — the best lever available

The LHS sweep is embarrassingly parallel with zero inter-process communication.

- Pure NumPy/SciPy. No GPU, no CUDA, no install friction beyond `pip install numpy scipy`.
- A 4-core Windows laptop contributes roughly what the M1 does. **Three machines ≈ 3× throughput.**
- ⚠️ **Seed each run's RNG from its row index in the design matrix**, never from wall-clock time or worker ID. Otherwise slices can't be reconciled, re-run, or debugged.

### Google Colab / Kaggle — skip them

| Resource | Offers | Verdict |
|---|---|---|
| Colab free | ~2 vCPU, T4 when available, idle timeout | **Downgrade** — 2 vCPU vs your 8 |
| Kaggle free | ~4 vCPU, ~30 GB RAM, ~30 GPU-h/wk, 12 h sessions | 4 vCPU ≈ half the M1; GPU unused |

Two structural reasons, not just "the numbers are close":

1. **The simulation cannot use a GPU.** It is sequential sparse LU factorization with a hard data dependency between timesteps. There is no GPU port writable in two days.
2. **The ML doesn't need one** (§5 below).

The one defensible use: Kaggle's 12-hour sessions as **extra free CPU workers** for an overnight 1,000-run sweep. Even that is optional — 1,000 IMPES runs across three laptops is ~1.2 hours.

*(Free-tier specs change; treat the table as approximate. The conclusion depends on the sim being CPU-sequential, which is structural, not on the exact vCPU counts.)*

## 5. ML stage — all local, all cheap

Measured on the M1:

| Model | Cost | Notes |
|---|---|---|
| HistGradientBoosting, 4 targets, 300×8 | **2.2 s total** | Original plan is right to prefer this over deep learning at n=300 |
| U-Net (117k params), 300 samples, 200 epochs | **13.3 min CPU / 2.4 min MPS** | `torch.backends.mps.is_available()` → `True`. Use it. |
| LSTM (2×64) on Volve history, 100 epochs | **1.5 min** | Trivial |
| PINN (6×64, 4096 collocation pts, 2nd-order autograd) | 29 ms/iter → **9.6 min** / 20k iters | Cheap to run, expensive to get right |

**The PINN's cost is not compute.** 9.6 minutes of training is nothing; the risk is the original plan's own warning — the PDE in the loss must match the simulator's governing equation, or it fails silently. A VE simulator has a much simpler governing equation, which makes the PINN *more* tractable. Still last priority.

## 6. Environment blockers found

### ⚠️ `import torch` before `sklearn` segfaults this machine

Reproduced deterministically, exit code 139, **no Python traceback**:

```python
import torch
from sklearn.ensemble import HistGradientBoostingRegressor
HistGradientBoostingRegressor().fit(X, y)   # SIGSEGV
```

Duplicate OpenMP runtime (Anaconda `libomp` vs PyTorch's). `KMP_DUPLICATE_LIB_OK=TRUE` **does not fix it** — verified. What works is import order:

```python
from sklearn.ensemble import HistGradientBoostingRegressor   # sklearn FIRST
import torch                                                  # torch second
```

Apply in every file including the Streamlit app. Because it crashes with no traceback it reads as a hardware fault — easy to lose hours to at 2am.

### Disk: 3.7 GB free (99% full)

Less blocking than feared for *packages*: numpy, scipy, sklearn, pandas, matplotlib, streamlit, plotly, CoolProp and torch 2.11 are **already installed**. Only `xgboost` is missing and `HistGradientBoostingRegressor` substitutes fine — don't spend disk on it.

The real risk is macOS: under 4 GB free with 8 GB RAM, swap has nowhere to grow and the machine stalls mid-demo. **Free 15–20 GB before Phase 1.**

Data footprint is genuinely small — the labels CSV is ~50 KB; 300 saturation maps at 64×64 float32 are ~4.9 MB.

---

# Part II — The Build Plan

## Where the three fixes land

| Fix (Part I §3) | Lands in | Enforced by |
|---|---|---|
| **1** — grid 40×12, `dz` = 8.3 m | Phase 2a | Budget check: 12.2 s/run |
| **2** — precomputed CoolProp table | Phase 1a | Budget check: 0.043 s/run; assert in sweep script |
| **3** — VE simulator before IMPES | Phase 1 ordering (whole phase) | Phase 1 checkpoint at mid-afternoon |

Each fix has a **numeric tripwire**, not just a note. If a budget check fails, the cause is almost always the thing the fix addresses — that's the point of stating them as thresholds.

## Phase 0 — Setup (45 min, everyone)

- [ ] **Free 15–20 GB on the M1.** Non-negotiable; do it first.
- [ ] `pip install numpy scipy pandas scikit-learn matplotlib streamlit plotly CoolProp` (skip xgboost)
- [ ] Verify the import-order fix on every machine: sklearn before torch
- [ ] Download SUHS-MRV (3.7 MB) + Volve ECLIPSE model (~30 MB). **Not the seismic.**
- [ ] Agree the design-matrix contract now: 8 input columns, 4 output columns, `run_id` = row index, RNG seeded from `run_id`

## Phase 1 — VE simulator + full pipeline (Day 1, ~6 h)

**Goal: an ugly but complete pipeline by end of day.** Data → simulation → labels → model → dashboard, all working end to end. This is the deliverable that de-risks everything else.

**This whole phase ordering *is* Fix 3** — VE before IMPES. The point is not that VE is better; it's that building it first unblocks 1b–1d immediately, so a slipping simulator can no longer sink the dashboard, the model, and the demo with it.

**1a. VE simulator (2–3 h)**
- Sharp-interface plume thickness `h(x,t)`, ~100 lines, nx = 200
- Buoyancy flux `q = -k·Δρ·g/μ · h · ∂h/∂x`, reservoir below / seal above, leaky old well as a high-perm column
- Fluid properties from a **precomputed CoolProp table** (Fix 2)
- 3 cycles × (6 mo injection / 6 mo withdrawal)
- Emit 4 labels: % H₂ lost, days to breakthrough, plume extent, peak well pressure
- **Budget check: 0.043 s/run.** If you're above ~0.5 s, something is wrong — likely CoolProp in the loop.

**1b. Dataset (15 min compute)**
- 8 inputs: permeability, porosity, seal thickness, seal permeability, injection rate, well seal quality, depth, temperature
- Ranges taken from the Volve model — this is what makes it credible
- Latin hypercube, **300 runs → 13 s**. Cheap enough to regenerate freely, so don't over-plan the design.

**1c. Model (30 min)**
- `HistGradientBoostingRegressor` per target — 2.2 s total
- R² on a held-out 20%, feature-importance chart
- Not deep learning. At n=300 gradient boosting wins and trains instantly.

**1d. Streamlit skeleton (2 h)**
- 8 sliders → live prediction
- One pre-computed migration heatmap
- Reservoir Health Score (scale predicted loss to 0–100)

> **Checkpoint:** if 1a isn't producing labels by mid-afternoon, ship a single-phase pressure solve plus a buoyancy rule and move on. A finished ugly pipeline beats a beautiful half-pipeline.

## Phase 2 — IMPES upgrade + polish (Day 2, ~6 h)

**2a. IMPES 40×12 simulator (2–3 h)**
- Full 2D two-phase Darcy, Brooks–Corey relperm, gravity on, upwind fractional flow, adaptive CFL
- **dz = 8.3 m — do not refine the vertical grid** (Fix 1)
- **Budget check: 12.2 s/run.** If you're at minutes, your `dz` is too small.

**2b. Regenerate dataset in parallel (~25 min)**
- `multiprocessing.Pool(6)` on the M1; split rows across all three laptops
- 300 runs: 61 min serial → **~23 min** at the measured 2.6× effective speedup
- Retrain — 2.2 s

**2c. Dashboard polish (3 h)**
- SUHS-MRV time series for the operations view
- 2D heatmap from a pre-computed run
- Practice the 3-minute pitch

**End of Day 2:** real Volve-derived parameter ranges, physics simulation, 300-run dataset, trained surrogate, interactive dashboard, health score. Complete prototype.

## Phase 3 — Days 3–5, pick two or three (not all)

**Data**
- [ ] Microbial H₂ loss as a decay term — one line, sounds good
- [ ] **1,000-run sweep: 45 s (VE) / ~80 min (IMPES, 3 laptops).** Not "overnight" — the original plan budgeted a night for this.
- [ ] Add a fault; compute Mohr–Coulomb slip risk from the pressure field as **post-processing**, not a coupled solve

**Models** (best value first)
- [ ] **U-Net**: permeability map + injection rate → leakage heatmap. **2.4 min on MPS.** Most demo-friendly output available.
- [ ] **LSTM**: forecast pressure from Volve history — 1.5 min. Ties back to the real dataset.
- [ ] **PINN** (stretch): only after the U-Net works, and only with the VE equation in the loss
- [ ] **GNN**: skip. High effort, low payoff, data isn't graph-shaped.

**Polish**
- [ ] **Economics module (~90 min) — spec in §Economics below.** Differential ROI only; do not attempt to price the storage project.
- [ ] 3D view in Plotly (extrude the 2D slice — looks 3D, costs nothing)
- [ ] Baseline comparison — **measure it, don't assert it.** Run a pressure-threshold detector over the simulator's own pressure trace, report the day it trips vs the day the surrogate crosses its risk threshold. Both come from the same synthetic run, so the comparison is internally consistent and you can say exactly what it is. *"Pressure-threshold monitoring catches it at day 40; we predict at day 5" was an invented number — do not put it on a slide.*
- [ ] Write the limitations slide honestly (see §Risks)

## Economics — scope, assumptions, and what not to claim

**Supersedes `Document 9.pdf` §4 (Economic & Operational Optimization).** That section lists operational costs, H₂ losses, compressor energy, storage efficiency, ROI, and price-driven scheduling. Built literally, it produces a dollar figure resting on ~20 unstated assumptions, most of which we cannot source in a hackathon. This section narrows it to what we can defend.

### The scope decision: compute the differential, not the project

Do **not** compute "ROI of underground hydrogen storage." Compute **the incremental value of adding HyLeakAI to a site that already exists.**

```
annual_benefit = (avoided_H2_loss + avoided_intervention_cost)
               − (system_cost + false_positive_cost)
```

In a differential, everything common to both arms cancels — and that removes exactly the assumptions we can't defend:

| Cancels (do not model) | Why it would otherwise dominate |
|---|---|
| Cushion gas | Roughly half of gas-in-place, permanently immobilised. Largest capex in porous storage. Identical in both arms. |
| Drilling, completion, surface facilities | Site exists in both arms |
| Compressor capex | Same machine either way |
| Discount rate / WACC / asset life | Not needed for an annual differential — **we deliberately do not compute NPV.** Picking a WACC we can't defend adds a 2–3× error for no gain. |

This also sidesteps the two worst framing errors: it does not require us to claim leakage is the dominant loss (it isn't — see below), and it does not require the operator to own the molecules.

### Assumption register

Every number the module consumes. **Status is the important column.** Nothing marked UNVERIFIED goes on a slide as a point value.

| Quantity | Value / range | Source | Status | ROI sensitivity |
|---|---|---|---|---|
| H₂ price | sweep $1–8/kg | market data — **needs a real citation** | ⚠️ UNVERIFIED | linear |
| Loss fraction | simulator `% H₂ lost` label | our own VE/IMPES run | ❌ **UNCALIBRATED** — no ground truth exists | linear |
| Working gas mass | pore volume × sat, from Volve | our own model | ✅ derived | linear |
| Compressor isentropic efficiency | 0.70–0.85 | textbook range; lower for H₂ reciprocating | ⚠️ needs cite | mild |
| Suction / discharge pressure | from simulator pressure field | our own model | ✅ derived | log — enters as `ln(p₂/p₁)` |
| Electricity price | ENTSO-E / EIA / CAISO | public, free, downloadable | ✅ verifiable | linear on compression term only |
| Intervention (workover) cost | order $10⁵–10⁶ | ⚠️ **needs a real citation** | ⚠️ UNVERIFIED | linear |
| Detection lead-time gain | **measure it** (see Phase 3) | our own simulator + surrogate | ✅ computable | linear |
| False-positive rate | held-out CV on the surrogate | our own model | ✅ **measurable — we already have it** | linear |
| Seasonal price spread | winter − summer | public price data | ✅ verifiable | linear on arbitrage term |

> **The project's own history is the reason for this table.** `Data_sources_research.md` was AI-generated and shipped fabricated datasets and an inverted viscosity/density claim. Do not accept a $/kg or $/workover figure from anyone — including a model — without a source you have opened.

### What we explicitly do NOT claim

State these on the limitations slide rather than waiting to be asked:

1. **Leakage is not the dominant hydrogen loss.** Our own physics section ranks the pathways and puts caprock breakthrough *last*; cushion gas, residual trapping (up to ~41% saturation), dissolution and microbial consumption are all larger. We model the *engineered* leak path (old wells) because it is the actionable one, not the biggest one.
2. **The loss fraction is uncalibrated.** No public H₂ leakage ground truth exists — that absence is the premise of the project. Monetising the label does not add information; it converts an order-of-magnitude uncertainty into a number with a currency symbol. Hence: ranges only.
3. **Storage is usually a service business.** If the operator sells capacity rather than molecules, shrinkage is contractual and the real drivers are permit retention, avoided workover, and insurance. We report avoided-loss value as an *upper bound* on the merchant case.
4. **False positives cost money.** A de-rated injection pressure is lost working-gas revenue. The term is in the formula and it is not zero.
5. **"Traditional monitoring" is not nothing.** Real sites run downhole gauges, DTS/DAS, periodic integrity logging, soil-gas and groundwater sampling. HyLeakAI is a forecasting layer *on top of* that stack, not a replacement for a strawman.

### Compressor energy — the one first-principles number

The only part of Doc 9 §4 that is genuinely computable from scratch, and the one a reservoir engineer on the panel can check in their head. Get it right.

- **Real gas, not ideal.** H₂'s compressibility Z exceeds 1 at reservoir pressure, so ideal-gas underestimates the work. Use enthalpy differences from the **precomputed CoolProp table** (Fix 2) — `w = (h_out − h_in) / η_isentropic` per stage, intercooled back to suction temperature between stages.
- H₂ also has a **negative Joule–Thomson coefficient** above ~193 K: it *warms* on throttling, unlike methane. Worth one sentence in the demo; it surprises people.

**Sanity anchor — compute this by hand before trusting the code.** Ideal isothermal work is `w = (R·T/M)·ln(p₂/p₁)`, and for H₂ at 300 K that constant is **1.237 MJ/kg = 0.344 kWh/kg per natural-log unit**. Pipeline 30 bar → reservoir 200 bar is `ln(6.67) = 1.90`, so ≈ 0.65 kWh/kg ideal, ≈ 0.9 kWh/kg at 75% efficiency. Multi-stage real-gas lands somewhat above that.

> **Tripwire: specific compression work must land in ~0.5–3 kWh/kg**, i.e. under ~10% of H₂'s LHV (33.3 kWh/kg). If you compute 20 kWh/kg you have a unit error or a molar-mass error, not an expensive compressor.

### Scheduling: seasonal spread, not hourly renewable arbitrage

Doc 9 §4 asks for schedules optimised against *renewable availability and market electricity prices* — an hourly / day-ahead problem. **Our simulator runs 3 cycles of 6-month injection / 6-month withdrawal.** You cannot do hourly dispatch optimisation on a 6-month half-cycle model. Pick the one that matches the physics:

- **Do:** seasonal spread arbitrage — inject on summer prices, withdraw on winter prices, net of compression energy at the injection-period electricity price.
- **Don't:** hourly curtailment-chasing. If the pitch needs that story, build it as a clearly-labelled separate toy that is *not* coupled to the simulator, and say so.
- **Label perfect foresight as perfect foresight.** Optimising against known future prices gives an upper bound, not achievable profit. Report it as "perfect-foresight ceiling" or report a naive-forecast run alongside it.
- The genuinely novel coupling, if there's time: constrain the schedule by the surrogate's predicted safe pressure. Economics bounded by the leakage model is the interesting version of this module.

### Tripwires

Same discipline as the compute fixes in Part I — thresholds, not notes.

| Check | Threshold | If it fails |
|---|---|---|
| Loss-fraction plausibility, **before monetising** | assert the label is in a physically plausible band | A site losing 30%/yr is not a business. The label is wrong, not the site. |
| Compression specific work | 0.5–3 kWh/kg, < 10% of LHV | Unit or molar-mass error |
| ROI output format | **range + tornado chart, never a point estimate** | A point ROI invites exactly the question you can't answer |
| False-positive cost term | non-zero | Without it, it isn't an ROI |

### Scale anchor for the pitch

~10,000 t working gas at ~$5/kg ≈ $50M inventory; **1% annual loss ≈ $500k/yr.** Memorise one anchor like this so the magnitude of every number on screen can be checked live. Verify the tonnage against whatever site scale you actually derive from Volve.

### Time budget (~90 min, Person C)

| Task | Time |
|---|---|
| Differential formula + assumption register wired to the labels CSV | 30 min |
| Real-gas compression energy off the CoolProp table | 20 min |
| Seasonal spread arbitrage on downloaded price data | 20 min |
| Tornado / sensitivity chart | 20 min |

Skip NPV, discounting, cushion gas, and hourly dispatch entirely.

## Work split

| Person | Machine | Owns |
|---|---|---|
| A | M1 Air | Simulator (VE → IMPES), physics, parameter ranges |
| B | Windows | Data prep, LHS design, surrogate training, U-Net |
| C | Windows | Streamlit dashboard, plots, economics, pitch |

All three run slices of the LHS sweep in Phase 2b — that's the only step where the extra hardware matters.

## Revised time budget vs the original plan

| Stage | Original | Assessed |
|---|---|---|
| Setup + disk | 30 min | 45 min |
| Simulator | 4 h | 2–3 h (VE) + 2–3 h (IMPES upgrade) |
| 300-run dataset | ~1 h | **13 s (VE)** / **23 min (IMPES, 6 workers)** |
| Train GBM | 2 h | 2.2 s compute, ~1 h human |
| Dashboard | 4 h | 4 h (unchanged — UI time is human time) |
| 1,000 runs | overnight | **45 s / 80 min** |
| U-Net | ~10 min | **2.4 min on MPS** |

**Compute is no longer the constraint anywhere in this plan.** The budget is dominated by writing and debugging the simulator, and by dashboard UI work. Direct remaining planning effort there.

---

## Risks & honest caveats

| Risk | Mitigation |
|---|---|
| Simulator not working by Day 1 afternoon | VE-first ordering exists precisely for this; single-phase + buoyancy rule is the floor |
| Silent 100× slowdown from CoolProp in loop | Assert per-run wall time in the sweep script; fail loudly above threshold |
| torch/sklearn segfault mid-demo | Import order fixed in every file, including Streamlit |
| M1 stalls during judging | Free 15–20 GB; pre-compute everything; **never run a simulation live** |
| Coarse `dz` questioned by judges | Own it — say vertical resolution was traded for 300 scenarios, and show the CFL arithmetic |
| **"Where did your $/kg come from?"** | Assumption register (§Economics) with sources and status; sweep the price, never quote one |
| **"Isn't leakage the smallest loss term?"** — it is | Answer it first, unprompted. We model the *actionable* loss path, not the biggest one. Differential ROI doesn't require it to be the biggest. |
| **Economics inherits the unvalidated loss label** | Plausibility tripwire before monetising; report ranges + tornado, never a point ROI |

**Caveats on the numbers in Part I:**

- Runtimes come from a solver written for benchmarking. It reproduces the *cost structure* faithfully — that is what was being measured — but its **physical outputs are not validated**. Its peak-pressure label came out at ~10⁶ bar, i.e. the pressure anchoring is wrong. **Treat the timings as sound and the labels as unverified.** Whoever writes the real simulator should not copy it.
- The CFL analysis assumes explicit saturation. A **fully implicit** solver removes the limit: measured at 4 Newton iterations × 219 steps (dt = 5 d), that's **20 s/run at 40×25** and 75 s at 60×80 — which would let you keep a fine grid. But a robust two-phase Newton solver is not a two-day task. Correct post-hackathon path, alongside **OPM Flow** (free, reads ECLIPSE decks, supports H₂ storage natively).
- Free-tier cloud specs change. The "skip Colab/Kaggle" conclusion rests on the simulation being CPU-sequential, not on exact vCPU counts.

## Demo notes

- **Pre-compute everything.** Load from CSV during judging. Never simulate live.
- **Say "physics-based synthetic training data,"** then explain that no public H₂ leakage dataset exists — that's *why* you generated it. This is the technical contribution.
- **Cut features, not the pipeline.** End-to-end beats a great simulator with no UI.
- **Close everything else.** 8 GB fills fast.
