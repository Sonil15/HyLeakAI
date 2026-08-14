# HyLeakAI frontend/API smoke test

**Run date:** 2026-08-12 (Asia/Kolkata)

**Frontend branch tested:** `feat/live-frontend` at `c2325bd`

**API:** `https://hyleak-api-demo.onrender.com`

## Results

| Check | Result | Evidence |
| --- | --- | --- |
| API health | PASS | `GET /health` returned HTTP 200 and `status: ready`. |
| Held-out simulations | PASS | `GET /v1/simulations` returned HTTP 200 with 150 simulation IDs. |
| GitHub Pages CORS | PASS | `OPTIONS /v1/assessments` from `https://sonil15.github.io` returned HTTP 200; allowed methods include `GET, POST`. |
| Live assessment | PASS | `POST /v1/assessments` for simulation `0`, timestep `30`, 3 fault samples, seed `20260809` returned HTTP 200. |
| Live response contract | PASS | The assessment returned `field_summary`, 3 `faults`, and `risk_summary`. Peak pressure was `204.3978729248047` bar; worst-case probability was `2.2875658487464534e-06`. |
| Frontend inline JavaScript | PASS | The final inline script in `app/web/index.html` compiles with Node's `new Function`. |
| Frontend/API wiring | PASS | Source contains the Render base URL; `/health`, `/v1/simulations`, and `/v1/assessments`; Preview/Live switch; live controls; and illustrative-field provenance label. |

## Scope note

The GitHub Pages production URL has not been retested with the new controls because PR #5 has not yet been merged into `main`. This run verifies the feature branch's source contract and the deployed API it calls. Merge PR #5, wait for the Pages workflow to complete, then repeat the browser interaction test against the public Pages URL.

