# Talking points: Impact, Economics, Business, and Roadmap

Companion document to [PRESENTATION_SCRIPT_FINALS.md](file:///Users/sonil/Desktop/HyLeakAI/docs/PRESENTATION_SCRIPT_FINALS.md). This file details technical arguments for Q&A sessions and panel discussions.

Two core guidelines apply: keep sentences short, and explain the physical significance of every quoted number. Every metric links to its source file for validation.

---

## 1. Impact

- **Storage relies on geological media:** Hydrogen offers seasonal renewable energy balancing. Terawatt-hour storage capacity requires porous rock formations, specifically depleted natural gas reservoirs with proven seal integrity.
- **Computation limits evaluation speed:** Multi-hour reservoir simulations limit traditional workflows to testing one or two fault hypotheses per site.
- **Fault geometry creates vertical pathways:** Crushed fault cores block lateral fluid movement, while surrounding fracture zones transmit gas upward through caprock seals.
- **Surrogate modeling expands coverage:** Decoupling fault parameters from state field predictions enables evaluating 20,000 fault hypotheses per site in milliseconds.
- **Scalable portfolio screening:** The system ranks 1,000 geological realisations (`outputs/site_suitability_ranking.csv`) with an inference cost of **0.65 vCPU-seconds** per pass.
- **Audit-ready risk documentation:** The pipeline generates auditable, provenance-tagged containment-risk statements for permitting and insurance evaluation.
- **Honest reporting of ranking limits:** The system presents suitability tiers rather than absolute single-site declarations because ranking order shifts by 2 to 5 positions under varied criteria weighting (see [SITE_SUITABILITY.md](file:///Users/sonil/Desktop/HyLeakAI/docs/SITE_SUITABILITY.md)). UI chips tag all metrics as `[DATASET]`, `[DERIVED]`, or `[ASSUMED]`.

---

## 2. Economics and Business Model

- **Value of Information replaces ROI:** Calculating ROI requires empirical hydrogen leakage data that does not exist in public datasets. Calculating Value of Information (VOI) via [voi.py](file:///Users/sonil/Desktop/HyLeakAI/src/economics/voi.py) measures how information improves operational decisions under uncertainty without requiring uncalibrated leakage prices.
- **Coverage drives value:** Evaluating 20,000 fault hypotheses provides near-optimal decision coverage compared to evaluating a small sample of exact simulations.
- **Efficiency ratios:** Screened surrogate evaluations capture 99.74 percent of available decision value compared to perfect information.
- **Surrogate accuracy preservation:** Swapping full simulator fields for U-Net predictions costs only 0.000178 of decision efficiency (AUC 0.99987 vs 0.99963) across 150 held-out test simulations.
- **Structural gross margin:** Decoupled execution produces flat marginal compute costs across variable fault hypothesis counts (6.52 s wall clock on 0.1 vCPU).
- **Commercial sequence:** Land through co-screening pilot studies, expand via annual subscriptions, and defend through methodology standardization.

---

## 3. Future Roadmap

- **Fluid expansion sequence:** Focus on hydrogen first, natural gas next, and CO2 later.
- **Physical fluid properties:** Fluid property calculations via [fluids.py](file:///Users/sonil/Desktop/HyLeakAI/src/economics/fluids.py) confirm CH4 buoyancy contrast sits at 0.88x H2, enabling model transfer via single-parameter recalibration. CO2 buoyancy sits at 0.21x H2, requiring architectural modification for monotonic injection.
- **Consortium partnership ask:** Request one real depleted-field dataset for label calibration and one pilot co-screening study alongside an active site evaluation.

---

## Metric reference map

| Claim | File |
|---|---|
| Efficiency, sweeps, harmful boundary | `outputs/voi_results.json` |
| Fluid properties, transfer table | `outputs/fluid_properties.json` |
| Unit cost, marginal-cost regression | `outputs/unit_cost.json` |
| Input provenance tags | `outputs/assumption_register.json` |
| Surrogate vs simulator degradation | `outputs/source_comparison.json` |
| Site ranking and robustness | `outputs/site_suitability_ranking.csv`, [SITE_SUITABILITY.md](file:///Users/sonil/Desktop/HyLeakAI/docs/SITE_SUITABILITY.md) |
| Comprehensive business case | [Economics_and_impact.md](file:///Users/sonil/Desktop/HyLeakAI/Economics_and_impact.md), [COMMERCIAL.md](file:///Users/sonil/Desktop/HyLeakAI/docs/COMMERCIAL.md) |

