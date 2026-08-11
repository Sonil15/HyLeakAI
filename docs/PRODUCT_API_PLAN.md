# HyLeakAI: usable-product and API plan

## Product position

HyLeakAI is a **physics-guided screening tool** for underground hydrogen storage. It is not a calibrated real-world leak-rate predictor. The source data contains reservoir fields but no observed faults, caprock measurements, or leakage labels; every public result must therefore show its assumptions and provenance.

## The two experiences we will keep

The project will always provide both of these experiences:

1. **Demo / Preview mode** — the current interactive mockup remains publicly available as a guided tour. It uses clearly labelled procedural and sample data, needs no API, and lets visitors understand the intended workflow even when the demo API is asleep or unavailable.
2. **Live assessment mode** — the same visual language, but results come from the deployed U-Net and XGBoost models. Every response states model version, field source, fault assumptions, and the screening-only limitation.

Demo mode must never be removed or silently presented as live inference. The UI will place a visible `Demo data` or `Live model` badge in every results panel.

## Architecture for the first public demo

```
GitHub Pages (static UI) ──HTTPS──> FastAPI service (Render)
      │                                      │
      ├─ Demo / Preview mode                 ├─ U-Net surrogate
      └─ Live assessment mode                ├─ XGBoost risk classifier
                                             └─ constants + model metadata
```

The API is deliberately stateless. It must not include the 5.9 GB simulator state array or 12.4 GB LMDB file. For surrogate assessment it needs only the U-Net checkpoint, XGBoost model, normalisation metadata, and static geological constants.

## Delivery phases

### Phase 1 — API foundation (this branch)

- Add FastAPI, CORS, health, and interactive OpenAPI documentation.
- Add `GET /v1/simulations` for held-out realisations.
- Add `POST /v1/assessments` for a realisation/timestep plus a supplied fault or seeded ensemble.
- Return pressure/plume summaries, risk, model metadata, provenance, and limitations.
- Add a Render blueprint, deployment requirements, and smoke tests.

### Phase 2 — connect the Pages UI

- Preserve the current page as `Demo / Preview`.
- Add a `Live assessment` route/view with scenario controls.
- Call the API, show a cold-start state, and recover gracefully to preview mode when the API is unavailable.
- Reuse the current atlas/reservoir/fault interaction patterns rather than rebuilding the interface.

### Phase 3 — decision workflow

- Compare two scenarios (fault hypotheses or operating timesteps).
- Show median, P10, P90, and worst-case risk—not only one number.
- Add sensitivity sweeps for fault permeability, length, width, and caprock fracture-gradient assumptions.
- Return a plain-language screening conclusion without presenting it as an approval/rejection decision.

### Phase 4 — reproducibility and trust

- Export JSON/CSV, then PDF, with inputs, assumptions, model/artifact version, timestamps, and limitations.
- Add API versioning, request IDs, logs, rate limits, monitoring, contract tests, and browser end-to-end tests.
- Before professional decision-support claims, validate against independent site-specific data and publish the protocol.

## One-week hosting choice

Use a **Render Free Web Service** for the temporary FastAPI demo and GitHub Pages for the frontend. Render supports Python and HTTPS. Its free tier has 512 MB RAM / 0.1 CPU, spins down after 15 idle minutes, and may take about a minute to wake; it is suitable for a preview, not production. The UI must explain the warm-up delay and offer Preview mode immediately.

Deployment is only authorised after local endpoint tests pass and the small inference artifact bundle is prepared. No artifact should be copied to a public service until its licensing and size are reviewed.

The first bundle is published as the `hyleak-api-artifacts-v0.1.0` GitHub prerelease asset. Render downloads and SHA-256-verifies it during the build; the raw simulator state and LMDB files remain excluded. When the repository is private, configure a read-only `HYLEAK_GITHUB_TOKEN` secret in Render so its build can access the release asset.

## Definition of usable

The public demo is usable when a visitor can choose a held-out simulation and timestep, define or sample fault hypotheses, see a labelled live risk distribution with assumptions, compare scenarios, and export a reproducible result. Preview mode must remain usable independently of the API.
