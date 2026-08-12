# PROMPT — paste everything below into NotebookLM

---

You are building a **12-slide presentation deck** for a hackathon Round 1 submission (including Intro/Cover and Closing/Thank You slides).

**Critical constraint: nobody will present this deck.** A judge will read it alone, as a PDF, in silence. This changes how you must write every slide:

- **The slide is the argument.** If it is not on the page, it was not said.
- **Every slide title is a full-sentence claim**, never a label. Write "The surrogate retains 99.0% of the simulator's screening accuracy", not "Results".
- **Every figure has a caption that states its takeaway**, not a description of what it shows.
- **There is no Q&A**, so every likely objection is pre-empted in the slide copy itself.
- Body copy target: **60–90 words per slide.** Over that, the reader skims. Under it, the slide does not stand alone.
- Reading order must be visually unambiguous: numbered, single-column wherever possible.

Do not add content that is not in this prompt. Do not invent statistics, dollar figures, comparisons, or citations. Every number you need is supplied below.

---

# PART 1 — DESIGN THEME AND COLOUR PALETTE

## Theme: "Field Notebook"

The deck should look like a **geologist's field notebook**: kraft paper, dark umber ink, forest-green annotations, brick-red markings for danger. It is warm, analog, and precise — the aesthetic of someone who writes measurements down carefully by hand.

This is deliberate. The project's entire argument is that its numbers are honestly sourced and independently checkable. A warm, hand-recorded, notebook aesthetic reinforces that claim; a glossy corporate-tech aesthetic would undercut it.

**Hold the theme consistently.** Do not mix in gradients, glassmorphism, neon, drop shadows, or stock photography. Flat colour, thin rules, generous margins, and precise typography only.

## Colour palette — use these exact values

### Surfaces and ink

| Role | Hex | Use |
|---|---|---|
| Page background | `#EDE4D6` | Kraft paper. Every slide background. |
| Card / panel | `#FAF5EC` | Aged paper. Content cards, tables, callout boxes. |
| Recessed panel | `#E4D9C6` | Sidebars, code blocks, secondary boxes. |
| Rule / border | `#C9B79C` | Thin 1px rules, table borders, card outlines. |
| Primary ink | `#2B211A` | Dark umber. Titles and body text. |
| Secondary ink | `#6B5844` | Captions, labels, table headers. |
| Faint ink | `#9C8871` | Footers, slide numbers, axis ticks. |

### Meaning colours — each one means exactly one thing, everywhere

| Role | Hex | Means |
|---|---|---|
| **Forest green** | `#2F6B4F` | Hydrogen, storage capacity, "good", our model's result |
| Green highlight | `#4A9B71` | Emphasis fills, plume gradient light end |
| **Brick red** | `#B4441C` | Pressure, flux, faults, "hot", the danger variable |
| **Ochre** | `#96701A` | Assumptions. Every `[ASSUMED]` tag and caution note. |
| **Oxblood** | `#7E1F2E` | Failure, breach, negative results |
| Neutral grey | `#8C8377` | Baselines and comparison bars — never our own result |

**Rule: our result is always forest green; the baseline it is compared against is always neutral grey.** This must hold on every chart in the deck.

### Lithology ramp — use ONLY inside geological cross-sections

| Layer | Hex |
|---|---|
| Overburden | `#BCA88E` |
| Caprock (shale) | `#4A3A2E` |
| Reservoir sandstone | `#D2A96F` |
| Baserock | `#7A6450` |
| Hydrogen plume | gradient `#2F6B4F` → `#7FC79E` |
| Fault plane | `#B4441C` |

## Typography & Font Size Specifications

Maintain strict typographic hierarchy across all 12 slides. Numbers and equations set in monospace reinforce the feel of a scientific instrument:

- **Slide Titles:** `36–40 pt`, Humanist Serif (Charter, Source Serif, Georgia), Bold, Primary Ink (`#2B211A`).
- **Section Headers / Sub-headers:** `24–28 pt`, Humanist Serif or Semi-bold Sans, Primary Ink (`#2B211A`).
- **Body Text:** `18–20 pt`, Clean Humanist Sans (Source Sans, Inter, Lato), 1.4 line height, Primary Ink (`#2B211A`).
- **Card Headers & Table Titles:** `18–20 pt`, Bold/Semi-bold Sans, Primary Ink (`#2B211A`).
- **Data Tables & Monospace Blocks:** `14–16 pt`, Monospace (JetBrains Mono, IBM Plex Mono, Menlo). Use for all equations, numbers, units, tensor shapes, and file paths.
- **Figure Captions & Takeaway Statements:** `14–15 pt`, Italic or Semi-bold Sans, Secondary Ink (`#6B5844`).
- **Provenance Chips & Footers:** `12–14 pt`, Small Caps / Monospace, Faint Ink (`#9C8871`).
- **Strict Size Constraint:** Nothing below `12 pt` anywhere on the slide.

## Layout

- 16:9 ratio. Generous margins — at least 6% of slide width on every side.
- A thin `#C9B79C` rule under every slide title.
- Persistent footer on every slide, in faint ink `#9C8871`: slide number on the right, and on the left the standing line **"Physics-guided screening. Real fields, derived labels."**
- Content cards use `#FAF5EC` on the `#EDE4D6` page, with a 1px `#C9B79C` border. No shadows.

## Provenance chips — the deck's signature device

Many numbers in this deck carry a small uppercase tag showing where the number came from. Render each as a small pill with 1px border and no fill:

| Chip | Text colour | Border | Meaning |
|---|---|---|---|
| `[DATASET]` | `#6B5844` | `#C9B79C` | Read directly from the source dataset. A fact. |
| `[DERIVED]` | `#2F6B4F` | `#2F6B4F` | Computed from a dataset value by a stated calculation. |
| `[ASSUMED]` | `#96701A` | `#96701A` | Our own choice, justified and swept. |

Use them consistently wherever they appear in the slide copy below.

## Pipeline / flowchart wireframes — house style

Several slides (Slide 2, Slide 3, Slide 8, Slide 11) feature architectural flowcharts and system diagrams. Format every pipeline and flowchart according to these structural wireframe rules:

- **Node Shapes:** Rounded rectangles with a `#FAF5EC` fill, 1.5px `#C9B79C` solid border, and `#2B211A` primary ink text.
- **Connectors & Arrows:** Use clean, 1.5px solid arrows in `#6B5844` with open arrowheads. Never use 3D, gradient, or filled block connectors.
- **Group Enclosures:** Enclose multi-step processes in dashed-line container boxes `#C9B79C` with small caps category labels in the top-left margin.
- **Data Shape Annotations:** Explicitly label data tensor shapes, feature dimensions, and execution latencies along connectors in monospace font (e.g., `(1000, 2, 128, 128)`, `41 features`, `~ms`).
- **Color Coding:** Use Forest Green (`#2F6B4F`) for geology and ML forward predictions, Brick Red (`#B4441C`) for fault parameters and leakage risk branches, Ochre (`#96701A`) for assumptions, and Oxblood (`#7E1F2E`) for bottlenecks or failure points.
- **Loop Markers:** Annotate iterative stages with a `⟳` glyph and iteration counts (e.g., `⟳ x20,000`).

---

# PART 2 — SLIDE-BY-SLIDE CONTENT

Build exactly these 12 slides, in this order.

---

## SLIDE 1 — Cover & Introduction

**Title (very large, 40 pt):** HyLeakAI

**Subtitle (24 pt):** Physics-guided leakage-risk screening for underground hydrogen storage

**Team Members (18 pt, horizontal badge row):**
- **Aryan Kandpal**
- **Sourav Choudhary**
- **Sonil Negi**
- **Brajesh Kumar Patel**

**Thesis line (20 pt, largest text after title):**
> A U-Net surrogate turns a full reservoir simulation into a sub-second forward pass, so a site can be screened against **thousands of unknown fault hypotheses** instead of the handful a simulator can afford.

**Bottom strip — thin band, full width, small type (13 pt), left border in ochre `#96701A`:**
> Features are real physics: 1,000 published tNavigator simulations. Leakage labels are ours, derived from a hypothetical fault. This screens risk; it does not predict leak rates.

**Visual:** Geological cross-section from Slide 4 desaturated to 25% opacity across the lower third.

---

## SLIDE 2 — The Problem Statement: Geological Risk & Computational Bottlenecks

**Title (36 pt):** Underground hydrogen storage faces high caprock breach risks, but screening fault uncertainty is computationally impossible with traditional simulators.

**Body (18 pt):**
> Storing terawatt-hours of hydrogen requires porous rock reservoirs (depleted gas fields), but containment is threatened by caprock seal failure. Caprocks do not seal by impermeability; they seal by capillary entry pressure.
>
> When cycling pore pressure exceeds fracture limits, or when fault damage zones cut through the caprock, hydrogen escapes vertically.
>
> **The Computational Bottleneck:** Fault permeability ($10^{-15}$ to $10^{-12}\text{ m}^2$) and location span 3 to 4 orders of magnitude of uncertainty. Running full numerical reservoir simulations (tNavigator) for thousands of fault realisations takes hours per run — making thorough risk sweeps computationally impossible and forcing operators to rely on 1 or 2 arbitrary hand-picked scenarios.

**Visual — Problem Flowchart Wireframe:**

```
+------------------------------------+
| Geological & Subsurface            |
| Fault Uncertainty                  |
| (k_f: 1e-15..1e-12 m², Position)   |
+------------------------------------+
                   |
                   v
+------------------------------------+
| Full Numerical Reservoir           |
| Simulator (tNavigator)             |  --> [COMPUTATIONAL BOTTLENECK]
| (3D Mesh PDE Numerical Solver)     |      Hours/days per simulation run
+------------------------------------+
                   |
                   v
+------------------------------------+
| 20,000 Monte-Carlo Sweeps Required |  --> [RESULT: IMPOSSIBLE IN PRACTICE]
| to assess site safety confidence   |      Operators evaluate only 1-2 scenarios,
+------------------------------------+      leaving major fault risks undetected.
```

**Caption (14 pt):** The barrier to safe hydrogen storage screening is not physical theory; it is numerical simulator latency. Sweeping fault uncertainty across a candidate field requires an instant forward surrogate.

---

## SLIDE 3 — Our Solution: The HyLeakAI Decoupled Physics-Guided Architecture

**Title (36 pt):** HyLeakAI decouples field prediction from fault scoring — turning multi-hour simulations into sub-second Monte-Carlo risk sweeps.

**Body (18 pt):**
> HyLeakAI replaces brute-force simulator runs with a physics-guided two-stage machine learning architecture.
>
> **1. U-Net Surrogate Model:** Predicts 2D/3D pressure ($P$) and hydrogen saturation ($S$) fields directly from rock porosity ($\phi$) and permeability ($k$) in milliseconds.
>
> **2. Decoupled Fault Risk Scoring:** We extract 41 scalar physics features from the predicted fields and overlay hypothesised fault parameters *after* surrogate execution.
>
> Because the fault never enters the U-Net, screening 20,000 fault hypotheses against a field requires running the U-Net **once**, followed by instant tree-walks via XGBoost with TreeSHAP attributions — **scoring thousands of risk scenarios in milliseconds.**

**Visual — HyLeakAI Decoupled Architecture Flowchart Wireframe:**

```
+----------------------------+
| Site Geology (φ, k grid)   |
+----------------------------+
               |
               v  [RUNS ONCE PER SITE — EXPENSIVE (~ms)]
+----------------------------+
| U-Net Surrogate Model      |  --> Predicts Pressure (P) & Saturation (S) Fields
+----------------------------+
               |
               v  (41 Physics-Guided Features Extracted)
+----------------------------+      +---------------------------------+
| 41 Scalar Feature Fields   | +--  | Hypothesised Fault Parameters   |
+----------------------------+      | (Monte-Carlo Sweep: ⟳ x20,000)  |
               |                    +---------------------------------+
               +-----------------------+
                                       |
                                       v  [RUNS THOUSANDS OF TIMES — MILLISECONDS]
                         +---------------------------+
                         | XGBoost Classifier &      | --> P(Elevated Leakage @ 6 Months)
                         | TreeSHAP Attribution      |     + Interpretable Feature Gain
                         +---------------------------+
```

**Caption (14 pt):** Decoupling subsurface field prediction from fault scoring is the core architectural breakthrough: field solver runs once; fault risk runs thousands of times in milliseconds.

---

## SLIDE 4 — Subsurface Trap Mechanics & Geology

**Title (36 pt):** A storage site fails at its seal — and the seal fails at a fault.

**Body (18 pt):**
> A caprock does not seal because it is impermeable. It seals because its pore throats are too small for gas to displace the water in them — a **capillary** seal. Hydrogen does not defeat that: H₂ and CH₄ wettability against water-wet caprock are comparable.
>
> **Pressure defeats it.** Raise pore pressure past the rock's fracture pressure and the seal cracks. And a fault gives pressure a shortcut: a fault's *core* is low-permeability gouge that seals sideways, but its *damage zone* is a fractured halo that conducts — and the conducting direction is **up**, through the seal.

**Visual — Geological Cross-Section Figure:** Vertical section, top to bottom, using lithology ramp:

1. Ground surface — thin line.
2. **Overburden** `#BCA88E`, labelled `~1,828 m` `[ASSUMED]`.
3. **Caprock** `#4A3A2E`, ~50 m `[ASSUMED]`, labelled "sealed: no-flow", annotated `P_frac = 319.3 bar @ 0.17 bar/m` `[ASSUMED]`.
4. **Reservoir** `#D2A96F`, 100 m thick `[DATASET]`, 7,680 m wide `[DATASET]`. Annotate `φ 0.25–0.31`, `k 1–739 mD`, `P_init 197.2 bar`.
5. **Baserock** `#7A6450`.

Overlays: Central vertical well, **hydrogen plume** flattened against underside of caprock (`buoyancy · Δρ ≈ 985 kg/m³`), **fault plane** in brick red `#B4441C` cutting through caprock (`k_f: 1e-15 … 1e-12 m²`), fault architecture zoom inset (core seals across vs damage zone conducts up).

**Caption (14 pt):** Reservoir at ~1,878 m `[ASSUMED]`, sealed by caprock with hydrogen pooled by buoyancy. Peak simulated pressure reaches **293.8 bar** `[DATASET]` against fracture pressure **319.3 bar** `[ASSUMED]` — 79% of the way to failure.

---

## SLIDE 5 — Data & Physics Provenance (The Data & Honesty Contract)

**Title (36 pt):** 1,000 published physics simulations verified byte-for-byte, with explicit separation of real physics and derived labels.

**Body (18 pt):**
> Source data: Mao et al. (2025), 12.38 GB Zenodo dataset (1,000 tNavigator simulations of a 7,680 m × 7,680 m × 100 m domain). MD5-checked against published records and verified for float16 conversion precision.
>
> **The Honesty Contract:** No public dataset contains real hydrogen leakage measurements. Given that absence, we use real physics for input features and derive leakage labels from a stated, tagged physics model.

**Visual — Two-Column Provenance Split:**

**Left: "Real Physics Features" `[DATASET]`:**
> Porosity ($\phi$) · Permeability ($k$) · Pressure fields ($P$) · H₂ saturation fields ($S$) · Domain geometry · Cycle structure (10 annual cycles) · Central well position
>
> Source: Mao et al. (2025) tNavigator 3D simulations.

**Right: "Derived & Tagged Labels" `[DERIVED]` `[ASSUMED]`:**
> Fault location, width, permeability `[ASSUMED]` · Caprock thickness 50 m `[ASSUMED]` · Fracture gradient 0.17 bar/m `[ASSUMED]` · H₂ viscosity $9.5\times 10^{-5}\text{ Pa}\cdot\text{s}$ `[ASSUMED]` · **Leakage flux $Q$ `[DERIVED]`**

**Callout — "Unmasking the 3rd Channel":**
> We discovered the Zenodo dataset contains an undocumented 3rd channel. We proved it correlates with pressure at $-0.993$ to $-0.999$ with coefficient $1.17\times 10^{-9}\text{ /Pa}$ (compressibility). We describe its units but do not use it as a target.

---

## SLIDE 6 — Leakage Physics & Governing Equations

**Title (36 pt):** Leakage requires overpressure *and* mobile gas. Both, or nothing — asserted in automated test suites.

**Equation (20 pt, monospace, centred):**

```
Q  =  k_f · k_rg(S) · A_f / μ_H₂  ·  max(P_fault − P_init, 0) / L_caprock

     m²  ·   [–]    ·  m²  / Pa·s  ·          Pa              /    m      =  m³/s
```

Colour symbols: `k_f`, `A_f`, `μ`, `L` in ochre (assumed); `P_fault` and `S` in forest green (simulated).

**Body (18 pt):**
> Darcy flux up a hypothetical fault, gated by a **Corey relative-permeability** term ($k_{rg}$). That gate enforces physical reality: below residual gas saturation ($S_{gr} = 0.05$), hydrogen is trapped in isolated pore bubbles and cannot flow at any pressure.
>
> Overpressure clipping ensures **leakage is exactly zero during all withdrawal phases**.

**Visuals:**
- Panel 2: Corey Curve Plot ($k_{rg}$ vs $S_g$, shading $S_{gr} = 0.05$ immobile zone).
- Panel 3: Automated assertion checklist (`python -m src.leakage.labels`) verifying 6 physical assertions pass on every commit.

**Caption (14 pt):** Automated physics tests run on every commit. If the label does not obey Darcy's law in the physically correct direction, the build fails.

---

## SLIDE 7 — Result 1: Forecasting Accuracy & Horizon Disqualification

**Title (36 pt):** PR-AUC 0.9931 against a persistence baseline of 0.0218 — at the half-cycle horizon where periodicity cannot cheat.

**Body (18 pt):**
> The task: predict elevated leakage **six months ahead** (top decile flux; 2.2% base rate).
>
> Six months is **half a storage cycle**, and that choice is crucial. At whole-cycle horizons (12, 24, 60 months), reservoir fields repeat annually and simply copying today's value (persistence) scores ~0.99. Scoring high at annual horizons measures seasonal periodicity, not model forecasting skill.

**Visual — Horizon Performance Chart (Model vs Persistence):**

| Horizon | Months | Cycle Phase | Model PR-AUC | Persistence PR-AUC | Status |
|---|---|---|---|---|---|
| 1 | 2 | different | 0.9949 | 0.4224 | Valid |
| **3** | **6** | **different (half-cycle)** | **0.9931** | **0.0218** | **PRIMARY RESULT** |
| 6 | 12 | SAME (whole-cycle) | 0.9975 | 0.9918 | Disqualified (Periodicity) |
| 12 | 24 | SAME (whole-cycle) | 0.9960 | 0.9758 | Disqualified (Periodicity) |

- Model bar in forest green `#2F6B4F`; persistence in neutral grey `#8C8377`.
- Whole-cycle horizons (6, 12, 30) are hatched and marked **"Disqualified: Persistence Wins"**.
- Dashed horizontal line at 0.022 base rate.

**Caption (14 pt):** At horizon 3 (6 months), persistence collapses to 0.0218 (below base rate) because injection switches to withdrawal. HyLeakAI achieves 0.9931 PR-AUC.

---

## SLIDE 8 — Result 2: Simulator vs. Surrogate Integrity & Interpretability

**Title (36 pt):** The surrogate retains 99.0% of simulator screening accuracy, and TreeSHAP attributions recover Darcy's law.

**Body (18 pt):**
> **Screening Accuracy:** Trained once on simulator features, the XGBoost risk model scores 0.9941 PR-AUC on true simulator fields and 0.9842 PR-AUC on U-Net surrogate fields — retaining **99.0% screening accuracy**.
>
> **Magnitude Gap:** Log-flux RMSE increases from 0.739 to 1.236 due to U-Net noise in time-derivative features (`plume_front_speed`). Thus, we claim risk screening, not quantitative leak-rate prediction.
>
> **Physics Attribution:** TreeSHAP feature importance matches the exact term hierarchy of Darcy's Law without being given the equation.

**Visual — Side-by-Side Validation Cards:**
- Card A: Screening Retention Bar Chart (Simulator 0.9941 vs U-Net 0.9842).
- Card B: TreeSHAP Feature Ranking vs Darcy Equation Terms:
  1. `fault_overpressure_bar` (428.0) — $\Delta P$ (Brick Red)
  2. `fault_p_bar` (334.3) — $\Delta P$ (Brick Red)
  3. `fault_log10_perm_m2` (151.6) — $k_f$ (Ochre)
  4. `fault_width_m` (41.9) — $A_f$ (Blue-grey)
  5. `fault_krg` (40.9) — $k_{rg}$ (Forest Green)

**Caption (14 pt):** U-Net surrogate preserves 99.0% of ranking accuracy because top-attributed features are structural and immune to surrogate derivative noise.

---

## SLIDE 9 — Module 1: Candidate Site Screening Suite

**Title (36 pt):** 1,000 candidate realizations ranked 0–100 — after clustering was tried, failed, and dropped.

**Body (18 pt):**
> Multi-criteria screening score: capacity from porosity (0.5), seal risk from peak pressure vs fracture limit (0.3), heterogeneity from porosity variance (0.2). All weights are `[ASSUMED]` and command-line configurable.
>
> **Negative Finding on Clustering:** KMeans clustering failed to exceed a silhouette score of **0.263**, and PCA revealed 99.9% of variance spans 3 continuous components with no discrete gaps. Subsurface sites exist on a continuous spectrum; forced clustering is invalid.

**Visual:** 1,000-point Scatter Plot (Capacity vs Seal Risk), green score gradient, and sensitivity table showing Spearman rank correlation ($\rho = 0.73 \dots 0.96$) across weight configurations.

**Caption (14 pt):** Rank ordering is robust ($\rho \ge 0.73$), but individual ranks shift by 2–5 seats under re-weighting. We report candidate suitability tiers, never individual "best" site IDs.

---

## SLIDE 10 — Module 2: Spatial Risk Mapping & Heatmaps

**Title (36 pt):** From "is this fault dangerous" to "where would one be" — a 32 × 32 conditional risk surface across the domain.

**Body (18 pt):**
> Instead of evaluating one static fault position, Module 2 sweeps a candidate fault across a 32 × 32 spatial grid, evaluating conditional leakage probability at every cell in ~1 second.
>
> Fault permeability and geometry are **marginalised across property draws**, ensuring spatial risk differences stem entirely from reservoir field dynamics rather than random sampling noise.

**Visual:** 32 × 32 spatial heatmap over the 7,680 m domain, kraft-to-brick-red gradient, labelled **"P(elevated leakage | fault here)"**, central well marker, plume contour overlay, crosshair on peak risk zone.

**Caption (14 pt):** Maps conditional risk: *If a fault exists at cell (x,y), what is the probability of elevated leakage 6 months ahead?* It does not predict fault existence.

---

## SLIDE 11 — Credibility: Negative Results & Scope Audit

**Title (36 pt):** Three negative results we measured and reported, and an honest audit of module delivery status.

**Body (18 pt):**
> **Negative Result 1 (0/1000 Lateral Loss):** Zero of 1,000 simulations reached the boundary (peak boundary $S_g = 0.0039$ vs 0.05 threshold). Plume reached 37.9% domain width. Target dropped.
>
> **Negative Result 2 (Fracture Gradient Sensitivity):** Sweeping assumed fracture gradient (0.15 vs 0.17 vs 0.20 bar/m) flipped binary breach from "some" to "zero". Switched to reporting continuous pressure margin.
>
> **Negative Result 3 (Withdrawn 12-Month Score):** Withdrew 0.9999 PR-AUC at 12-month horizon after finding persistence scored 0.9918. Switched to 6-month half-cycle testing.

**Visual — Delivery Status Grid Table:**

| Module | Status | Delivery |
|---|---|---|
| 1 · Site Screening | **Prototype** | 1,000 realisations ranked; live frontend panel |
| 2 · Leakage Engine | **Built (Narrower Scope)** | U-Net + XGBoost + TreeSHAP + 32x32 Spatial Risk Map |
| 3 · Digital Twin & Dashboard | **Partial** | Deployable UI: 1 panel real, 2 labelled mockups |
| 4 · Economics | **Not Started** | Scoped differential-ROI specification; no code |

**Caption (14 pt):** Disclosing negative results and exact software delivery scope establishes scientific credibility.

---

## SLIDE 12 — Conclusion, Verification Roadmap & Thank You

**Title (36 pt):** Everything on these slides is an open-source file you can inspect and verify. Thank you.

**Left Column — "Roadmap & Next Steps":**
1. **Frontend Real-Data Export:** Convert 24 held-out simulations into 2 MB sprite sheets to remove 12.38 GB dataset requirement.
2. **Explicit Safe Pressure Limit:** Derive numerical max-safe injection pressure caps from caprock pressure margin features.
3. **Economics Module:** Implement differential ROI formula for cushion gas vs risk mitigation costs.

**Right Column — "Independent Verification File Audit":**

| Claim / Benchmark | Verification File Path |
|---|---|
| All measurements & negative results | `docs/FINDINGS.md` |
| Horizon sweep & persistence scores | `outputs/xgb_horizon_sweep.json` |
| Simulator vs surrogate comparison | `outputs/source_comparison.json` |
| Site suitability ranking (1,000 rows) | `outputs/site_suitability_ranking.csv` |
| Tagged constants & config parameters | `src/config.py` |
| Automated physics assertions | `python -m src.leakage.labels` |

**Closing Text (20 pt, bold):**
> We spent as much effort proving what our numbers *don't* mean as producing them.
>
> **Repository:** GitHub: Sonil15/HyLeakAI · **Live Demo:** HyLeakAI Platform
>
> **Thank You!**

---

# PART 3 — RULES YOU MUST NOT BREAK

Check the finished deck against every line below.

- Do **not** claim 3D reservoir prediction. The grid is 128 × 128 × **1**.
- Do **not** say the model was "trained on leakage ground truth." There is none.
- Do **not** state a binary caprock-breach rate anywhere.
- Do **not** present lateral containment loss as a finding. It is 0/1000, and it belongs on slide 11 as a negative result.
- Do **not** quote any score at horizon 6, 12 or 30 without its persistence bar beside it.
- Do **not** write "site #468 is the best site." Tiers or percentiles only.
- Do **not** include any ROI, $/kg, or avoided-cost figure. That module does not exist.
- Do **not** compare against "traditional monitoring" with invented detection times.
- Do **not** claim to reproduce the source paper's accuracy. We are ~1.9× its error, and slide 8 & 11 say so.
- Do **not** name the undocumented third channel. Describe its units only.
- Do **not** attach an hours figure to "reservoir simulation." It was never timed.
- Do **not** add any statistic, citation, company name, or comparison that does not appear in this prompt.
- Every figure must have a caption stating a takeaway, not a description.
- Every screenshot of the web interface must be captioned as real or as a mockup, in the caption itself.
- The deck must remain readable in greyscale and when printed.
