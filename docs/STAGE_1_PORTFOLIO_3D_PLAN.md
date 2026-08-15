# Stage 1 — 3D Portfolio Explorer plan

## Goal

Turn the Storage Atlas into a defensible, explorable ranking of the 1,000
synthetic geological realisations. It must let a user understand *why* a
realisation ranks where it does, inspect every point, and select one to carry
into the reservoir assessment. It must not suggest that the points are real
geographic drilling locations.

## Scientific basis to preserve

The ranking is a weighted multi-criteria screening score, not a trained
probability and not a field-specific storage permit decision.

```text
capacity       = min-max(mean porosity)                 higher is better
seal risk      = min-max(peak caprock pressure margin)  higher is worse
heterogeneity  = min-max(porosity standard deviation)   higher is worse

raw score = 0.50 × capacity − 0.30 × seal risk − 0.20 × heterogeneity
suitability score = min-max(raw score) × 100
```

`logk_mean` is deliberately not an extra scoring term: in this dataset it is
almost perfectly correlated with mean porosity, so adding it would double-count
the same geological signal. Measured across all 1,000 realisations,
`corr(poro_mean, logk_mean) = 0.9995`.

### Seal-risk assumption and threshold

The source metric is:

```text
caprock pressure margin = (Pmax − Pinitial) / (Pfracture − Pinitial)
```

- `0` means peak pressure stayed at initial pressure.
- `1.0` means the assumed fracture pressure was reached; values above `1.0`
  are an exceedance.
- `Pfracture` is derived from an **assumed** reservoir depth and fracture
  gradient in the project configuration.

This is a standard *type* of pressure-screening criterion, but `1.0` is not a
universal industry approval threshold and cannot substitute for a
site-specific geomechanical fracture-pressure study. The interface will state
that directly and label the score weights and fracture-gradient inputs as
assumptions.

**Measured distribution, and why the axis is not drawn to 1.0.** Across all
1,000 realisations the peak margin runs **0.431 to 0.792** (median 0.645), and
**zero** realisations exceed 1.0. Drawing the seal axis from 0 to 1.0 with a
threshold marker would push every real point into the lower half of the axis
and imply the portfolio was screened against a limit it never approaches. The
axis is therefore scaled to the observed range so real differences stay
visible, and the `1.0` exceedance point is stated in the disclosure text
instead of drawn. This is a presentation choice about resolution, not a
softening of the caveat.

## Experience design

### 1. Scoring explainer at the top of Stage 1

Add a compact, always-visible “How this ranking is calculated” panel above
the visualisation:

- the formula, signs, weights, normalisation, and a one-line interpretation;
- three criterion cards: capacity (50%), seal risk (30%), heterogeneity (20%);
- a disclosure popover describing the seal-margin equation, `margin = 1.0`
  exceedance point, and its project-specific assumptions;
- an explicit banner: “1,000 synthetic geological realisations — not map
  locations or drill recommendations.”

Weight presets will remain visible and will update both the formula labels and
every displayed rank/score immediately.

### 2. Interactive 3D point cloud

Replace the 2D canvas scatter with a rotatable 3D chart:

| Dimension | Data | Direction |
|---|---|---|
| X | Normalised capacity | right is better |
| Y | Normalised seal risk | upward is worse |
| Z | Normalised heterogeneity | farther/deeper is worse |
| Colour | Recomputed suitability score | low → high score |
| Size/outline | selection and live-model availability | visual state only |

Interactions:

- drag to orbit; scroll/pinch to zoom; reset view; keyboard-accessible reset;
- hover/raycast a point for simulation ID, rank, score, all three normalised
  criteria, and their raw geological values where available;
- click selects the point, synchronises the details pane and ranking list,
  and clearly states whether it is available for Stage 2 live inference;
- depth cues (axes, floor projection, subtle grid, transparent points) prevent
  the third variable from becoming hidden decoration;
- a responsive 2D fallback is retained for WebGL-disabled or narrow devices.

Implementation: a pinned Three.js build **vendored into `app/web/`**, not
loaded from a CDN. It gives real orbit controls and point picking without a
fragile hand-built projection, and serving it same-origin keeps the page
working with no internet — a CDN outage or flaky venue wifi during judging
would otherwise mean no 3D at all. Cost is ~600 KB in the repo and image.

Note the frontend is no longer on GitHub Pages: FastAPI serves `app/web/` from
the same Cloud Run origin, so there is no cross-origin consideration here.

The fallback uses the current Canvas renderer and preserves selection/table
controls.

### 3. Clear colour legend and visual accessibility

Add a labelled, perceptually ordered viridis scale beside the chart:

- `0 — low suitability` to `100 — high suitability`;
- tick marks at 0, 25, 50, 75, and 100;
- a separate outline/shape cue for selected and Stage-2-available points, so
  meaning does not depend only on colour;
- visible legends for every encoding: position, colour, point state.

### 4. Full ranking list and selected-point evidence

Replace the short “top 12” table with a searchable, sortable virtualised list
of all 1,000 points.

- columns: rank, simulation ID, score, capacity, seal risk, heterogeneity,
  raw mean porosity, peak pressure margin, and Stage-2 availability;
- sorting by any column and filters for score/tier and live-model availability;
- row hover highlights the corresponding 3D point; row click selects it;
- details panel shows the selected point’s raw values, normalised inputs,
  weighted contributions, assumptions, and the currently active weighting;
- export the current ranking/filter state as CSV/JSON.

Only held-out test IDs will be marked **“Live field prediction available”**.
All other points can be ranked but must not imply that their 2D U-Net field is
available.

## Implementation sequence

1. **Data** — there is no `/v1/suitability` endpoint; the API exposes
   `/health`, `/v1/simulations`, `/v1/metadata`, `/v1/fields/{id}` and
   `/v1/assessments`. Stage 1 data is embedded inline in `index.html` as a
   `SITES` array of `[sim_id, capacity, seal_risk, heterogeneity, score,
   rank]`, which lacks the raw values the tooltip and table need. Extend the
   embedded rows with `poro_mean`, `logk_mean` and `caprock_margin_peak` from
   `outputs/site_suitability_ranking.csv` (~+40 KB). Embedding rather than
   adding an endpoint keeps Stage 1 free of a cold-start fetch and working
   when the API is down.
2. **Frontend structure** — split Stage 1 into a maintainable module instead
   of extending the large inline page script; define a single score function
   shared by the plot, table, tooltip and export.
3. **Scoring explainer** — implement the formula/assumption panel and
   disclosure language before the graph.
4. **3D renderer** — build point cloud, axes, orbit/zoom/reset, GPU-aware
   fallback, hover picking and selection synchronisation.
5. **Legend and details** — add the colour scale, encoding legend, selection
   card and score-contribution calculation.
6. **Ranking list** — implement all-row sorting/filtering/search and
   chart/list bidirectional highlighting.
7. **Verification** — unit-test score parity against the Python ranking;
   browser E2E-test loading 1,000 points, hover contents, orbit/reset,
   selection, reweighting, list sort/filter, fallback mode and Stage-2 handoff;
   then test against the live Cloud Run API and GitHub Pages deployment.

## Verification results

`python scripts/test_atlas_e2e.py` — 22/22 assertions pass in headless Chrome,
driving the real page inside a same-origin iframe. Covers 3D initialisation,
1,000 points, virtualisation, reweighting, selection propagation to Stage 2,
filters, search, sorting and view reset.

`python scripts/embed_atlas.py --check` — verifies the embedded array matches
the CSV; exits 1 if stale.

### Score parity, measured

Under default weights the JS recomputation agrees with the Python ranking to
**max |Δ| = 0.005** on a 0–100 scale. Rank order is not bit-identical: 113
sites shift, **maximum displacement 2 places, and the maximum CSV score gap
across any swap is 0.0000**. Every disagreement is tie-ordering between sites
whose scores are indistinguishable (the ranking contains 94 exact ties). The
top 10 match exactly. This is inherent to recomputing from rounded normalised
inputs and is not worth removing — but ranks should be read as tier bands, as
the interface already says.

### Two bugs this verification caught

1. **`three.module.min.js` alone is not enough** — it imports
   `three.core.min.js`, and downloading only the first gives a runtime 404 with
   nothing logged that points at the cause. The 3D view would simply never
   appear.
2. **A fixed fallback timer is the wrong mechanism.** The first implementation
   demoted the atlas to 2D after 4 s, which races the ~720 KB Three.js
   download — a working 3D view would drop to 2D on slow wifi. Replaced with
   signal-based detection: the `<script>` `error` event, an explicit
   `moduleStarted()` call, and a guarded `init()` that reports the real reason,
   with a long timer only as a last-resort backstop.

## Acceptance criteria

- Every one of the 1,000 points is plotted in X/Y/Z and remains selectable.
- A hover exposes score plus all three input values without pretending they are
  geographic coordinates.
- Formula, default weights (50/30/20), normalisation and seal-risk assumption
  are visible before interaction.
- The colour gradient has a numerical legend and selection does not rely only
  on colour.
- The side ranking list covers all points and stays in exact parity with the
  active weights.
- A selected point has an unambiguous live-model-availability state.
- No text calls the assumptions universal industry thresholds or claims the
  synthetic portfolio is a real site map.

## Decisions taken

| Question | Decision | Reason |
|---|---|---|
| Raw values for tooltip/table | Embed 3 more columns in `SITES` | No cold-start fetch; Stage 1 survives an API outage |
| Three.js delivery | Vendor into `app/web/` | Page stays self-contained; no CDN risk mid-demo |
| Fracture-gradient / depth inputs | **Show but keep fixed** | Making them tunable turns the score into a scenario tool and invites "which setting is right?", which we cannot answer |
| Seal-risk axis scale | Scale to observed range; state `1.0` in text | Nothing exceeds 0.792, so a 0-1.0 axis wastes half the range and implies a screening that did not happen |

Weight presets stay interactive — they are a stated preference, not a physical
assumption, so varying them is honest in a way that varying fracture gradient
is not.
