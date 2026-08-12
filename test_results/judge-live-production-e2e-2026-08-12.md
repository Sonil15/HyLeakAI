# Judge Live model production test

**Target:** `https://sonil15.github.io/HyLeakAI/`

**Result:** PASS

After PR #6 merged and GitHub Pages deployed, a real headless Chrome session:

1. Opened the public site and switched to **Live model**.
2. Loaded the Render API's 150 held-out simulation IDs.
3. Submitted a three-fault live assessment for simulation 0 at timestep 31.
4. Received the completed status message from the page.
5. Confirmed the UI labelled the result `Live API · U-Net surrogate + XGBoost`.
6. Confirmed all three returned faults rendered in the results waterfall.

Captured status:

```text
Live assessment complete for simulation #0, timestep 31.
Results are screening outputs, not calibrated predictions.
```

The live tab also displays a clearly labelled verified cached API result immediately before a refresh run, plus the visible preparation, field-inference, and fault-scoring stages.

## Selenium note

`test_results/selenium-production-e2e.py` contains the requested Selenium test. It was not executable in this workspace because the Selenium package download timed out twice; Chrome CDP automation was used for the successful production run above.

