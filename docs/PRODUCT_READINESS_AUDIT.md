# HyLeakAI product-readiness audit

**Date:** 2026-08-14  
**Scope:** repository pipeline, API contract, local Streamlit research dashboard, and deployed GitHub Pages frontend.  
**Deployment note:** this review does not change Render or Cloud Run configuration.

## Executive finding

HyLeakAI already has a credible **screening pipeline**:

```text
Porosity + permeability + timestep
        -> U-Net surrogate
        -> 128 x 128 pressure and H2-saturation fields
        -> physics feature extraction + user/sampled fault hypothesis
        -> XGBoost
        -> probability distribution of elevated leakage at a 6-month horizon
```

The local research dashboard can display real fields and calculate a conditional spatial risk map. The public API successfully runs the U-Net and XGBoost, but currently returns only **aggregated field summaries** and a list of sampled-fault scores. The public frontend therefore cannot render a true pressure, saturation, or risk map from its live response. Its 2.5D reservoir graphic remains an illustrative view and should not be positioned as live spatial model output.

The path to a useful product is not another design pass. It is to expose the real pipeline outputs in small, explicit API resources and render those resources with conventional scientific maps, scenario controls, provenance, and export.

## What is real today

| Product element | Evidence / source | Product status |
| --- | --- | --- |
| Geological suitability ranking | `outputs/site_suitability_ranking.csv`, produced by `src/site_suitability.py` for 1,000 geological realisations | Can be shown as a real ranking of synthetic realisations; not real geographic sites. |
| Surrogate field prediction | `api/service.py:predict_fields()` returns 128×128 pressure and H2 saturation predictions for an allowed held-out simulation and timestep | Real model output exists, but is not exposed by the public API. |
| Field summaries | `field_summary`: peak pressure, pressure delta, plume area, caprock margin | Live API output; suitable for metric cards and tables. |
| Fault-ensemble screening | `POST /v1/assessments` samples or accepts faults and returns one probability per fault | Live API output; useful when each sampled assumption is visible. |
| 6-month risk horizon | `outputs/xgb_results.json`, report horizon = 3 timesteps = 6 months | Defensible headline horizon: it has the largest gain over persistence. |
| Model quality evidence | `outputs/source_comparison.json`: surrogate PR-AUC 0.9842 vs simulator 0.9941 on 150 held-out simulations | Useful validation context, with the screening-only limitation. |
| Conditional spatial risk | `src/leakage/risk_map.py`, used by `app/dashboard.py` | Real calculation exists locally but is not exposed by the API. |

## Inputs through the current pipeline

### Immutable model inputs

The deployed inference service uses an allowed **held-out simulation ID** and its static geological arrays:

| Input | Shape / range | Meaning |
| --- | --- | --- |
| `simulation_id` | one of 150 held-out IDs | A synthetic geological realisation, not a physical site or map location. |
| Porosity | 128×128 | Dataset property, stored in `constants.npy`. |
| Permeability | 128×128 | Dataset property, stored in `constants.npy`. |
| `timestep` | 1–60, two months per step | Operating point in a ten-year injection/withdrawal cycle. |

### Scenario inputs

The current API accepts:

| Input | Current API support | Product recommendation |
| --- | --- | --- |
| Fault ensemble size | `fault_count`, 1–50 | Keep; default to 20 and expose why it affects uncertainty. |
| Random seed | `seed` | Keep; display it in the result and exports for reproducibility. |
| Custom faults | `mode="custom_faults"` plus `x_m`, `y_m`, `length_m`, `width_m`, `permeability_m2`, `orientation_rad` | Add a map click / editable table; this is more useful than a decorative fault swarm. |
| Fault permeability | Supported in custom fault request | Expose a log-scale slider and show its assumed range (1e-15–1e-12 m²). |
| Fault length and width | Supported in custom fault request | Expose as clearly labelled hypotheses, not inferred properties. |

### Assumptions that must stay visible

The dataset has no observed faults, caprock measurements, or leakage labels. Leakage labels are produced by a semi-analytical Darcy-flux rule. A usable interface should pin these assumptions beside every risk result:

- caprock thickness: 50 m;
- H2 viscosity: 9.5e-6 Pa·s;
- assumed fracture gradient: 0.17 bar/m (sweep range 0.15–0.20);
- fault permeability: sampled log-uniformly from 1e-15 to 1e-12 m²;
- fault length: 200–2,000 m; width: 1–10 m;
- conclusion: physics-guided screening, **not** a calibrated leak-rate prediction or injection approval.

## Outputs available vs. outputs currently delivered

| Pipeline output | Exists in code | Current API response | Needed product treatment |
| --- | --- | --- | --- |
| Pressure field | Yes: 128×128 array | No | Scientific heatmap with fixed units/domain and colourbar. |
| H2 saturation field | Yes: 128×128 array | No | Scientific heatmap with fixed 0–1 scale and plume contour. |
| Permeability field | Yes: 128×128 static array | No | Toggleable context layer; it does not change with timestep. |
| Caprock margin | Yes | Summary only | Metric, threshold explanation, and sensitivity to fracture gradient. |
| Sampled-fault probabilities | Yes | Yes | Sortable table + histogram/ECDF + map markers. |
| Worst, median, P90 risk | Yes | Yes | Decision summary, not a single headline probability. |
| Custom-fault result | Yes | Yes | Inspectable single-scenario card and compare-to-baseline. |
| Conditional risk map | Yes: `src/leakage/risk_map.py` | No | On-demand map endpoint with explicit resolution and draw count. |
| SHAP / feature attribution | Artifacts exist; local dashboard can use model feature names | No | Top contributors for a selected fault; label as model attribution, not causation. |
| Suitability ranking | Yes | Frontend has embedded/static representation | A filterable candidate-realisations table, separate from leakage risk. |
| Reproducibility metadata | Partly available | Incomplete | Request ID, model/artifact version, seed, inputs, timestamp, assumptions, export. |

## Why the current public frontend is not yet a product screen

1. **The live request does work, but it is summary-only.** The cards and fault rows can be real, while the spatial slab cannot be. Scaling a procedural graphic from a plume-area number does not make it a field prediction.
2. **The active live workflow exposes only a sampled ensemble.** The API supports custom faults, but a user cannot construct one in the public UI. This hides the most decision-relevant interaction.
3. **No scenario comparison exists.** A user cannot answer: “what changed when permeability, operating step, or fault location changed?”
4. **No reproducible output can be saved.** There is no report/JSON/CSV export containing the request, artifact/model identity, assumptions, and outcome.
5. **No operational guardrails exist in the UI.** The API result does not include a plain-language interpretation or a clear “do not use for approval” boundary at the decision point.
6. **The current cached response helps a demonstration but is not a product feature.** It should be clearly described as a cached, dated API result and never substitute for a fresh run.

## Recommended product interface

### 1. Start screen: candidate context

Replace the broad design-story content with a compact scenario workspace:

- Select a held-out geological realisation; show its suitability percentile and the three component scores.
- State “synthetic geological realisation” directly under the selector.
- Show the 10-year operating timeline and selected timestep.
- Display static rock context: porosity and log-permeability maps.

### 2. Field view: real model fields

Replace the procedural 2.5D slab with three synchronized 2D panels:

1. H2 saturation (0–1);
2. pressure (bar);
3. conditional leakage risk, only after a risk-map request.

Each panel needs units, fixed/reported colour domain, a colourbar, timestep, simulation ID, `U-Net surrogate` source tag, and a loading/error state. Use the same grid extent (0–7.68 km) as the local Streamlit dashboard.

Do not synthesize cell values on the client. If a field response is unavailable, show an empty-state panel explaining that the API is warming or the field resource was not requested.

### 3. Fault scenario builder

Provide two explicit paths:

- **Explore uncertainty:** sample 20 faults with a seed; return median, P90, worst case, a distribution plot, and the assumptions used.
- **Assess a hypothesis:** click a map or fill a table to define one or more custom faults. Show the input values next to each probability.

Map markers must come from the returned fault coordinates. A fault should never be drawn just for visual texture.

### 4. Decision summary and comparison

For every run show:

- worst-case, P90, and median P(elevated leakage in 6 months);
- peak pressure, pressure delta, plume area, caprock margin;
- assumptions and model limitations;
- a small “compare scenarios” list that holds two to five runs and shows deltas.

Use neutral language such as **“screening signal”**, **“requires engineering review”**, or **“low within sampled hypotheses”**. Do not display “safe”, “approved”, or a leakage-rate claim.

### 5. Export and evidence

Add `Export result` after each completed run. It should generate JSON first, then CSV/PDF later. The JSON must include:

```json
{
  "request_id": "...",
  "created_at": "ISO-8601",
  "model_version": "...",
  "artifact_version": "...",
  "simulation_id": 0,
  "timestep": 31,
  "fault_inputs": [],
  "risk_summary": {},
  "field_summary": {},
  "assumptions": {},
  "limitations": []
}
```

## API work needed for Cloud Run

Cloud Run is a good fit for stateless inference. Keep the full 12.38 GB LMDB and 5.9 GB state array out of the container; the current small artifact approach is correct. Add the following contracts before redesigning the frontend around them.

| Endpoint | Purpose | Suggested response |
| --- | --- | --- |
| `GET /v1/metadata` | Tell the UI what is deployed | API/model/artifact versions, grid/domain, timestep units, allowed simulation IDs, assumptions, limitations. |
| `GET /v1/simulations/{id}` | Candidate context | suitability score/components, synthetic-reality label, static geology summaries. |
| `GET /v1/fields/{id}?timestep=31&layers=pressure,saturation` | Real surrogate grids | Compact arrays or quantized PNG tiles plus min/max/unit/source metadata. |
| `POST /v1/assessments` | Keep and extend | Current output plus `request_id`, `created_at`, model/artifact versions, input echo, assumption echo. |
| `POST /v1/risk-maps` | On-demand conditional spatial risk | Requested resolution, draw count, reducer, risk grid, extent, returned fault assumptions. |
| `GET /v1/assessments/{request_id}` | Optional asynchronous support | Useful if field/risk-map calculations become slow. |

For small responses, arrays can be JSON. For production-quality map loading, prefer quantized `uint8` PNG/WebP layers or compressed binary arrays with explicit scale/offset metadata. Never infer a colour scale from the browser-only visual.

## Delivery order

### Product minimum viable workflow

1. Add `GET /v1/metadata` and version every live response.
2. Add real `pressure` and `saturation` field delivery for one simulation/timestep.
3. Replace the public procedural slab with those two real field maps.
4. Add custom-fault controls that send `mode="custom_faults"`.
5. Show ensemble distribution + worst/P90/median + the exact inputs used.
6. Add a JSON export with request/response/assumption provenance.

### Next useful capability

7. Expose `POST /v1/risk-maps` at a conservative default (for example 24×24 cells and 8 property draws) with a progress state.
8. Add scenario comparison and an assumption sensitivity sweep for permeability and fracture gradient.
9. Add cached API responses only as an explicitly dated demo fallback, not as “live” output.

### Before any external decision-support claim

10. Add authentication/rate limiting, structured request logs, health/latency monitoring, and Cloud Run resource/concurrency limits.
11. Add contract tests, browser E2E tests, and a reproducible benchmark fixture.
12. Validate against independent, site-specific data before representing risk probabilities as field-calibrated.

## Acceptance criteria for replacing the current mockup

The frontend is ready to stop calling any map a mockup only when all of these are true:

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
