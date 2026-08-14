# Economics and Impact — the whole thing, explained

This is the plain-language version of Module 4. It explains what we built, why we
built it that way, what it says, and where it breaks. If you only read one file
about the business case, read this one.

- The terse, slide-ready version is `docs/COMMERCIAL.md`.
- The code is `src/economics/`.
- The original spec this supersedes is `Build_Plan.md` §Economics.

---

## 1. Why this exists

In the online round we said nothing about business. A judge asked:

> "How will you make a business out of this?"

We had no answer, and the reason was structural: our own `README.md` status table
marked **Module 4 (Economic & Operational Optimisation) as ❌ Not Started**, and
`docs/PRESENTATION_CONTEXT.md` listed *"any ROI, $/kg, or avoided-cost number"* as
a **forbidden claim** — precisely because the module did not exist.

So one missing module was costing us on two of the five judging criteria at once:
**Industrial / Commercial Impact** and **Feasibility & Prototype Maturity**.

Module 4 is now built. It deliberately does **not** produce an ROI, and §3
explains why that is the stronger result rather than a dodge.

---

## 2. What we built

Four modules, in descending order of how defensible their outputs are.

| Module | What it does | Output |
|---|---|---|
| `src/economics/fluids.py` | CoolProp fluid properties behind the "CH₄ next, not CO₂" claim | `outputs/fluid_properties.json` |
| `src/economics/assumptions.py` | The assumption register — decides which numbers may appear on a slide | `outputs/assumption_register.json` |
| `src/economics/voi.py` | Value of Information — the headline result | `outputs/voi_results.json` |
| `src/economics/unit_cost.py` | What a screening pass costs us to run | `outputs/unit_cost.json` |

Run them all — no dataset needed, they work on a laptop from a fresh clone:

```bash
python -m src.economics.fluids
python -m src.economics.assumptions
python -m src.economics.voi
python -m src.economics.unit_cost
```

`voi.py` runs its own self-test first, every time, and refuses to report if the
mathematical identities fail.

---

## 3. The core decision: Value of Information, not ROI

### Why an ROI would have been dishonest

An ROI needs a **leak rate**. And the founding fact of this entire project is
that no public dataset anywhere in the world contains hydrogen leakage
measurements (`Data_sources_research.md` §1). Our leakage label is our own
semi-analytical physics, uncalibrated against any real measurement, because there
is nothing to calibrate against.

Multiplying that label by a hydrogen price would not create knowledge. It would
put a currency symbol on an order-of-magnitude uncertainty — and it would take
the one asset we actually have, the honesty discipline, and destroy it four
minutes into a five-minute pitch.

### What Value of Information is

VOI is the framework petroleum decision analysis already uses for exactly this
question. Instead of asking *"how much money does this save?"* it asks:

> **What is knowing this worth, measured in decisions changed?**

That needs three things: the structure of the decision, a prior, and the
reliability of the information source. It does **not** need the true leak rate.
That is why it works here when ROI does not.

The decision we model is the real one an operator faces:

- A site may harbour a fault conductive enough to matter. Call that probability θ.
- They can **proceed** with injection as planned, or **mitigate** — extra
  appraisal, de-rated injection pressure, a relocated well — at a certain cost.
- Proceeding when the site is genuinely dangerous costs a containment failure.

Everything is expressed **relative to the containment-failure loss**, so the two
costs we cannot source collapse into one ratio, which we then sweep over three
decades rather than pick.

---

## 4. The key insight: we sell coverage, not accuracy

This is the part worth understanding properly, because our first attempt got it
wrong and the wrong version was flattering.

### The wrong framing

The obvious move is "our classifier versus a perfect classifier." Run that and
you get **efficiency ≈ 1.0** — "we capture 100% of the value of perfect
information."

That number is garbage, for a reason our own code admits. `train_xgb.py` says
plainly that the T3 label is a closed-form function of quantities already in the
feature vector — at a fixed timestep it is **algebra**. Our classifier scores AUC
0.9996 against it. So "we capture 100% of perfect information" is not a result;
it is a restatement of the label. Any sharp judge takes it apart in one question.

### The right framing

Your own pitch already contains it: *"twenty thousand **guesses about one
crack**."*

A site has **one** unknown fault. **Nobody ever observes it** — not the
simulator, not us. Both parties are estimating the same quantity θ. They differ
only in how well:

|  | Coverage | Nature of the error |
|---|---|---|
| **Unaided operator** | k ≈ 2 hypotheses, simulated **exactly** | Unbiased, but hopeless variance — at k = 2 the only estimates available are 0, ½, 1 |
| **HyLeakAI** | 20,000 hypotheses at measured skill | Sampling noise negligible; the error is the **bias from our own calibration** |

That is a **bias–variance trade**, and it is the honest form of the comparison.
The unaided operator is not modelled as ignorant or as using a worse tool. They
are modelled as using a **better** tool on a sample far too small to cover the
uncertainty.

### Why our advantage has a hard ceiling

Because sampling noise vanishes at N = 20,000, our error is entirely the gap
between the true sensitivity/specificity and our *estimates* of them — and those
were measured on finite held-out data, with only **~308 positive rows** behind
the sensitivity.

**So more fault hypotheses cannot make us better.** Only a better-characterised
classifier can. That ceiling is real, it is in the output, and we state it before
anyone asks.

---

## 5. The results

Base case: prior site risk 10%, mitigation/loss ratio at the geometric middle of
the swept range.

| Arm | Hypotheses | VOI / VOPI |
|---|---|---|
| Unaided (exact simulator) | 2 | **0.00** |
| **HyLeakAI screen** | **20,000** | **0.9974** |
| Perfect information | — | 1.00 |

**Efficiency is dimensionless** — it is a share of the available decision value,
bounded at 1 by construction. There is no currency in it, because there is
nothing honest to put there yet.

**Raising the simulator budget does not help.** At 1, 2, 3, 5, 10 and 20 exact
runs the unaided efficiency stays at **0.00** — at this cost ratio, a handful of
samples never moves the decision across the threshold. Coverage is what is
scarce, not accuracy. That single row is the clearest statement of what the
product is for.

**The speedup is nearly free in decision terms.** Swapping the simulator's fields
for the U-Net's costs **0.000178** of efficiency — AUC 0.99987 → 0.99963,
PR-AUC 0.9941 → 0.9842, measured on 150 held-out simulations. That is the number
an operator actually wants when they ask whether the AI is good enough to decide
on.

### Where we are worth less than nothing

Below a mitigation-to-loss ratio of **6.2e-5**, VOI turns **negative**.

The mechanism is worth understanding: when mitigation is that cheap, the correct
move is to mitigate almost regardless. A screen can then only *talk you out of
it* — and since our estimate is bias-corrected using imperfectly known error
rates, sometimes it wrongly does.

**That boundary sits below the plausible range** of the cost ratio (1e-4 to
1e-1), so across every ratio we consider credible the screen never destroys
value. We report the boundary anyway: knowing where a tool fails is worth more
than claiming it does not.

> **Report the sign, not the ratio, in this corner.** Where VOI goes negative,
> VOPI is also collapsing towards zero, so the *ratio* VOI/VOPI becomes wild —
> a loss of 2e-10 against a VOPI of 3e-12 prints as "−80×", which wildly
> overstates a rounding-scale effect. The code flags those points with
> `efficiency_meaningful: false` and detects the boundary from the **sign of
> VOI**. This bit us once already: see §12.

Note the asymmetry, which is real mathematics rather than a quirk:

- The **unaided** arm is an unbiased Bayesian update, so Jensen's inequality
  guarantees its VOI ≥ 0. More data cannot hurt someone who updates correctly.
- **Our** arm is bias-corrected, so it carries no such guarantee.

We report this because it is true, because it is a property of bias-corrected
screening in general rather than of our implementation, and because it defines
the operating envelope a customer needs before buying. `voi.py --self-test`
**asserts the regime still exists**, so it cannot quietly disappear in a later
refactor.

---

## 6. The cost side, which we own completely

Everything above is a ratio. The one genuine money quantity is what it costs
**us** to run, because we can time our own service and cloud pricing is published.

Measured against the live API on 2026-08-14:

| | Measured |
|---|---|
| One screening pass | 6.52 s wall clock on 0.1 vCPU = **0.652 vCPU-seconds** |
| Marginal cost per extra fault hypothesis | **Indistinguishable from zero** — slope 95% CI [−0.035, +0.041] s across a 50× range |
| Cold start | **63.3 s** (free tier — a preview, not a deployment) |

The flat marginal cost **is the decoupling, showing up directly in wall clock.**
Going from 1 to 50 fault hypotheses does not change the runtime, because the
fault is not an input to the network — hypotheses are overlaid on a field that
has already been predicted. Gross margin is therefore structural, not projected.

**What we do not claim:** that we timed 20,000 hypotheses (we timed 50 — the
API's own cap — and the architecture carries the rest, which we say explicitly),
and any cost or speedup ratio against tNavigator, because **we have never timed
tNavigator.**

---

## 7. Market: hydrogen now, natural gas next, and *not* CO₂

We name two markets and stop. The reason is physical and computed, not asserted
— `src/economics/fluids.py`, CoolProp at 197.2 bar and 40 °C.

**The calibration check that makes the table trustworthy:** the module refuses to
emit anything unless CoolProp first reproduces the H₂ viscosity we had already
committed to in `LeakageConfig` (9.5e-06 Pa·s). It returns 9.5164e-06 — 0.2%
agreement. Only then does it report CH₄ and CO₂.

| Relative to H₂ | Viscosity | Density | **Buoyancy vs brine** |
|---|---|---|---|
| CH₄ | 1.93× | 10.4× | **0.88×** |
| CO₂ | 8.29× | 61.2× | **0.21×** |

**CH₄ is an interpolation from H₂. CO₂ is not.** Caprock leakage is
buoyancy-driven, and CO₂'s driving force against brine is ~5× weaker — so an
H₂-trained model would mis-rank CO₂ risk **systematically, not randomly**. CO₂ is
also injected monotonically rather than cyclically, and our U-Net carries a
literal cyclic-index input channel that would be meaningless there.

**So we do not claim CO₂, despite ₹20,000 crore of Indian CCUS budget sitting
there.** That restraint is the claim we most want a technical jury to test.

### What transfers, exactly

| Layer | Transfers? |
|---|---|
| Fault-decoupling method | **Fully** — it is a method, not a model |
| T3 leakage physics | **Fully** — one config constant (`h2_viscosity_pa_s`) |
| U-Net architecture, channels, training recipe | **Fully** — 4.23 h on a Kaggle T4, already measured |
| Features / XGBoost / SHAP / API / provenance tooling | Form transfers; weights refit |
| **Trained U-Net weights** | **No.** One retraining run per fluid. |

### Why natural gas storage, in India, now

India has begun building its **first strategic natural gas storage**, and
**depleted gas fields are the stated preferred option** — same reservoir class,
same cyclic inject/withdraw duty as UHS. GAIL, ONGC and Petronet LNG are all
MC²+ members, so the buyer, the reservoir and the data all sit inside the
consortium.

Hydrogen stays the long game, and we should say plainly that it is not here yet:
the National Green Hydrogen Mission targets 5 MMT/yr by 2030, and roughly
**8,000 t/yr** was commissioned as of February 2026. Being the team that names
that gap — and shows a costed path to the market that already exists — is a
credibility position, not a weakness.

---

## 8. The business model

**What we sell:** not a simulator licence. We would lose to tNavigator and
ECLIPSE on features and should not pick that fight. We sell an **auditable
containment-risk statement** — a provenance-tagged number that survives a
permitting or insurance conversation. Our own round-one script had already found
this: *"the one operators need and the one nobody else is offering."*

**How it is priced:** a rational operator pays less than the VOI. So
willingness-to-pay is bounded by arithmetic rather than asserted, and the cost
floor is measured. **VOI is the pricing model.**

| Stage | Offer |
|---|---|
| 1. Land | Paid co-screening study alongside a decision already being taken |
| 2. Expand | Per-asset annual subscription — re-screen as the geological model updates |
| 3. Defend | Assurance / methodology role as storage permitting rules are written |

**The ask to MC²+ — not capital:**

1. **One real depleted-field dataset.** Our biggest technical gap is that no real
   leakage ground truth exists, so our labels are our own physics. ONGC and Oil
   India hold real depleted-field models. We built the label as a swappable
   module precisely so this substitution is a config change, not a rewrite.
2. **One pilot co-screening study**, run alongside a screening decision being
   taken anyway, compared against the existing simulator workflow.

Both are cheap to grant, and only MC²+ can grant them.

---

## 9. Everything we do not claim

- **No ROI, no $/kg, no avoided-cost figure.** Efficiency is a ratio; the only
  price is our own compute.
- **No speedup or cost ratio against tNavigator** — we never timed it.
- **No CO₂ / CCUS capability.** The buoyancy table is why.
- **Efficiency 0.9974 does not mean the label is right.** It means we capture
  that share of the *available decision value*. The label remains ours,
  semi-analytical and uncalibrated — which is exactly what the ask is for.
- **Sensitivity/specificity come from a binormal ROC** fitted to the measured
  AUC, because held-out scores were never dumped. `src/train_xgb.py
  --dump-predictions` now exists and writes the empirical ROC if we want to
  replace the assumption.
- **The prior over site risk is deliberately diffuse.** We are claiming
  ignorance, not calibration.
- **Mitigation is modelled as removing the loss entirely.** Partial mitigation
  would lower both arms.

---

## 10. How the assumption register enforces all this

`src/economics/assumptions.py` is the module that decides which numbers are
allowed on a slide. It extends the `[DATASET]` / `[DERIVED]` / `[ASSUMED]` tags
from `src/config.py` with one more that physics did not need:

**`[UNVERIFIED]` — no source we have opened.** The rule attached to it is
absolute and enforced by an assertion in the constructor: an UNVERIFIED quantity
**may be swept and may never carry a point value.** Try to give one a value and
the module refuses to import.

The bar is set there because of this project's own history: `Data_sources_
research.md` was AI-generated and shipped fabricated datasets and an inverted
viscosity claim. The lesson taken was *do not accept a price figure from anyone,
including a model, without a source you have opened.* Nobody on this team has
opened a source for a workover cost, so no workover cost gets a point value.

What survives the rule is very little, and that is the point:

| Status | Count | Examples |
|---|---|---|
| MEASURED | 5 | PR-AUC simulator/surrogate, positive rate, API latency |
| DERIVED | 1 | hypotheses per field prediction |
| ASSUMED | 2 | prior site risk, hypotheses an operator can simulate |
| **UNVERIFIED** | **3** | mitigation/loss ratio, H₂ price, workover cost — **swept only** |

The headline result consumes only the MEASURED quantities plus swept ranges. The
H₂ price and workover cost are listed but **not consumed at all** — they are in
the register so the omission is visible rather than quiet.

---

## 11. Where every number lives

| Claim | File |
|---|---|
| Efficiency 0.9974 vs 0.00, the harmful boundary, all sweeps | `outputs/voi_results.json` |
| Fluid properties, transfer table, calibration check | `outputs/fluid_properties.json` |
| Unit cost, marginal-cost regression, timings | `outputs/unit_cost.json` |
| Every input with its provenance tag | `outputs/assumption_register.json` |
| Surrogate vs simulator degradation | `outputs/source_comparison.json` |
| Slide-ready commercial case | `docs/COMMERCIAL.md` |
| The 4–5 minute pitch | `docs/PRESENTATION_SCRIPT_FINALS.md` |

**Sources for the market claims:**
[strategic gas storage](https://www.businessworld.in/article/india-plans-strategic-natural-gas-storage-to-bolster-energy-security-after-west-asia-crisis-613462) ·
[ONGC/OIL depleted fields](https://psuwatch.com/newsupdates/exclusive-ongc-oil-to-use-depleted-oil-fields-for-carbon-sequestration-gas-storage) ·
[NGHM](https://mnre.gov.in/en/national-green-hydrogen-mission/) ·
[CCSNet prior art](https://ccsnet.ai/)

> **Prior art, worth knowing before someone tells you:** Stanford's CCSNet
> (Wen & Benson) already published a deep-learning surrogate for CO₂ storage with
> an open dataset. So "AI surrogate for storage" is **not** our novelty and we
> must never present it as such. Our novelty is the **fault-hypothesis layer**,
> which sits on top of *any* surrogate — including someone else's. That is also
> why it survives every fluid swap.

---

## 12. Two mistakes we made building this, and what they cost

Recorded in the same spirit as `docs/FINDINGS.md`: if a judge asks how we know
the numbers are right, "we found our own bugs and wrote them down" is a better
answer than "they looked plausible."

### Mistake 1 — the flattering framing

The first model treated a dangerous site as containing ~387 dangerous fault
hypotheses (the pooled positive rate × 20,000). Detection was then trivial and
efficiency saturated at **1.0000 screened vs 0.0000 unaided** — a stark-looking
result that was really an artefact of the setup.

The fix came from our own pitch language: *twenty thousand guesses about **one**
crack*. There is one fault, nobody observes it, and both parties are estimating
the same probability. That reframing produced the bias–variance comparison in §4,
which is both harder to attack and more interesting.

**Lesson:** a number that makes you look perfect is a bug report.

### Mistake 2 — a sign error in the Rogan-Gladen inversion

`screened_threshold()` solves for the true θ at which the screen's estimate
crosses the decision line. The calibration-error term had **its sign inverted**.

It was nearly invisible, for a bad reason: the two terms cancel exactly whenever
the true and estimated specificities agree — which is almost always, since
specificity is measured on 15,603 negative rows. So the bug only bit in the one
place the module exists to model: **calibration error**.

It was caught during PR review, by checking the function against an *independent*
restatement of the estimator rather than against the same algebra. What it had
been corrupting was precisely the harmful-regime result: it reported the screen
as value-destroying at a cost ratio of 1e-4 (efficiency −0.135). With the sign
corrected, that boundary moves to **6.2e-5 — below the plausible range** — and
the base-case efficiency shifts 0.9975 → 0.9974.

So the corrected story is *better* for us, which is exactly why it needed
checking rather than accepting.

`--self-test` now verifies the threshold round-trips through an independently
written form of the estimator, at four calibration configurations plus the
perfectly-calibrated case where θ\* must equal the cost ratio exactly.

**Lesson:** assert against an independent restatement, not against a rearrangement
of the same expression.
