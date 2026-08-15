# HyLeakAI: geologist-facing product direction

## What the product can claim today

HyLeakAI serves as a **screening tool**, not a calibrated site model. Its live service predicts pressure and saturation for held-out synthetic geological realisations using a U-Net surrogate, then scores explicitly supplied or sampled fault hypotheses with an XGBoost classifier. The 128 by 128 fields, model provenance, and fault probabilities represent real service outputs from [main.py](file:///Users/sonil/Desktop/HyLeakAI/api/main.py). They do not represent measured site data.

The public interface in [index.html](file:///Users/sonil/Desktop/HyLeakAI/app/web/index.html) provides two distinct workflows:

1. **Site-input screen (Geologist Workbench):** A transparent scalar volumetric calculation accepts a user's interpreted area, thickness, porosity, efficiency, CO2 density, depth, overpressure allowance, injection schedule, and caprock thickness. It returns effective capacity, planned mass, utilisation, and hydrostatic pressure ceilings via `POST /v1/site-screen`. A default saline-aquifer profile enables immediate evaluation without data uploads.
2. **Analogue risk screen:** The deployed surrogate allows exploring representative field behaviour and fault-pathway sensitivity. Labels clearly specify "synthetic realisation" and "screening only."

This separation remains essential: scalar inputs cannot map directly into the current U-Net surrogate trained on gridded synthetic realisations.

## Significance of geological inputs

Reservoir structure, thickness, porosity, permeability, and natural flow characteristics determine storage capacity and plume movement. Caprock continuity, entry pressure, fault networks, and geomechanical responses govern containment. NETL identifies pressure-front tracking, plume migration pathways, structural faults, and physical property shifts as primary monitoring concerns. See [NETL subsurface monitoring](https://netl.doe.gov/node/5873) and [NETL site-screening best practice](https://netl.doe.gov/node/5829).

## Roadmap increments

1. **Project package ingestion:** Accept CSV, LAS, and WITSML summaries alongside GIS boundary polygons with units, coordinate reference systems, and validation checks.
2. **Evidence-based storage-complex model:** Incorporate reservoir boundaries, net-to-gross ratios, flow property distributions, pressure-temperature-salinity profiles, capillary pressure curves, and stress states with explicit uncertainty ranges.
3. **Calibrated dynamics:** Couple compositional-flow simulators to generate project-specific scenarios, conditioning surrogates strictly within valid operational envelopes.
4. **Fault and well integrity workspace:** Enable direct input of mapped fault traces, offsets, throw, permeability ranges, and legacy well locations to rank migration pathways.
5. **Monitoring and decision workflow:** Generate baseline, operational, and contingency monitoring plans covering downhole pressure, injection rates, seismic logs, and tracer tests.
6. **Governance and compliance:** Implement role-based access control, immutable run logs, downloadable audit packages, and explicit regulatory disclaimers.

## Product rules

- Every output explicitly identifies its source: measured site data, user input, synthetic dataset, surrogate prediction, or analytical calculation.
- Input updates modify only the specific downstream calculations dependent on those values.
- Default examples carry explicit example labels and never present as measured site data.
- Output probabilities match the precision supported by underlying model calibration.
- The interface presents actionable risk ranges and uncertainty thresholds rather than binary indicators.

