# Production browser end-to-end smoke test

**Run date:** 2026-08-12 (Asia/Kolkata)

**Target:** `https://sonil15.github.io/HyLeakAI/`

## Result: PASS

The test drove a real headless Chrome session against the public GitHub Pages deployment.

1. Loaded the production URL and found the Preview/Live switch.
2. Switched to **Live model**.
3. Waited for the deployed Render API to load the simulation list.
4. Confirmed the UI reported **150 held-out simulations**.
5. Set the fault count to 3 and ran a live assessment.
6. Confirmed the page displayed: `Live assessment complete for simulation #0, timestep 31`.
7. Confirmed the live provenance label: `Live API · U-Net surrogate + XGBoost`.
8. Confirmed the results contained 3 rendered fault rows and live risk readouts.

## Captured UI state

```json
{
  "status": "Live assessment complete for simulation #0, timestep 31. Results are screening outputs, not calibrated predictions.",
  "mode": "Live model assessment",
  "badge": "API ready · 150 held-out simulations",
  "simulationDisabled": false,
  "runDisabled": false,
  "riskBadge": "Live API · U-Net surrogate + XGBoost",
  "faultRows": 3
}
```

The executable test is saved alongside this report as `production-e2e-smoke.js`.

