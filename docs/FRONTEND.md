# Frontend — direction, and what is actually real

Companion to `docs/FINDINGS.md` and `docs/SITE_SUITABILITY.md`, same rules:
report what exists, including what doesn't. This covers the interactive
frontend at `app/web/index.html`, which replaces the Streamlit dashboard as
the *shippable* face of the project.

---

## Summary

**What this is:** a single self-contained HTML page — no server, no build
step, no dataset — that presents the pipeline as three panels: a site atlas,
a reservoir view, and a risk readout.

**Why it exists:** `app/dashboard.py` (Streamlit) cannot be deployed. It
requires `torch`, `xgboost` and the converted 12.38 GB dataset, and calls
`st.stop()` when `data/states.npy` is absent — which it is on any machine
that has not run the full download. It is a local research tool and should
keep being treated as one.

**Read this before quoting anything off the page:**

| Panel | Status | Source |
|---|---|---|
| **1. Storage Atlas** | ✅ **Real** | All 1,000 rows of `outputs/site_suitability_ranking.csv`, embedded. Real scores, real ranks, real criteria. The weight toggle re-scores live using the same formula as `src/site_suitability.py`. |
| **2. Breathing reservoir** | ⚠️ **Mockup** | Procedural stand-in fields. Correct *qualitative* behaviour (heterogeneous permeability, a plume that grows on injection and retreats on withdrawal, pressure peaking at the end of each injection stage) but **not model output**. |
| **3. Risk / attribution** | ⚠️ **Mockup** | Real feature names from `outputs/shap_features.json`, invented magnitudes. Layout only. |

The page states this on itself, twice — a per-panel badge in each panel bar,
and a footer that names exactly which data is real. Do not remove those.

---

## Design direction

The one-line thesis: **an instrument, not a dashboard.** The pipeline's whole
claim is that a multi-hour reservoir simulation becomes a sub-second screening
pass. A frontend that renders that as static matplotlib PNGs throws the claim
away. The six decisions that follow from it:

1. **The plume is the hero, and it breathes.** Ten annual injection/withdrawal
   cycles is a rhythm, and the plume grows and shrinks with it. That is the
   most characteristic motion in the dataset and no static figure shows it.
   The timeline is therefore the *cycle ribbon* — 60 ticks banded by stage —
   not a generic slider.

2. **A 2.5D slab, not three flat `imshow` panels.** The domain is
   7,680 m × 7,680 m × 100 m under a sealed caprock. Rendered as an extruded
   slab with a translucent lid, the fault becomes a vertical plane *piercing
   the seal* — which is the entire physics argument, made in one picture.

3. **The fault swarm replaces the histogram.** A histogram of N probabilities
   abstracts away something inherently spatial. Drawn as segments on the plan
   view, coloured by risk, you see that the dangerous faults sit on the plume
   front near the pressure ridge.

4. **Provenance is the design system.** `src/config.py` already tags every
   constant `[DATASET]` / `[DERIVED]` / `[ASSUMED]`. That taxonomy is promoted
   into the UI as a chip on every number. The honesty stops being a yellow
   warning banner nobody reads.

5. **The weight toggle is the demo moment.** The suitability weights are
   `[ASSUMED]` and the top ten shifts 2–5 seats under re-weighting
   (`docs/SITE_SUITABILITY.md`). Reshuffling the ranking live turns that
   caveat from a footnote into the thing the audience remembers.

6. **The latency is on screen.** "Sub-second instead of multi-hour" is the
   core claim and it currently lives in a README. Every recompute on the page
   is timed with `performance.now()` and printed.

**Palette:** the two accents are sampled from viridis and inferno — the
colormaps `app/dashboard.py` already uses for saturation and pressure. A
legend colour and a UI colour meaning the same thing is free coherence. Both
light and dark themes are built; dark is a workstation, light is a plotted
chart on paper.

---

## Deployment

The page is one file with no external requests, so anything that serves static
files works, and it also opens correctly straight from disk
(`open app/web/index.html`) if venue Wi-Fi fails.

**GitHub Pages** is the default: the repo is already on GitHub, it is free,
and `.github/workflows/pages.yml` publishes `app/web/` on every push to
`main`. It needs one manual step that cannot be done from code —
**Settings → Pages → Source → GitHub Actions** — after which the site is at
`https://sonil15.github.io/HyLeakAI/`.

Alternatives, in case Pages is inconvenient: drag `app/web/` onto
<https://app.netlify.com/drop>, or `npx vercel deploy app/web`. Both are
about a minute and neither needs the repo.

---

## Next round: making panels 2 and 3 real

Estimated at **half a day of build time**, plus one Kaggle run that can happen
in parallel. Steps 2, 3 and 5 do not depend on the data pack — build against
the existing procedural stand-ins and swap real data in at the end.

### Step 1 — the demo pack (must run on Kaggle, where the data is)

Write an export kernel that selects ~24 held-out test simulations and writes,
per simulation:

- pressure and H2 saturation, all 60 timesteps, quantised to uint8 and packed
  as greyscale PNG sprite sheets;
- the porosity and permeability maps;
- the U-Net's *predicted* pressure and saturation for the same steps, so the
  simulator-vs-surrogate toggle keeps working without torch in the browser.

The arithmetic that makes this viable:

| | bytes |
|---|---|
| one field, one timestep, uint8 | 128 × 128 = 16 KB |
| one simulation, 60 steps × 2 fields | 1.97 MB |
| + porosity and permeability | 32 KB |
| **per simulation, raw** | **≈ 2 MB** |
| 24 simulations on the CDN | ≈ 48 MB |

**The browser only ever fetches the simulation the user selected.** That is
the whole trick: ship fields, not a dataset. 12.38 GB → ~2 MB per site
selection, less once PNG-compressed.

On quantisation: uint8 gives ~0.4% resolution, dequantised through the min/max
already in `checkpoints/stats.json`. The surrogate's own pressure error is
~16% (`docs/FINDINGS.md`), so quantisation sits two orders of magnitude below
the error we already report. It is not a meaningful additional approximation.

**If a previous Kaggle output holds the converted arrays, attach it as an
input and skip the Zenodo download** — that is the difference between a
~15-minute run and a ~1-hour one.

### Step 2 — port the model and the physics to JS

- `fault_leakage_flux` in `src/leakage/labels.py` is closed-form; it is a
  handful of lines in JS. Port the monotonicity self-checks with it.
- Dump the XGBoost booster to JSON and walk the trees in ~150 lines. **Open
  question, resolve first:** the classifier is 2.0 MB as `.ubj` (0.69 MB
  gzipped); the JSON dump is typically several times the binary and has not
  been measured, because `xgboost` is not installed locally. If it comes out
  unreasonable for a web payload, retrain with fewer or shallower trees rather
  than reaching for a server.

### Step 3 — the panels

Most of the drawing already exists in `app/web/index.html` and carries over
largely as-is: the oblique projection, the colormap ramps, the cycle ribbon,
the scatter with its iso-score lines, the fault hit-testing.

### Step 4 — swap the stand-ins for the demo pack

Replace `buildFields()` / `updateFields()` with sprite-sheet loading and
dequantisation. Delete the "MOCKUP FIELD" badges **only** as each panel
actually becomes real.

### Step 5 — build tooling

Only worth introducing when step 2 lands, since a tree-walker and sprite
loading want modules and types. Vite + TypeScript; keep canvas and skip a
charting library, which would fight the projection, the colormaps and the
ribbon and still not draw the slab.

### Also worth doing, and cheap

- **Safe injection pressure limit** (item 2 on the README's path ahead). The
  caprock margin feature already exists; deriving an explicit max-safe-pressure
  number from it and putting it in the readout closes most of the remaining
  gap in module 2.
- **Wire the real SHAP values** into the attribution waterfall from
  `outputs/shap_features.json` and the SHAP output. Until then the waterfall
  is layout only and is labelled as such.

---

## Maintenance note

`app/web/index.html` is the canonical copy. It is self-contained by design —
a strict no-external-requests page — so keep it that way: no CDN scripts, no
webfont URLs, no remote images. If it ever needs a font, inline it as a data
URI.
