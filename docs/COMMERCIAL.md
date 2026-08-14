# Commercial case — how HyLeakAI becomes a business

> A judge in the online round asked how we would make a business out of this and
> we had no answer, because Module 4 (Economics) was the one module in our own
> README marked **Not Started**. This document and `src/economics/` are that
> answer. The module is now built, and it deliberately does not produce an ROI —
> Section 2 explains why that is the stronger result.

---

## 1. What we sell

Not a reservoir simulator, and not a licence competing with tNavigator or
ECLIPSE. We would lose that fight on features and should not pick it.

We sell **an auditable containment-risk statement for a storage site** — a
defensible, provenance-tagged number that survives a permitting or insurance
conversation. Our own round-one script already identified this as the wedge:

> "A permit or an insurance case needs a defensible number... the one operators
> need and the one nobody else is offering."

The technical asset behind it is not the neural network. It is the **decoupling**:
the fault is not an input to the surrogate, so one field prediction is re-scored
against thousands of fault hypotheses. That turns "simulate the one fault you
happened to think of" into "sweep the space of faults you cannot rule out", which
is what an auditable statement actually requires.

**Delivery model, in order:**

| Stage | Offer | Why it comes here |
|---|---|---|
| 1. Land | Paid co-screening study alongside a decision the operator is already taking | No procurement fight; we are measured against their existing workflow on their own site |
| 2. Expand | Per-asset annual subscription — re-screen as the geological model updates | Screening is not one-shot; every new well log changes the prior |
| 3. Defend | Assurance / methodology role as storage permitting rules are written | The moat is being the accepted method, not the fastest code |

---

## 2. Why there is no ROI number here, and what replaces it

An ROI needs a leakage loss fraction. **No public dataset anywhere in the world
contains hydrogen leakage measurements** — that absence is the founding premise
of this project, documented in `Data_sources_research.md` §1. Multiplying an
uncalibrated label by a hydrogen price does not create knowledge; it puts a
currency symbol on an order-of-magnitude uncertainty.

So `src/economics/voi.py` computes **Value of Information** instead — the
framework petroleum decision analysis already uses for exactly this question. VOI
prices information by how much it changes a decision. It needs the decision
structure and the reliability of the screen; it does not need the true leak rate.

### What is actually being valued: coverage, not accuracy

A site has **one** unknown fault. Nobody observes it — not the simulator, not us.
Both parties are estimating the same quantity: the probability that this site's
fault is conductive enough to matter. They differ only in how well:

| | Coverage | Error |
|---|---|---|
| **Unaided operator** | k ≈ 2 hypotheses, simulated exactly | Unbiased, hopeless variance — at k = 2 the only estimates available are 0, ½, 1 |
| **HyLeakAI** | 20,000 hypotheses at measured skill | Sampling noise negligible; error is the **bias from our own calibration** |

This is a bias–variance trade, and it is the honest form of the comparison. The
unaided operator is not modelled as ignorant or as using a worse tool — they are
modelled as using a **better** tool on a sample far too small to cover the
uncertainty.

### Result

Screen efficiency is **VOI / VOPI**: the share of the available decision value
captured, bounded at 1 by construction. It is **dimensionless**, so it carries no
invented price at all.

| Arm | Hypotheses | VOI / VOPI |
|---|---|---|
| Unaided (exact simulator) | 2 | **0.00** |
| HyLeakAI screen | 20,000 | **0.9974** |
| Perfect information | — | 1.00 |

Raising the simulator budget to 20 exact runs still yields **0.00** — because at
the base cost ratio, two or twenty samples never move the decision across the
threshold. Coverage, not accuracy, is what is scarce.

**The speedup is nearly free in decision terms.** Swapping the simulator's fields
for the U-Net's costs **0.000178** of efficiency (AUC 0.99987 → 0.99963). That is
the number that matters to an operator asking whether the AI is good enough to
decide on, and it is measured on 150 held-out simulations.

### Where it stops being worth running

There is a regime where the screen is worth **less than nothing**: below a
mitigation-to-loss ratio of **6.2e-5**, VOI turns negative. When mitigation is
that cheap the right move is to mitigate almost regardless, so an imperfectly
calibrated screen can only talk you out of it.

**That boundary sits below the plausible range** (1e-4 to 1e-1), so across every
cost ratio we consider credible, the screen never destroys value. We quote it
anyway — knowing where a tool fails is worth more than claiming it does not.

Note the asymmetry, which is real mathematics and not a quirk of implementation:
the unaided arm is an unbiased Bayesian update, so Jensen's inequality guarantees
its VOI ≥ 0; ours is bias-corrected and carries no such guarantee.
`--self-test` asserts both that the harmful regime still exists at very low cost
ratios and that it does **not** reach the base case.

### VOI is also the pricing model

A rational operator pays less than VOI for the screen. So willingness-to-pay is
bounded by arithmetic rather than asserted — and the cost side is measured:

| | Measured |
|---|---|
| One screening pass | 6.52 s wall clock on 0.1 vCPU = **0.65 vCPU-seconds** |
| Marginal cost per extra fault hypothesis | **Below the noise floor** across a 50× range (slope 95% CI [−0.035, +0.041] s) |
| Cold start | 63.3 s (free tier; a preview, not a deployment) |

The flat marginal cost **is** the decoupling, showing up directly in wall clock:
adding hypotheses does not re-run the network. Gross margin is therefore
structural, not a projection.

---

## 3. Market sequence — hydrogen now, natural gas next

We name two markets and stop there. The reason is physical, and computed rather
than asserted (`src/economics/fluids.py`, CoolProp at 197.2 bar / 40 °C, verified
against the H₂ viscosity already committed to in `LeakageConfig`):

| Relative to H₂ | Viscosity | Density | **Buoyancy vs brine** |
|---|---|---|---|
| CH₄ | 1.93× | 10.4× | **0.88×** |
| CO₂ | 8.29× | 61.2× | **0.21×** |

**CH₄ is an interpolation from H₂. CO₂ is not.** Caprock leakage is
buoyancy-driven, and CO₂'s driving force is ~5× weaker — an H₂-trained model
would mis-rank CO₂ risk *systematically*, not randomly. CO₂ is also injected
monotonically rather than cyclically, and our U-Net carries a literal cyclic-index
input channel that would be meaningless there.

**So we do not claim CO₂**, despite it being where the money currently is. That
restraint is the claim we most want a technical jury to test.

### What transfers, exactly

| Layer | Transfers? |
|---|---|
| Fault-decoupling method | **Fully** — a method, not a model |
| T3 leakage physics | **Fully** — one config constant (`h2_viscosity_pa_s`) |
| U-Net architecture, channels, training recipe | **Fully** — 4.23 h on a Kaggle T4, already measured |
| Features / XGBoost / SHAP / API / provenance tooling | Form transfers; weights refit |
| **Trained U-Net weights** | **No.** One retraining run per fluid. |

### Why natural gas storage, in India, now

India has begun building its **first strategic natural gas storage**, and
**depleted gas fields are the stated preferred option** — the same reservoir
class, the same cyclic inject/withdraw duty as UHS. GAIL, ONGC and Petronet LNG
are all MC²+ members, so for this market the buyer, the reservoir and the data
sit inside the consortium.

Hydrogen remains the long game, and we should say plainly that it is not here
yet: the National Green Hydrogen Mission targets 5 MMT/yr by 2030, and roughly
**8,000 t/yr** was commissioned as of February 2026. Being the team that states
that gap, and shows a costed path to the market that already exists, is a
credibility position rather than a weakness.

---

## 4. The ask

MC²+ offers infrastructure, piloting sites, capital and expertise across seven
energy majors. What we need most is not capital.

**1. One real depleted-field dataset.** Our largest technical gap is that no real
leakage ground truth exists anywhere, so our labels are our own physics. ONGC and
Oil India hold real depleted-field models. One of them turns a semi-analytical
label into a calibrated one. We built the label as a swappable module precisely
so this substitution is a configuration change, not a rewrite.

**2. A pilot co-screening study.** Run HyLeakAI alongside a screening decision
being taken anyway, and compare against the existing simulator workflow. That
gives us a reference customer, and gives the consortium a measured answer to
"does surrogate screening change what we would have decided?"

Both are cheap to grant, and only MC²+ can grant them.

---

## 5. What we do not claim

Carried forward from `docs/PRESENTATION_CONTEXT.md` §14, with the economics
additions:

- No ROI, no $/kg, no avoided-cost figure. Efficiency is a **ratio**; the only
  price is our own compute.
- No speedup or cost ratio against tNavigator — **we never timed it.**
- No CO₂ / CCUS capability. The buoyancy table above is why.
- The screen's ceiling is set by how well Se/Sp are known, and sensitivity rests
  on ~308 positive held-out rows. **More hypotheses cannot raise that ceiling** —
  only a better-characterised classifier can.
- Efficiency of 0.9974 says how much of the *available decision value* the screen
  captures. It does **not** say the underlying T3 label is correct. That label is
  ours, semi-analytical, and uncalibrated — see the ask.

---

## Sources

- India strategic gas storage, depleted fields preferred — [BW Businessworld](https://www.businessworld.in/article/india-plans-strategic-natural-gas-storage-to-bolster-energy-security-after-west-asia-crisis-613462)
- ONGC / Oil India, depleted fields for sequestration and gas storage — [PSU Watch](https://psuwatch.com/newsupdates/exclusive-ongc-oil-to-use-depleted-oil-fields-for-carbon-sequestration-gas-storage)
- National Green Hydrogen Mission targets — [MNRE](https://mnre.gov.in/en/national-green-hydrogen-mission/)
- Prior art on storage surrogates (not our novelty — the fault layer is) — [CCSNet, Wen & Benson, Stanford](https://ccsnet.ai/)

Internal: `outputs/voi_results.json`, `outputs/unit_cost.json`,
`outputs/fluid_properties.json`, `outputs/assumption_register.json`.
