# HyLeakAI — Compute Feasibility Assessment

> **Superseded.** This benchmarks the custom Volve-based IMPES/VE simulator
> from `Data_sources_research.md`. That simulator was never built — the
> project pivoted to Mao et al.'s published UHS dataset (Zenodo 14029514)
> with a U-Net surrogate + XGBoost risk model instead. See
> [`README.md`](README.md) and [`docs/FINDINGS.md`](docs/FINDINGS.md) for
> what actually shipped. Kept as historical record of the M1 hardware
> benchmarks (import-order segfault, thermal throttling, parallel scaling),
> which are still accurate for this machine.

**Assessed:** 2026-08-09 · **Against:** `Data_sources_research.md` §4–§6
**Method:** benchmarked on the actual target machine (M1 Air, 8 GB, 8 cores, fanless), not estimated.

---

## Verdict

The plan is **feasible, but §4 and §5 contain one arithmetic error that would have cost you the hackathon.**

The stated simulator config — 60×80 cells, "2–10 s per run" — actually takes **~54 minutes per run**, measured. That is a **300–500× underestimate**. At that rate the 300-run dataset in Day 1 afternoon takes **11 days**, not 1 hour.

The fix is cheap and the rest of the plan survives intact. Three changes below.

Second finding: **the free cloud GPUs are irrelevant to this project.** Your bottleneck is CPU sparse linear algebra, which GPUs don't accelerate, and the only GPU-shaped work (the U-Net) runs in **2.4 minutes on your own M1 GPU**. Don't spend time setting up Colab/Kaggle.

---

## 1. Why the simulator estimate was wrong

§3 of the roadmap gets the physics right: hydrogen moves by **buoyancy**, not viscous flow. §4 then costs the simulator as if that didn't matter. It does — buoyancy is exactly what makes explicit timestepping expensive.

The Darcy velocity from buoyancy alone:

```
v = k·Δρ·g / μ_H2  =  (200 mD)(980 kg/m³)(9.81) / 1.05e-5 Pa·s  =  16.6 m/day
```

With 1.25 m tall cells (100 m ÷ 80), the explicit CFL limit is `dt ≤ φ·dz/(v·df/dS)` ≈ **0.1 hours**. Three years of cycling therefore needs **~265,000 timesteps**, each requiring a sparse pressure solve.

Measured cost of one timestep (assemble + solve + transport):

| Grid | Cells | spsolve | splu | CG |
|---|---:|---:|---:|---:|
| 30×40 | 1,200 | 3.4 ms | 2.9 ms | 23.6 ms |
| **60×80** | **4,800** | **12.5 ms** | **12.3 ms** | 49.4 ms |
| 100×120 | 12,000 | 38.7 ms | 38.7 ms | 182.0 ms |
| 150×200 | 30,000 | 144.2 ms | 135.0 ms | 825.3 ms |

`265,000 steps × 12.3 ms` = **54 minutes per run**. In high-perm rock (1 D) it's **4.5 hours**.

I confirmed this by building a complete IMPES solver (gravity on, adaptive CFL, upwind fractional flow) and running it end to end:

| Grid | Cells | Steps (3 yr) | **Measured runtime** |
|---|---:|---:|---:|
| 40×12 | 480 | 11,518 | **12.2 s** ✅ |
| 60×20 | 1,200 | 24,799 | **68.8 s** ⚠️ |
| 60×80 | 4,800 | — | **did not finish in 20 min** ❌ |

Note the scaling is worse than linear in cell count: halving `dz` both doubles the step count *and* raises per-step cost.

---

## 2. The three changes

### Change 1 — grid: 60×80 → **40×12** (dz = 8.3 m, not 1.25 m)

This is the whole fix. Vertical cell size drives the CFL limit linearly, so coarsening `dz` by 6.7× buys back 6.7× in step count *and* 4× in per-step cost.

- **Measured: 12.2 s per 3-year run**, holds up to 1 D permeability (26.6 s worst case).
- 300 runs = **61 min serial**, **~23 min** using all 8 cores.
- You lose vertical resolution of the plume. For four scalar labels (% lost, breakthrough day, extent, peak pressure) that is an acceptable trade. Say so in your limitations slide.

### Change 2 — tabulate CoolProp; never call it in the loop

Measured `PropsSI` scalar call: **280–300 µs**. That is 25,000× slower than a NumPy array op.

| Usage | Cost |
|---|---|
| Per cell, per timestep | **99 CPU-hours per run** ☠️ |
| Once per timestep | 74 s per run — still 6× your entire budget |
| **Precomputed 40×40 (T,p) table + interpolation** | **0.45 s once, ~1 µs per lookup** ✅ |

Build the table at startup, use `np.interp` / `RegularGridInterpolator` thereafter. This is a one-line-of-thought change that is otherwise a silent project-killer.

### Change 3 — keep the fallback, and start with it

§5's fallback ("single-phase + buoyancy rule") is currently framed as the panic option. **Consider making it the primary.** A vertical-equilibrium / sharp-interface model — the standard reduced-order approach for buoyancy-dominated CO₂ and H₂ storage — integrates vertically and solves for plume thickness `h(x,t)`:

| Model | Per run | 300 runs |
|---|---:|---:|
| VE / sharp-interface, nx=200, dt=1 d | **0.043 s** | **13 s** |
| VE, nx=400, dt=0.25 d | 0.153 s | 46 s |
| Full IMPES 40×12 | 12.2 s | 61 min |

That is **280× faster**, which converts your dataset budget from "an hour, if nothing breaks" into "rerun the whole design whenever you want." It also unlocks the Day-3 goal of 1,000+ scenarios trivially.

**Suggested sequencing:** build VE first (it is genuinely ~100 lines and hard to get catastrophically wrong), lock the full pipeline end-to-end, then upgrade to IMPES 40×12 with time left over. That inverts the current risk profile — right now, everything downstream is blocked behind the hardest component.

---

## 3. Team compute — what actually helps

### Parallel scaling on the M1 (measured, realistic multi-second jobs)

| Workers | Speedup | Efficiency |
|---:|---:|---:|
| 1 | 0.99× | 99% |
| 2 | 1.75× | 88% |
| 4 | 2.33× | 58% |
| 8 | **3.13×** | 39% |

**Plan for ~3×, not 8×.** The M1 has 4 performance + 4 efficiency cores; the E-cores contribute little. Use `multiprocessing.Pool(6)` — past 6 you're paying scheduling cost for marginal gain.

### Thermal throttling (measured, 6 min sustained on 8 workers)

Settles at **80–90% of cold-start throughput**, with occasional dips to ~68%. This is **milder than the 30–40% previously assumed** — a ~15% haircut. Combined planning factor: **~2.6× effective speedup**.

### Teammates' Windows laptops — yes, and this is your best lever

The LHS sweep is embarrassingly parallel with zero communication. Split the design matrix into disjoint row ranges, everyone runs the same script, concatenate CSVs.

- Pure NumPy/SciPy — no GPU, no CUDA, no install friction beyond `pip install numpy scipy`.
- A 4-core Windows laptop contributes roughly what your M1 does. Three machines ≈ **3× throughput**.
- **Watch out:** results must be reproducible per-row. Seed the RNG from the *row index*, not from time or worker ID, or you can't reconcile or re-run a slice.

### Google Colab / Kaggle — skip them

This is the counterintuitive part, so here is the reasoning explicitly:

| Resource | What it offers | Use for HyLeakAI |
|---|---|---|
| Colab free | ~2 vCPU, T4 GPU when available, idle timeout | **Worse than a laptop** for the sim (2 vCPU < your 8) |
| Kaggle free | ~4 vCPU, ~30 GB RAM, ~30 GPU-h/week, 12 h sessions | 4 vCPU ≈ half your M1; GPU unused |

- **The simulation cannot use a GPU.** It is sequential sparse LU factorization with a data dependency between timesteps. There is no GPU port of this that you can write in two days.
- **The ML doesn't need a GPU** (next section).
- Colab's 2 vCPU makes it a *downgrade* from every machine you already have.

The one legitimate use: Kaggle's 12-hour sessions as **free extra CPU workers** for an overnight 1,000-run sweep — 2–3 notebooks each running a slice. Even that is optional, since 1,000 runs at 12.2 s across three laptops is ~1.2 hours.

---

## 4. ML stage — comfortably feasible, all local

All measured on this M1:

| Model | Cost | Verdict |
|---|---|---|
| HistGradientBoosting, 4 targets, 300×8 | **2.2 s total** | Trivial. §5 is right to prefer this over deep learning. |
| U-Net (117k params), 300 samples, 200 epochs | **13.3 min CPU / 2.4 min on MPS** | Use `device="mps"` — 5.5× free speedup |
| LSTM (2×64) on Volve history, 100 epochs | **1.5 min** | Trivial |
| PINN (6×64, 4096 collocation pts, 2nd-order autograd) | 29 ms/iter → **9.6 min** for 20k iters | Cheap to *run*; expensive to get *right* |

Two notes:

- **Use MPS for the U-Net.** `torch.backends.mps.is_available()` returned `True`. This is your GPU, and it beats waiting on a Colab queue.
- **The PINN's cost is not compute.** 9.6 minutes of training is nothing; the risk is §6's own warning — the PDE in the loss must match the simulator's, or it fails silently. With a VE simulator the governing equation is much simpler, which makes the PINN *more* tractable, not less. Still: last priority.

---

## 5. Environment blockers found

### ⚠️ `import torch` before `sklearn` segfaults this machine

Reproduced deterministically — exit code 139:

```python
import torch
from sklearn.ensemble import HistGradientBoostingRegressor
HistGradientBoostingRegressor().fit(X, y)   # SIGSEGV
```

Duplicate OpenMP runtime between Anaconda's `libomp` and PyTorch's. `KMP_DUPLICATE_LIB_OK=TRUE` **does not fix it**. What works:

```python
from sklearn.ensemble import HistGradientBoostingRegressor   # sklearn FIRST
import torch                                                  # torch second
```

Put sklearn imports above torch imports in every file, including the Streamlit app. This will otherwise hit you at the worst possible moment.

### Disk: 3.7 GB free (99% full) — still the top infrastructure risk

Less blocking than feared for *packages* — numpy, scipy, sklearn, pandas, matplotlib, streamlit, plotly, CoolProp and torch 2.11 are **all already installed**. Only `xgboost` is missing, and `HistGradientBoostingRegressor` is a fine substitute; don't spend disk on it.

The risk is macOS itself: under 4 GB free with 8 GB RAM, swap has nowhere to go and the machine will stall mid-demo. **Free 15–20 GB before Day 1.** Note the data footprint is genuinely small — the CSV is ~50 KB, and 300 saturation maps at 64×64 float32 are only ~4.9 MB.

---

## 6. Revised time budget

Assuming VE-first, 40×12 IMPES upgrade, 6 workers, 0.85 thermal factor:

| Stage | Roadmap says | Assessed |
|---|---|---|
| Setup + disk cleanup | 30 min | 45 min (disk cleanup is real work) |
| Simulator (VE first) | 4 h | 2–3 h for VE; +2–3 h for IMPES upgrade |
| 300-run dataset | ~1 h | **13 s (VE)** / **23 min (IMPES, 6 workers)** |
| Train GBM | 2 h | 5 min compute, ~1 h of your time |
| Streamlit dashboard | 4 h | 4 h (unchanged — UI time is human time) |
| **Day 3: 1,000 runs "overnight"** | overnight | **45 s (VE) / ~80 min (IMPES)** — not overnight |
| Day 4: U-Net | ~10 min | **2.4 min on MPS** |

**The compute is no longer the constraint anywhere in this plan.** Your budget is dominated by writing and debugging the simulator, and by dashboard UI work. Spend your remaining planning effort there.

---

## 7. Caveats on this assessment

- Runtimes come from a solver I wrote today for benchmarking. It reproduces the cost structure faithfully (that's what was being measured), but its **physical outputs are not validated** — its peak-pressure label came out at ~10⁶ bar, i.e. the pressure anchoring is wrong. Treat the timings as sound and the labels as unverified.
- The CFL analysis assumes explicit saturation. A **fully implicit** solver removes the limit entirely: measured at 4 Newton iterations × 219 steps (dt = 5 d), that's **20 s per run at 40×25** and 75 s at 60×80. Legitimate, and it would let you keep the fine grid — but writing a robust two-phase Newton solver is not a two-day task. Noted as the correct post-hackathon path, alongside OPM Flow.
- Free-tier Colab/Kaggle specs change; treat those rows as approximate. The conclusion doesn't depend on the exact numbers — it depends on the sim being CPU-sequential, which is structural.

---

## Benchmark scripts

`bench2.py` (per-step cost, CFL counts) · `bench3.py` (fixes, CoolProp) · `bench_par2.py` (parallel scaling) · `real_sim.py` (end-to-end IMPES) — in the session scratchpad:
`/private/tmp/claude-501/-Users-sonil-Desktop-HyLeakAI/cec8609d-1959-473b-aefd-45904c323cab/`
