# Commercial case: how HyLeakAI scales as a business

> In the online evaluation round, judges inquired about our business model. Module 4 (Economics) in [economics](file:///Users/sonil/Desktop/HyLeakAI/src/economics) addresses that question directly. The module generates a defensible Value of Information framework rather than an ungrounded ROI figure. Section 2 details why this strategy provides a stronger analytical position.

---

## 1. Value proposition and market position

We do not sell a full reservoir simulator or a software license competing against tNavigator or ECLIPSE. We sell **an auditable containment-risk statement for a storage site**: a defensible, provenance-tagged risk quantification suitable for permitting and insurance evaluation.

The technical core relies on **decoupling fault properties from field predictions**: because the surrogate predicts fields without taking fault parameters as inputs, one field prediction can be evaluated against thousands of fault hypotheses in real time. This converts single-fault deterministic simulation into comprehensive hypothesis sweeping across unconstrained fault parameter spaces.

**Delivery stages:**

| Stage | Offer | Strategy |
|---|---|---|
| 1. Land | Co-screening study alongside an existing operator evaluation | Evaluates performance directly against existing workflows on client assets |
| 2. Expand | Per-asset annual subscription for continuous re-screening | Re-evaluates risk whenever updated well logs or geological models arrive |
| 3. Defend | Assurance and methodology validation as storage permitting rules evolve | Establishes our method as the accepted industry benchmark |

---

## 2. Value of Information (VOI) framework

Calculating a traditional ROI requires knowing the actual hydrogen leakage fraction. **No public dataset worldwide provides measured hydrogen leakage data**, as documented in [Data_sources_research.md](file:///Users/sonil/Desktop/HyLeakAI/Data_sources_research.md) section 1. Multiplying uncalibrated physics labels by energy prices yields arbitrary financial figures.

Therefore, [voi.py](file:///Users/sonil/Desktop/HyLeakAI/src/economics/voi.py) computes **Value of Information (VOI)**: the standard petroleum decision analysis methodology for valuing information based on its ability to optimize decisions under uncertainty.


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

**So we do not claim CO₂**, despite CO₂/CCUS being where the money currently
is — on the order of **₹20,000 crore** of committed Indian budget, the largest
of the three markets by far. That restraint is the claim we most want a
technical jury to test.

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

### Market size, side by side

| Market | Where it stands | Sequencing |
|---|---|---|
| Hydrogen storage | ~8,000 t/yr commissioned vs. 5 MMT/yr by 2030 — early, small | **Now** — the market we were built and validated for |
| Natural gas storage | Active buildout, depleted fields the stated preferred reservoir, buyer already in-consortium | **Next** — one retraining run away, fastest path to a paid pilot |
| CO₂ storage (CCUS) | ~₹20,000 crore committed budget — largest by far | **Not yet** — physics doesn't transfer; revisit after an architecture change for monotonic injection, or with real CO₂ field data |

**What closing the CO₂ gap actually takes** (not a retrain — a redesign):

1. Redesign the cyclic-index channel for monotonic (one-way) injection.
2. Re-derive the buoyancy term — CO₂'s driving force is ~5× weaker than H₂'s,
   not a config-constant swap like CH₄.
3. Retrain and independently validate against a held-out check, not just retrain.
4. Ground it in real CO₂ leakage data or a validated CO₂ simulator — the
   "close enough to H₂" argument that covers CH₄ doesn't apply here.

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

## 5. Explicit limitations

Carried forward from [PRESENTATION_CONTEXT.md](file:///Users/sonil/Desktop/HyLeakAI/docs/PRESENTATION_CONTEXT.md) section 14, with economics additions:

- No ROI, no $/kg, and no "avoided cost" figure. Efficiency represents a **ratio**; compute usage represents our only direct cost.
- No speedup or cost comparisons against tNavigator (we benchmarked surrogate speed directly without timing proprietary software).
- No CO2 or CCUS claims. The physical buoyancy table above explains why H2 models do not transfer directly to CO2.
- The screening ceiling depends on receiver sensitivity and specificity bounds (evaluated on ~308 positive held-out scenarios). Increasing fault hypothesis counts cannot exceed this upper bound without improved classifier calibration.
- An efficiency value of 0.9974 measures the percentage of available decision value captured. It does not certify that the underlying T3 semi-analytical physics label represents true field leakage rates.

---

## Sources

- India strategic gas storage, depleted fields preferred: [BW Businessworld](https://www.businessworld.in/article/india-plans-strategic-natural-gas-storage-to-bolster-energy-security-after-west-asia-crisis-613462)
- ONGC / Oil India, depleted fields for sequestration and gas storage: [PSU Watch](https://psuwatch.com/newsupdates/exclusive-ongc-oil-to-use-depleted-oil-fields-for-carbon-sequestration-gas-storage)
- National Green Hydrogen Mission targets: [MNRE](https://mnre.gov.in/en/national-green-hydrogen-mission/)
- Prior art on storage surrogates: [CCSNet, Wen & Benson, Stanford](https://ccsnet.ai/)

Internal outputs: `outputs/voi_results.json`, `outputs/unit_cost.json`, `outputs/fluid_properties.json`, `outputs/assumption_register.json`.

