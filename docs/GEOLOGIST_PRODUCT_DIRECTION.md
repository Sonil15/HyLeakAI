# HyLeakAI: geologist-facing product direction

## What the product can claim today

HyLeakAI is a **screening tool**, not a site model. Its live service predicts
pressure and saturation for held-out synthetic geological realisations using a
U-Net surrogate, then scores explicitly supplied or sampled fault hypotheses
with an XGBoost classifier. The 128 by 128 fields, model provenance and fault
probabilities are real service outputs. They are not measurements from a user
site and must not be presented as such.

The public interface now has two deliberately separate paths:

1. **Site-input screen.** A transparent scalar volumetric calculation takes a
   user's interpreted area, thickness, porosity, efficiency, CO2 density,
   depth, overpressure allowance, injection schedule and caprock thickness.
   It returns effective capacity, planned mass, utilisation and a hydrostatic
   pressure ceiling. A default saline-aquifer case makes the workflow usable
   without a data upload.
2. **Analogue risk screen.** The deployed surrogate remains a way to explore
   representative field behaviour and fault-pathway sensitivity. It must keep
   the labels “synthetic realisation” and “screening only.”

This separation is essential: scalar inputs cannot validly be mapped into the
current U-Net, which was trained on gridded synthetic realizations.

## Why these inputs matter

Reservoir structure, thickness, porosity/permeability and natural flow control
capacity and plume behaviour. Seal continuity, entry pressure, faults and
geomechanical response control containment. NETL identifies pressure-front and
plume tracking, potential migration pathways, faults/fractures and physical
property change as core monitoring concerns. [NETL subsurface
monitoring](https://netl.doe.gov/node/5873) and [NETL site-screening best
practice](https://netl.doe.gov/node/5829) support this workflow.

## Next product increments, in order

1. **Project package input.** Accept CSV/LAS/WITSML-derived summaries and GIS
   polygons with units, coordinate reference system, provenance and validation.
   Keep raw files private; persist a versioned input manifest.
2. **Evidence-based storage-complex model.** Add reservoir top/base, net-to-
   gross, porosity/permeability distributions, pressure/temperature/salinity,
   relative permeability and capillary-pressure curves, wells, faults, caprock
   entry pressure and stress data. Require uncertainty ranges rather than one
   “best” number.
3. **Calibrated dynamics.** Couple a compositional-flow or trusted reservoir
   simulator to generate project-specific scenarios, then train/condition a
   surrogate only inside that scenario envelope. Show out-of-distribution
   warnings and prediction intervals.
4. **Fault and well integrity workspace.** Let users enter mapped fault traces,
   offsets, throw, permeability ranges, orientation/stress relationship and
   legacy wells. Rank pathways with evidence links, rather than random samples.
5. **Monitoring and decision plan.** Generate baseline, injection and
   contingency monitoring actions: downhole pressure/temperature, injection
   rate and volume, well integrity, repeat seismic/logs, tracers and pressure
   fall-off testing. Track observed pressure and plume response against the
   forecast envelope. NETL notes that pressure front and plume front need to be
   distinguished and that monitoring design must identify possible pathways.
6. **Governance.** Add project roles, assumption approvals, immutable run
   records, downloadable input/result packages, data-retention controls and an
   explicit “not permit-ready” gate until calibrated studies are attached.

## Product rules

- Every output names its source: measured, user-entered, synthetic dataset,
  surrogate prediction or derived calculation.
- A change in user input must visibly change only outputs that actually use it.
- Default examples are labelled examples, never “site data.”
- No probability is shown with more precision than the calibration supports.
- The UI shows actionable thresholds and uncertainty, not a single traffic
  light.
