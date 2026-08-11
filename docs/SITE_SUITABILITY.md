# Site suitability — a running record

Companion to `docs/FINDINGS.md`, same rules: report what we measured,
including what didn't work. This covers the work done after checking out
`feat/unet-xgboost-leakage-pipeline`, closing the gap identified against the
original 4-module pitch (`Document 9.pdf`): module 1, "geological
intelligence" / subsurface site screening, had no code at all. This is that
module's first prototype.

---

## Summary

**What this does:** ranks the 1,000 geological realisations in the Mao et
al. UHS dataset by how suitable each is for hydrogen storage — a 0-100
suitability score and a full ranking, the first working piece of the
"geological intelligence" module from the original project scope.

**Method:** a weighted multi-criteria score, not a classifier and not
clustering.

| Criterion | Weight | From | Direction |
|---|---|---|---|
| Capacity | 0.5 | mean porosity (storage volume / injectivity proxy) | higher is better |
| Seal risk | 0.3 | peak pressure vs. the caprock's assumed fracture pressure | higher is worse |
| Heterogeneity | 0.2 | porosity variability within a realisation | higher is worse |

KMeans clustering was tried first, to group sites into discrete "types." It
didn't work: the geology varies along continuous axes with no natural gaps
(best silhouette 0.263 — weak; porosity and permeability are ~perfectly
correlated in this dataset, r=1.00). A continuous score is both what the
data actually supports and the standard approach real CO2/H2 storage-site
atlases use, so it replaced clustering rather than sitting alongside it.

**Results:**
- Scores span the full 0-100 range (median 46.9), so the ranking spreads the
  population out rather than bunching it.
- Top: sim 468, score 100/100 — highest porosity/permeability in the set.
  Bottom: sim 974, score 0/100 — lowest.
- **Robustness check:** re-scored under 4 very different weightings.
  Broad tier placement holds up (Spearman ρ 0.73-0.96 vs. the default
  weights), but the exact top-10 shifts by 2-5 seats depending on the
  weighting. Report which *tier* a site lands in on stage, not "site #468 is
  THE best site."

**Honest limit:** these are 1,000 synthetic realisations of one domain, not
1,000 real-world locations — this ranks candidate rock properties, not
places on a map. No leakage-risk information is mixed in (that's a separate
model, module 2, kept deliberately separate). No frontend yet.

Code: `src/site_suitability.py` (`python -m src.site_suitability`). Full
ranking: `outputs/site_suitability_ranking.csv`. Summary: `outputs/site_suitability_summary.json`.

*Everything below is the detailed working log: how this was built, the two
Kaggle bugs hit along the way, and the reasoning behind each choice.*

---

## 0. Why this module, and why now

`README.md`'s status table (added this session) maps the shipped pipeline
against the original 4-module pitch. Module 2 (leakage prediction) and a
slice of module 3 (dashboard) exist; module 1 (which sites are even worth
storing hydrogen in) and module 4 (economics) did not. With round-1
submission same-day, module 1 was chosen as the priority: it's the more
fundamental gap (you screen sites before you screen leakage risk at one), and
unlike economics it doesn't need a new set of unverified $/kg assumptions to
produce something defensible.

**Constraint that shaped everything below:** no time to source and integrate
new real-world geological data. Everything here reuses the Mao et al. UHS
dataset already in the pipeline (`docs/FINDINGS.md`), and reuses
already-tested code (`src/leakage/features.py`, `src/leakage/labels.py`)
rather than writing new feature logic.

**Framing this makes honest, and repeats on stage:** the dataset's 1,000
"simulations" are 1,000 porosity/permeability *realisations of one synthetic
domain*, not 1,000 distinct real-world locations. So this module answers
"given a candidate reservoir's rock properties, how does it rank against this
population" — not "here is a map, drill here." That's still a legitimate and
standard framing (it's how CO2/H2 storage atlases screen prospects), just not
what "site selection" sounds like at first mention.

## 1. Getting the data onto Kaggle, without the local disk

**Status: done. 6.6 minutes, measured.**

The M1 this runs on had 9.1 GB free disk; the raw Zenodo LMDB alone is
12.38 GB, so it doesn't fit locally even before the ~3.9 GB converted output
is added. `data/download.py`'s own file is a *single* monolithic LMDB blob —
there is no way to fetch just the small porosity/permeability slice without
reading the whole thing once, so partial download wasn't an option either.

Kaggle was already the proven path for exactly this (the U-Net training
notebook does the same download+convert). Built `kaggle/make_prep_notebook.py`,
a generator producing a **GPU-free, download-and-convert-only** notebook —
deliberately smaller than the full training notebook, since this step needs
neither a GPU nor training code. Pushed and ran it via the Kaggle API
(`kaggle kernels push`), using credentials already present in
`~/.kaggle/kaggle.json`.

Measured, from the kernel's own log:

| Step | Time |
|---|---|
| Download (12.38 GB, 16 parallel connections) | 4.6 min, up to 51 MiB/s |
| MD5 verify | included above |
| LMDB -> memmap conversion (1000 sims) | 66 s |
| Round-trip verification | pressure err 3.1e-2 bar (limit 4.7e-2), saturation err 2.4e-4 (limit 7.3e-4) — both within float16 tolerance |
| **Total** | **6.6 minutes** |

Output: `sonilnegi/hyleakai-dataset-download-conversion` (Kaggle kernel,
persisted output = `data/constants.npy`, `data/states.npy`, `data/stats.json`).
Stats matched `docs/FINDINGS.md` exactly (porosity mean 0.280, permeability
1.03-738.8 mD, pressure 82.7-293.8 bar) — same dataset, correctly converted.

## 2. Feature extraction: reuse, don't reimplement

**Status: done, after two bugs.**

`src/leakage/features.geology_features()` and
`src/leakage/labels.caprock_margin()` already compute exactly what's needed
per realisation (porosity/permeability statistics; peak pressure vs. an
assumed fracture gradient) — built for the leakage-risk pipeline, but nothing
about them is leakage-specific. Rather than reimplement this logic in a
Kaggle-flattened script (the way `kaggle/hileak_*.py` reimplements the U-Net
training path), `kaggle/make_suitability_notebook.py` embeds
`src/config.py`, `src/leakage/labels.py`, and `src/leakage/features.py`
**verbatim** into the notebook and imports them directly. Same reasoning as
the rest of this project's Kaggle tooling: duplicated logic is how a fix in
one place silently stops applying in the other.

This notebook attaches the previous kernel's *output* as an *input*
(`kernel_sources` in `kernel-metadata.json`), so it re-reads the already-converted
arrays with **no internet and no re-download**.

Two bugs, both in the push mechanics, not the science:

1. `%%writefile` on an empty file (`src/__init__.py`, `src/leakage/__init__.py`)
   raises `UsageError: cell body is empty`. Fixed by `Path(...).touch()`
   instead of embedding the (empty) file content.
2. `kernel-metadata.json`'s `id` field didn't match the slug Kaggle actually
   assigned from the title (same "title does not resolve to id" warning
   Kaggle prints and that this project should now treat as non-cosmetic) —
   caused a `409 Conflict` on the second push. Fixed by setting `id` to the
   real assigned slug.

Third push succeeded: 1000/1000 simulations processed in the log, wall time
~4 minutes, output = `site_features.csv` (poro_mean, poro_std, logk_mean,
logk_std, p_max_bar, caprock_margin_peak per simulation).

## 3. Clustering was tried first, and it doesn't work here

**Status: measured. Negative result — same discipline as `docs/FINDINGS.md`
§2 and §3.**

First attempt: KMeans on the 5 features above, k swept 2-6, best k chosen by
silhouette score.

| k | silhouette |
|---|---|
| 2 | 0.259 |
| **3** | **0.263** (chosen) |
| 4 | 0.234 |
| 5 | 0.231 |
| 6 | 0.233 |

0.263 is weak — the conventional floor for "real cluster structure" is
~0.25, so this sits right at the edge where the honest reading is "no
strong structure," not "3 site types." Diagnosed why, locally, on the
returned CSV (no Kaggle round-trip needed for this part):

```
correlation matrix:
                     poro_mean  poro_std  logk_mean  logk_std  caprock_margin_peak
poro_mean                 1.00      0.25       1.00      0.01                 0.12
poro_std                  0.25      1.00       0.24      0.97                 0.01
logk_mean                 1.00      0.24       1.00      0.00                 0.12
logk_std                  0.01      0.97       0.00      1.00                -0.02
caprock_margin_peak       0.12      0.01       0.12     -0.02                 1.00
```

`poro_mean` and `logk_mean` correlate at **r = 1.00** — in this dataset
they're the same underlying quantity via a fixed porosity-permeability
transform, not two independent signals. `poro_std`/`logk_std` correlate at
**r = 0.97**, same story for the heterogeneity axis. PCA on the 5 features
puts 99.9% of variance in 3 components (45.2% / 35.3% / 19.4%) with no gap
between them — 3 continuous axes (mean quality, heterogeneity, caprock
margin), not discrete groups. KMeans forcing hard boundaries onto continuous,
ungapped distributions is exactly what produces a weak silhouette regardless
of k — the clustering code is not wrong, the premise (that this population
has natural groups to find) is.

**Consequence: clustering is dropped for this task.** Also corrects something
said earlier in this project's own working notes: a claim that "higher-quality
geology correlates with higher caprock margin (no free lunch)" was drawn from
the cluster-mean table and overstated — the real correlation is r = 0.12,
weak, not a trend worth repeating.

## 4. What replaced it: a continuous suitability score

**Status: done, in `src/site_suitability.py`.**

A weighted multi-criteria score is both the honest framing (matches what
the correlation structure actually supports — a ranking along continuous
axes) and the standard one: CO2/H2 storage-site atlases screen prospects
this way (porosity, permeability, seal integrity, weighted and summed), not
by clustering candidates into named types.

```
capacity      = minmax(poro_mean)              # logk_mean not added separately: r=1.00 with
                                                 # poro_mean here, so summing both would just
                                                 # double-count one signal
seal_risk     = minmax(caprock_margin_peak)     # higher = closer to assumed fracture pressure = worse
heterogeneity = minmax(poro_std)                # higher = less predictable injection = worse

score = 0.5 * capacity - 0.3 * seal_risk - 0.2 * heterogeneity      # then rescaled to 0-100
```

The three weights are **[ASSUMED]**, tagged as such in the module docstring —
same convention `src/config.py` uses for the leakage pipeline's assumptions,
because there is no ground-truth "suitability" label to fit them against, the
same reason the leakage labels in `src/leakage/labels.py` are derived rather
than trained. `--w-capacity` / `--w-seal` / `--w-het` on the CLI so the
weighting is a stated, sweepable choice rather than a buried constant.

**Sensitivity check before calling this done** — same principle as
`docs/FINDINGS.md`'s tripwire discipline (don't report a number without
checking whether the assumption behind it is load-bearing):

| Weight variant | Spearman ρ vs. default | Top-10 overlap |
|---|---|---|
| Equal weights (.34/.33/.33) | 0.912 | 7/10 |
| Capacity-only (1/0/0) | 0.730 | 5/10 |
| Seal-heavy (.3/.6/.1) | 0.800 | 6/10 |
| Drop heterogeneity term (.6/.4/0) | 0.957 | 8/10 |

**Reading this honestly:** the broad ordering is reasonably stable (ρ
0.73-0.96 across quite different weightings) — which quartile a site falls
in is a robust statement. The exact top-10 is not — it shifts by 2-5 seats
depending on how much weight goes to seal risk vs. capacity. Report tiers or
percentile rank on stage; don't lean on "site #468 is the single best site in
the dataset."

Output: `outputs/site_suitability_ranking.csv` (all 1000, ranked; gitignored
as a regenerable raw dump, same policy as `data/features.npy` — see
`.gitignore`'s outputs section) and `outputs/site_suitability_summary.json`
(top/bottom 10, score distribution, weights used — tracked, small, matches
how `outputs/xgb_results.json` is kept for the leakage pipeline).

## 5. What this deliberately does NOT do

State these before being asked, same as `docs/FINDINGS.md` §10:

- **Not real-site selection.** This ranks 1,000 synthetic realisations of one
  domain against each other, not real geographic locations. Says so in §0.
- **Not integrated with the leakage-risk model.** `caprock_margin_peak` is
  used here as a static geological descriptor; the fault-conditional flux
  forecast (module 2) is a separate question about a separate hypothesis
  (a specific fault, at a specific chosen site) and mixing the two would
  conflate "is this rock good" with "is this specific fault dangerous."
  Keeping them separate is a deliberate architecture choice, not an oversight.
- **Not validated against any ground-truth suitability label** — none exists,
  same absence of ground truth that motivates the derived leakage labels.
- **No frontend yet.** This is backend/analysis only; visualisation (a chart,
  or a dashboard panel) is the next, explicitly deferred step.

## 6. Files this produced

| File | What |
|---|---|
| `kaggle/make_prep_notebook.py` | generator: download+convert-only Kaggle notebook |
| `notebooks/kaggle_prep_data.ipynb` | generated notebook, run as `sonilnegi/hyleakai-dataset-download-conversion` |
| `kaggle/make_suitability_notebook.py` | generator: feature extraction + clustering notebook |
| `notebooks/kaggle_site_suitability.ipynb` | generated notebook, run as `sonilnegi/hyleakai-site-suitability-features-clustering` |
| `src/site_suitability.py` | the scoring/ranking module — `python -m src.site_suitability` |
| `outputs/site_suitability_summary.json` | tracked in git |
| `outputs/site_suitability_{features,clusters,cluster_summary,ranking}.csv` | gitignored, regenerate via the two notebooks + `python -m src.site_suitability` |

None of this is committed yet — everything above is in the working tree on
`feat/unet-xgboost-leakage-pipeline`.
