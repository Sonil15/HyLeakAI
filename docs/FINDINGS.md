# Findings

A running record of what we measured, including the things that did not work.
Anything reported from this project should be consistent with this file.

Source: Mao, S., Carbonero, A., & Mehana, M. (2025). *Deep learning for
subsurface flow: A comparative study of U-Net, Fourier neural operators, and
transformers in underground hydrogen storage.* JGR: Machine Learning and
Computation, 2, e2024JH000401. Dataset: Zenodo record 14029514 (CC-BY-4.0/MIT).

---

## 1. The dataset has three channels, not two

**Status: undocumented upstream. Confirmed by direct inspection.**

Both the Zenodo description and the `ml4uhs-dataset` README state that each
`"<sim>-<t>"` value is a 2-tuple `(pressure, h2_saturation)`. It is a 3-tuple.

We characterised the third channel across timesteps and simulations:

| Timestep | corr(aux, pressure) | corr(aux, saturation) | aux / (P − P_init) |
|---|---|---|---|
| 1  | −0.9978 | −0.7022 | −1.177e-4 |
| 3  | −0.9990 | −0.7198 | −1.164e-4 |
| 6  | −0.9938 | +0.8411 | −1.160e-4 |
| 30 | −0.9930 | +0.9252 | −1.181e-4 |

It is essentially a linear function of pressure with a constant coefficient of
−1.17e-4 per bar, i.e. **1.17e-9 /Pa — a compressibility**, the right order for
brine plus pore compressibility. Roughly 10% of its variance is not explained by
pressure and tracks the H2 plume. Its sign flips between injection and
withdrawal stages.

We cannot name it definitively and do not guess. It is preserved in
`states.npy` channel 2 as `aux_undocumented` and is **not used as a model
target** — the paper predicts pressure and saturation, and being ~99% collinear
with pressure it carries almost no independent information.

## 2. T1 (lateral containment loss) is DROPPED

**Status: measured across all 1,000 simulations. Negative result.**

T1 was the only leakage signal genuinely present in the data: the paper states
the simulations have "no-flow boundaries at the top and bottom, and outflow
boundaries on the sides", so H2 reaching the lateral boundary really does leave
the domain. The plan made this a go/no-go checkpoint precisely because it might
not occur.

It does not occur.

| Quantity | Value |
|---|---|
| Simulations reaching the boundary | **0 / 1000** |
| Highest boundary saturation anywhere | 0.00390 |
| Threshold for mobile H2 | 0.05 |
| Largest equivalent plume radius | ~1,454 m |
| Domain half-width | 3,840 m |
| Fraction of the way to the boundary | **37.9%** |

The plume peaks at 6.06 km² after ten years and stays well inside the domain.
Peak boundary saturation is 13× below the threshold, so this is not a marginal
call that a different threshold would rescue.

**Consequence:** T1 is dropped. We did not lower the threshold until it produced
labels. The project rests on T3, with T2 as a continuous feature.

## 3. T2 (caprock breach) is usable only as a continuous margin

**Status: measured. The binary label is not defensible.**

Peak pressure across the full dataset is **293.8 bar**. The binary "caprock
exceeded" label depends entirely on an assumed fracture gradient, which is not
in the paper or the dataset:

| Fracture gradient | P_frac (at ~1,878 m) | Peak margin | Binary label |
|---|---|---|---|
| 0.15 bar/m | 281.7 bar | 1.097 | some exceedances |
| **0.17 bar/m** (our default) | 319.3 bar | 0.759 | **identically zero** |
| 0.20 bar/m | 375.6 bar | 0.519 | identically zero |

Flipping one assumed constant flips the label from "never happens" to "sometimes
happens". A binary caprock-breach label is therefore an artifact of our own
assumption, not a finding, and we do not report one.

The **continuous** margin `(P_max − P_init)/(P_frac − P_init)` is monotone in
pressure regardless of the gradient, so it is retained as a model feature.

## 4. Validations that passed

**Well location.** The paper says only "a central well". Located empirically:
pressure maximum during injection and minimum during withdrawal both land on
cell (63, 63), 0.71 cells from the grid centre. `config.WELL_BLOCK` is correct,
so the distance-to-well channel is properly anchored — which matters, because
the paper attributes 24 percentage points of pressure accuracy to that channel.

**Cyclic indexing.** On injection steps, well pressure exceeds **100.0%** of the
field; on withdrawal steps, **0.0%**. This reproduces the paper's section 5.8
description exactly and confirms `config.cycle_index()` is aligned with the
simulations.

**Architecture.** Our U-Net matches the paper's Table 1 weight counts:

| Model | Embedding | Ours | Paper |
|---|---|---|---|
| Small | 32 | 7.76M | 7.7M |
| Medium | 64 | 31.04M | 31M |
| Large | 128 | 124.12M | 124M |

This confirms the paper's architecture is milesial/Pytorch-UNet at depth 4 with
transposed-convolution upsampling and a configurable base embedding.

**Download integrity.** MD5 `6bc841f02ad3f40c9a8ef8ad187edf43`, matching the
Zenodo record exactly.

## 5. Storage precision

`states.npy` is float16. Worst-case round-trip error, verified against the LMDB:

| Field | Max error | float16 limit at that magnitude |
|---|---|---|
| Pressure | 3.12e-2 bar | 4.69e-2 |
| Saturation | 2.44e-4 | 7.32e-4 |
| Aux | 3.82e-6 | 5.72e-6 |
| Porosity, permeability | 0 (float32) | — |

Pressure error is 0.027% of the peak excursion — about 300× smaller than the
surrogate's own ~8.6% relative error, so it cannot affect any downstream result.
Storing pressure as float32 would double the file for no usable gain.

Permeability is in **millidarcy** (1.03–738.8 mD), not m². It spans 716×, so the
normaliser takes log10 before standardising.

## 6. Compute reality

No local CUDA device (Intel Iris Xe, `torch 2.9.0+cpu`). U-Net training on CPU
is impractical at full scale — the training split alone is 42,000 samples per
epoch. Training runs on Colab (T4); everything else runs locally.

The paper supplies the escape route: **U-Net-Small with cyclic and distance
channels reaches 8.6% pressure error, level with U-Net-Large's 8.61%** at 124M
parameters and 35 GB. Without those channels Small degrades to 32.7%. The input
representation, not the parameter count, carries the accuracy — so a 7.7M model
on a free T4 is a legitimate reproduction rather than a compromise.

## 7. The forecast horizon was wrong, and fixing it inverted the result

**Status: measured across all 1,000 simulations. A correction to an earlier
conclusion.**

### What XGBoost is actually trained on

This needs stating plainly because "synthetic" is ambiguous:

- **Features are real.** Porosity, permeability, pressure and saturation all
  come from Mao et al.'s tNavigator physics simulations.
- **Labels are ours.** The dataset contains no leakage. T3 is a semi-analytical
  Darcy flux through a *hypothetical* fault whose location, permeability, length
  and width we sample.

The consequence is severe: the label

    Q = k_f · k_rg(S_fault) · A_f / mu · max(P_fault - P_init, 0) / L_caprock

is a **closed-form function of quantities that appear in the feature vector**
(`fault_log10_perm_m2`, `fault_area_m2`, `fault_s`, `fault_p_bar`). At the same
timestep it is pure algebra. The only genuine learning content is how the fields
evolve over the forecast horizon.

### The horizon sweep

The original run used horizon 6 = one full storage cycle, so the observed and
labelled timesteps sat at the **same phase** of consecutive annual cycles. Test
set, 1,000 simulations:

| Horizon | Months | Phase | Model PR-AUC | Persistence PR-AUC | Gain | Model R² | Persistence R² |
|---|---|---|---|---|---|---|---|
| 1 | 2 | different | 0.9949 | 0.4224 | +0.5725 | 0.9669 | +0.3269 |
| **3** | **6** | **different** | **0.9931** | **0.0218** | **+0.9714** | **0.9711** | **−0.7642** |
| 6 | 12 | SAME | 0.9975 | 0.9918 | +0.0057 | 0.9850 | +0.9198 |
| 12 | 24 | SAME | 0.9960 | 0.9758 | +0.0202 | 0.9757 | +0.8405 |
| 30 | 60 | SAME | 0.9918 | 0.9125 | +0.0792 | 0.9556 | +0.6101 |

Every horizon that is a multiple of 6 lands at the same cycle phase, and
**persistence alone scores 0.91–0.99**. Horizon length does not fix this —
even at five years persistence reaches 0.9125. Phase does.

At horizon 3, persistence collapses to **0.0218 PR-AUC, below the 2.3% base
rate** — it is actively anti-correlated, because half a cycle later injection
has become withdrawal and high flux has become zero. Its log-flux R² is
**negative** (−0.7642): worse than predicting the mean.

### Consequences

- **Horizon 3 (six months, half a storage cycle) is the reported task.** It is
  also the operationally meaningful one: "will risk be elevated at the next
  stage change?"
- The earlier headline (AUC 0.9999 at horizon 6) was **mostly the system's
  annual periodicity**, not forecasting skill. It is withdrawn.
- `train_xgb.py` now selects the shipped model by largest gain over persistence,
  not by longest horizon, and flags any horizon where persistence exceeds
  0.9 PR-AUC as "not a forecasting task".

### Remaining caveat, not resolved

Even at horizon 3, the model is given the fault's permeability and area
*exactly*, and those are multiplicative constants in the label. Real fault
properties are uncertain by orders of magnitude. The honest framing is that
this answers **"given this fault hypothesis, how does risk evolve?"** — useful
for Monte-Carlo screening over unknown faults, which is what the dashboard does
— and not "how much hydrogen will leak".

## 8. U-Net surrogate: trained, and ~1.9x short of the paper

**Status: trained on Kaggle (T4), 120 epochs, 4.23 h, 127 s/epoch, batch 48.**

Held-out test error (150 simulations never seen in training):

| | Ours | Paper U-Net-**Small** | Paper U-Net-Large |
|---|---|---|---|
| Pressure | **0.1640** | **0.086** | 0.0861 |
| Saturation | **0.1101** | ~0.06–0.07 | 0.0577 |

The right comparison is the paper's **Small** model, since that is what we
trained. We are roughly **1.9x its error**. This is a working surrogate and a
faithful implementation — the parameter counts match Table 1 exactly — but it is
not a reproduction of the paper's accuracy, and should not be described as one.

### The training curve says "noisy floor", not "converged"

| Epoch | val pressure | val saturation | lr |
|---|---|---|---|
| 0 | 0.5099 | 0.2665 | 1.0e-4 |
| 50 | 0.3035 | 0.1344 | 5.0e-5 |
| 70 | 0.2427 | 0.1300 | 5.0e-5 |
| **76** | **0.1863** | **0.1217** | 5.0e-5 |
| 90 | 0.2075 | 0.1281 | 5.0e-5 |
| 110 | 0.1878 | 0.1301 | 2.5e-5 |
| 119 | 0.1927 | 0.1328 | 2.5e-5 |

Pressure fell steeply to 0.186 by epoch 76, then oscillated between 0.19 and
0.22 for the remaining 44 epochs. Neither learning-rate halving (epochs 50 and
100) broke through. So a longer run will not help; the limiter is elsewhere.

### Ranked suspects

1. **The shared two-head trunk — our own deviation.** The paper trains a
   *separate* model per state variable. We emit both from one two-channel head
   to halve training cost. The targets conflict: pressure is smooth, global and
   sign-flipping between stages; saturation is local with a sharp front. A
   shared trunk must compromise. Untested; this is the experiment to run.
2. **Batch 48 vs the paper's 128.** Noisier gradients, and the "halve every 50
   epochs" schedule was tuned at 128.
3. **Mixed precision.** The paper reports consistent precision throughout.

## 9. Surrogate error barely affects risk *screening*, but does degrade *magnitude*

**Status: measured on 150 held-out simulations, 16,880 aligned rows.**

The question the whole surrogate argument depends on: the U-Net has ~16%
relative error on pressure and ~11% on saturation. Does that wreck the leakage
risk estimate?

Setup, chosen so that only surrogate error can explain the difference:

- The risk model is trained **once, on simulator features, and never retrained**
  — the actual deployment situation.
- Both tables take **labels from the simulator**, so the target is identical
  (asserted at runtime).
- Both use the **same leak thresholds**, so class balance is identical.
- Rows aligned on `(sim_id, fault_id, timestep_observed)`.

| Field source | PR-AUC | AUC | log-flux R² | RMSE |
|---|---|---|---|---|
| Simulator | 0.9941 | 0.9999 | +0.9714 | 0.739 |
| **U-Net** | **0.9842** | 0.9996 | **+0.9200** | **1.236** |
| Cost | **−0.0099** | −0.0003 | **−0.0514** | +0.497 |

**The surrogate retains 99.0% of the simulator's PR-AUC.** For screening and
ranking — "which fault hypotheses are dangerous, and when" — surrogate fields
are nearly as good as running the simulation.

**But magnitude estimation degrades materially.** Log-flux RMSE rises from 0.739
to 1.236, i.e. from predicting flux within ~5.5x to within ~17x. So the
defensible claim is *risk screening*, not *quantitative leak-rate prediction* —
which is the framing this project already committed to, now with evidence.

### Which features absorb the error

15 of 41 features are **bit-identical**: geology and fault properties never pass
through the surrogate. The distortion concentrates in **time-derivative**
features, as differencing amplifies field noise:

| Feature | mean abs error / scale |
|---|---|
| `plume_front_speed_m_per_year` | 0.493 |
| `dp_dt_bar_per_year` | 0.186 |
| `hpv_rate_m3_per_year` | 0.178 |
| `plume_centroid_offset_m` | 0.122 |
| `fault_delta_p_bar` | 0.121 |
| `fault_krg` | 0.107 |
| `fault_overpressure_bar` | 0.097 |

That the top SHAP features (`fault_log10_perm_m2`, `fault_area_m2`) are among
the identical ones is why PR-AUC barely moves: the model leans hardest on inputs
the surrogate cannot corrupt.

### Two features are vestigial and should be removed

`boundary_hpv_fraction` and `boundary_saturation_max` report enormous *relative*
distortion (763443x and 9588x) but negligible *absolute* error (0.0016, 0.003).
Both are near-zero everywhere — they are leftovers from the dropped T1 target
(§2), since the plume never reaches the boundary. The ratios are an artefact of
dividing by ~0. They contribute nothing and should be dropped from the feature
set.

## 10. Claims this project will not make

- Not "we predict 3D reservoir maps" — the grid is 128×128×**1**.
- Not "trained on simulated leakage ground truth" — there is none; T3 is a
  derived semi-analytical label.
- Not "real-time sensor fusion" — there is no sensor data.
- Not a binary caprock-breach rate (see §3).
- Not a lateral containment-loss result (see §2).
- Not a leakage score quoted at a horizon that is a whole number of storage
  cycles, where a trivial persistence baseline already scores ~0.99 (see §7).
- Not "predicts hydrogen leakage" without stating that the leakage label is
  ours, computed from a hypothetical fault, on real simulated flow fields.
