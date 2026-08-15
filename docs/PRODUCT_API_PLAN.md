# HyLeakAI: product architecture and API plan

## Product position

HyLeakAI operates as a physics-guided screening tool for underground hydrogen storage. It is not a calibrated real-world leak-rate predictor. The source dataset contains reservoir fields but no observed faults, caprock measurements, or leakage labels. Every public interface must display assumptions and data provenance clearly.

## Core experiences

The project maintains two distinct user experiences:

1. **Demo / Preview mode:** The interactive frontend at [index.html](file:///Users/sonil/Desktop/HyLeakAI/app/web/index.html) provides a self-contained static tour using labelled procedural data. Visitors explore the workflow even when the backend API is asleep or offline.
2. **Live assessment mode:** The same visual interface requests real model predictions from the deployed U-Net surrogate and XGBoost risk models in [main.py](file:///Users/sonil/Desktop/HyLeakAI/api/main.py). Every response identifies the model version, field source, fault assumptions, and screening limitations.

The frontend presents explicit status badges (`Preview values` or `Live API`) in every results panel.

## Architecture

```text
Static Web UI + FastAPI Service (Google Cloud Run single origin)
      │
      ├─ Preview / Demo mode (client-side procedural stand-ins)
      └─ Live assessment mode (FastAPI endpoints)
            ├─ U-Net surrogate (pressure and saturation fields)
            ├─ XGBoost risk classifier (6-month leakage probability)
            ├─ Volumetric site-screen calculator (scalar feasibility screen)
            └─ Geological constants and metadata
```

The API service remains stateless. It excludes the 5.9 GB simulator state array and 12.4 GB LMDB file. Inference requires only the U-Net checkpoint, XGBoost model, normalisation metadata, and static geological constants.

## Delivery phases

### Phase 1: API foundation (Completed)

Implemented in [main.py](file:///Users/sonil/Desktop/HyLeakAI/api/main.py) and [service.py](file:///Users/sonil/Desktop/HyLeakAI/api/service.py), deployed to Google Cloud Run at `https://hyleakai-152424867743.asia-south1.run.app`.

- FastAPI framework with CORS configuration and `GET /health`.
- `GET /v1/simulations` returning held-out test realization IDs.
- `GET /v1/metadata` displaying model parameters and grid definitions.
- `GET /v1/fields/{simulation_id}` providing U-Net predicted pressure and saturation grids.
- `POST /v1/assessments` executing the U-Net surrogate and XGBoost risk classifier for sampled or custom fault hypotheses.
- `POST /v1/site-screen` computing transparent volumetric site feasibility metrics and overpressure flags.
- Automated CI/CD pipeline in [deploy-cloud-run.yml](file:///Users/sonil/Desktop/HyLeakAI/.github/workflows/deploy-cloud-run.yml) using Workload Identity Federation.

### Phase 2: Frontend integration (Completed)

Implemented in [index.html](file:///Users/sonil/Desktop/HyLeakAI/app/web/index.html).

- Preserved client-side Preview mode.
- Integrated Live model scenario controls connected to the Cloud Run API.
- Integrated Geologist Site Input Screen (Geologist Workbench) for direct volumetric screening.
- Added visual loading states and automatic fallback to Preview mode if the API is unreachable.

### Phase 3: Decision workflow

- Compare two fault scenarios or operating timesteps side by side.
- Present median, P10, P90, and worst-case risk distributions instead of a single metric.
- Provide sensitivity sweeps for fault permeability, length, width, and fracture gradient.
- Output plain-language screening summaries with clear engineering caveats.

### Phase 4: Reproducibility and governance

- Export complete JSON and PDF run records containing inputs, assumptions, model versions, timestamps, and limitations.
- Implement API rate limiting, structured logs, and automated contract tests.
- Validate against site-specific field data prior to any operational decision-support claims.

## Deployment model

The public service runs on Google Cloud Run with 1 vCPU, 1 GiB RAM, startup CPU boost, and `min-instances=0`. Serving static assets and API routes from a single FastAPI application eliminates CORS configuration issues and cross-origin security constraints.

