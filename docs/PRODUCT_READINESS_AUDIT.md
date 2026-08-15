# HyLeakAI product-readiness audit

**Scope:** Repository pipeline, API contract, local Streamlit research dashboard, and deployed single-origin web application.
**Deployment note:** Single-origin deployment runs on Google Cloud Run serving both FastAPI routes and the static frontend from [index.html](file:///Users/sonil/Desktop/HyLeakAI/app/web/index.html).

## Executive finding

HyLeakAI provides a functional **screening pipeline**:

```text
Porosity + permeability + timestep
        -> U-Net surrogate
        -> 128 x 128 pressure and H2-saturation fields
        -> physics feature extraction + user/sampled fault hypothesis
        -> XGBoost classifier
        -> probability distribution of elevated leakage at a 6-month horizon
```

The public API in [main.py](file:///Users/sonil/Desktop/HyLeakAI/api/main.py) delivers surrogate field arrays via `GET /v1/fields/{simulation_id}`, metadata via `GET /v1/metadata`, risk scores via `POST /v1/assessments`, and volumetric screening via `POST /v1/site-screen`. The public frontend at [index.html](file:///Users/sonil/Desktop/HyLeakAI/app/web/index.html) presents both candidate site ranking, live surrogate model scoring, and the Geologist Site Input Screen (Geologist Workbench).

## Available system capabilities

| Product element | Evidence / source | Product status |
| --- | --- | --- |
| Geological suitability ranking | `outputs/site_suitability_ranking.csv`, produced by [site_suitability.py](file:///Users/sonil/Desktop/HyLeakAI/src/site_suitability.py) for 1,000 geological realisations | Ranks synthetic realisations; does not represent physical geographic locations. |
| Surrogate field prediction | [service.py](file:///Users/sonil/Desktop/HyLeakAI/api/service.py) generates 128×128 pressure and H2 saturation fields for held-out simulations | Exposed via `GET /v1/fields/{simulation_id}`. |
| Field summaries | `field_summary`: peak pressure, pressure delta, plume area, caprock margin | Live API output; populates UI metric cards and summary tables. |
| Fault-ensemble screening | `POST /v1/assessments` samples or accepts custom faults and returns leakage probabilities | Live API output; displays individual fault hypotheses and risk distributions. |
| 6-month risk horizon | `outputs/xgb_results.json`, report horizon = 3 timesteps (6 months) | Defensible horizon with maximum predictive gain over persistence. |
| Model quality evidence | `outputs/source_comparison.json`: surrogate PR-AUC 0.9842 vs simulator 0.9941 on 150 held-out simulations | Contextual validation data with screening-only limitations. |
| Volumetric site screening | `POST /v1/site-screen` calculates capacity, pressure ceiling, and overpressure flags | Live API output; supports the Geologist Site Input Screen. |

## Inputs through the pipeline

### Realisation inputs

The deployed inference service accepts an allowed held-out simulation ID and its static geological arrays:

| Input | Shape / range | Meaning |
| --- | --- | --- |
| `simulation_id` | 150 held-out IDs | A synthetic geological realisation, not a physical site map. |
| Porosity | 128×128 | Dataset property stored in `constants.npy`. |
| Permeability | 128×128 | Dataset property stored in `constants.npy`. |
| `timestep` | 1–60 (two months per step) | Operating point in a ten-year injection/withdrawal cycle. |

### Scenario inputs

The public API accepts:

| Input | API support | Product recommendation |
| --- | --- | --- |
| Fault ensemble size | `fault_count` (1–50) | Maintain default of 20 and explain its relationship to sampling variance. |
| Random seed | `seed` | Display seed in UI and exports to guarantee reproducibility. |
| Custom faults | `mode="custom_faults"` with geometry and permeability fields | Provide interactive fault creation controls on the frontend map. |
| Fault permeability | Supported in custom fault request | Expose log-scale slider for the assumed range (1e-15 to 1e-12 m²). |
| Fault dimensions | Supported in custom fault request | Present length and width as explicitly defined hypotheses. |

### Explicit assumptions

Because the underlying dataset contains no observed faults or caprock measurements, leakage labels rely on a semi-analytical Darcy-flux calculation. The user interface must keep these parameters visible:

- Caprock thickness: 50 m
- H2 viscosity: 9.5e-6 Pa·s
- Assumed fracture gradient: 0.17 bar/m (range: 0.15–0.20 bar/m)
- Fault permeability: sampled log-uniformly from 1e-15 to 1e-12 m²
- Fault length: 200–2,000 m; width: 1–10 m
- Operational conclusion: physics-guided screening signal, not a calibrated leak-rate prediction or regulatory permit approval

## API endpoints on Cloud Run

Cloud Run hosts the stateless FastAPI inference service. [Dockerfile](file:///Users/sonil/Desktop/HyLeakAI/Dockerfile) includes the compact model artifacts while excluding raw simulation arrays.

| Endpoint | Purpose | Status |
| --- | --- | --- |
| `GET /` | Serves static web frontend | Implemented |
| `GET /health` | Service health status | Implemented |
| `GET /v1/simulations` | Returns held-out test simulation IDs | Implemented |
| `GET /v1/metadata` | Exposes model specifications, grid definitions, and limitations | Implemented |
| `GET /v1/fields/{simulation_id}` | Delivers U-Net predicted pressure, saturation, and static geology grids | Implemented |
| `POST /v1/assessments` | Runs U-Net surrogate and XGBoost risk classifier for fault hypotheses | Implemented |
| `POST /v1/site-screen` | Computes scalar volumetric capacity and pressure feasibility metrics | Implemented |


- every displayed cell comes from a documented API field/risk-map response;
- the selected simulation, timestep, model/artifact version, units, and map scale are visible;
- fault markers match returned or user-entered fault coordinates;
- the run shows reproducible inputs, seed, timestamp, and assumptions;
- error, cold-start, and API-unavailable states are honest and usable;
- exported output reproduces the displayed summary;
- the product continues to state that outputs are conditional screening results based on assumed fault properties.

## Recommended demo narrative for judges

1. Select a synthetic geological realisation from the suitability ranking.
2. Inspect its actual U-Net pressure and H2-saturation fields at a selected operating timestep.
3. Sample fault uncertainty or define a specific fault hypothesis.
4. Show the 6-month conditional risk distribution and its assumptions.
5. Change one operational or fault assumption and compare scenarios.
6. Export a traceable screening result.

That is a coherent, useful product demonstration. It is stronger than a visually impressive but synthetic map because every interaction answers a real question and can be traced back to the deployed pipeline.
