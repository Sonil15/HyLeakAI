# HyLeakAI — Presentation Script (4-Minute Target)

> **Note:** This script is optimized for a fast, punchy 4-minute presentation (~456 spoken words at 125–130 wpm). It removes conversational filler while preserving all core physics claims, benchmark metrics, economic VOI results, and strategic roadmap targets intact.

---

### Section 1: The Problem & The Mission

To store terawatt-hours of seasonal hydrogen energy, depleted gas fields are the only containers big enough.

Underground pressure can crack caprock seals, and unmapped faults create leakage pathways. Today, running a full reservoir simulation takes hours per scenario, so operators only test one or two fault guesses and move on.

Under the National Green Hydrogen Mission, India targets 5 million metric tons of annual hydrogen by 2030. All of that requires secure geological storage. We screen these depleted fields before injection begins.

---

### Section 2: Module 1 — Site Suitability Screening

We built two modules. Module 1 screens candidate rock suitability across 1,000 geological grids.

From each grid, we extract mean porosity, peak injection pressure, and porosity variation to evaluate Capacity, Seal Fracture Risk, and Heterogeneity.

We combine these criteria using Analytic Hierarchy Process (AHP) weights. Because rankings remain highly consistent across weighting sensitivities (Spearman rank correlation 0.73 to 0.96), we report robust candidate tiers rather than claiming a single winning site.

---

### Section 3: Module 2 — Leakage Risk (U-Net + XGBoost)

Module 2 evaluates leakage probability and volume across two decoupled steps.

Step one runs a U-Net neural network once per site. It inputs porosity and permeability maps, well distance, and injection cycle stage. Crucially, fault geometry is excluded from the U-Net input. In under one second, it predicts 10-year pressure and saturation fields.

Step two uses Darcy's law and XGBoost. We introduce hypothetical fault properties and predict 6-month leakage risk in milliseconds.

Because the fault is excluded from the U-Net input, evaluating 20,000 fault hypotheses takes seconds. When compared against full tNavigator simulator runs, our model matches performance (PR-AUC 0.984 vs 0.994) at a 10,000x speedup.

---

### Section 4: Economic Impact & Value of Information (VOI)

We quantify financial impact using Value of Information. Value of Information is not about "what does it save." It is about **what does it change** in your decision.

In critical operations, mitigation is cheap, but failure is catastrophic. When you calculate the ratio of mitigation cost divided by failure cost, you land in the hardest corner of risk management, where downside risk is highest.

Because traditional reservoir simulations take hours, running just two simulator runs yields **roughly 0% decision efficiency**.

HyLeakAI screens 20,000 fault hypotheses in seconds for 0.65 vCPU-seconds per pass. Right in that hardest corner, we elevate decision efficiency to **21.5%**, recovering true decision value and providing an exportable, auditable risk statement.

---

### Section 5: Improvements & What's Next

Since Round 1, we made four key upgrades:
1. We shifted to a 6-month prediction horizon to eliminate annual cycle-copying bias (holding 99% AUC versus a 2% baseline).
2. We split our surrogate into dual U-Nets for smooth pressure and sharp plume fronts.
3. We added caprock mineral chemical decay over time.
4. On our roadmap, as the Ministry of Petroleum and Natural Gas builds strategic natural gas reserves in indicated reservoirs (targeting 15% gas by 2030), our model easily extends to CH4 (methane buoyancy sits within 12% of hydrogen), requiring just one retraining run.

We do not need capital. We need one real depleted-field dataset and one pilot co-screening study alongside an active operator decision.

Thank you!
