# HyLeakAI — End-to-end presentation context

**Audience for this file:** an agent tasked with (a) explaining HyLeakAI to hackathon
judges, geology included, and (b) building the deck / visuals.

**This file is a briefing, not a script.** Everything in it is either sourced from a
file in this repo (path given) or explicitly marked as background knowledge the agent
must not attribute to our measurements. Numbers carry their provenance. If a number
you want to say is not in here with a source, go find the source before it goes on a
slide — this project's entire differentiator is that its numbers survive being
questioned.

**Reading order if you are short on time:** §1 (the pitch), §2 (the honesty contract
— non-negotiable), §6 (the numbers table), §9 (slide plan), §11 (Q&A bank).

---

## Table of contents

1. [What this project is, in three sizes](#1-what-this-project-is-in-three-sizes)
2. [The honesty contract — read before writing a single slide](#2-the-honesty-contract--read-before-writing-a-single-slide)
3. [Geology, in depth](#3-geology-in-depth)
4. [The dataset, read as a geological object](#4-the-dataset-read-as-a-geological-object)
5. [The pipeline, end to end](#5-the-pipeline-end-to-end)
6. [Every number, with provenance](#6-every-number-with-provenance)
7. [The three negative results — and why they are the strongest slides](#7-the-three-negative-results--and-why-they-are-the-strongest-slides)
8. [Visuals: what to draw, from what data, to prove what](#8-visuals-what-to-draw-from-what-data-to-prove-what)
9. [Deck structure and narrative arc](#9-deck-structure-and-narrative-arc)
10. [Live demo script](#10-live-demo-script)
11. [Q&A bank — hostile questions and honest answers](#11-qa-bank--hostile-questions-and-honest-answers)
12. [Design system for the deck](#12-design-system-for-the-deck)
13. [Glossary for a non-geologist judge](#13-glossary-for-a-non-geologist-judge)
14. [Forbidden claims](#14-forbidden-claims)
15. [File map — where everything lives](#15-file-map--where-everything-lives)

---

## 1. What this project is, in three sizes

### One sentence

> HyLeakAI turns a multi-hour underground-hydrogen-storage reservoir simulation into a
> sub-second screening pass, so an operator can Monte-Carlo thousands of *unknown* fault
> hypotheses instead of simulating one known fault.

### One paragraph

Underground hydrogen storage in depleted gas reservoirs is the only way to store hydrogen
at the terawatt-hour scale that seasonal energy balancing needs. The risk that kills a
site is a leak path through the caprock — usually a fault or a legacy well. You cannot
measure that risk directly, and the reservoir simulation that would estimate it takes
hours per scenario, so operators evaluate a handful of scenarios instead of the thousands
that the uncertainty in fault properties actually demands. HyLeakAI replaces the
simulator with a U-Net surrogate that predicts pressure and hydrogen-saturation fields
from geology alone, extracts 41 physically meaningful features from those fields, overlays
a hypothesised fault, and scores the probability of elevated leakage six months ahead with
a gradient-boosted model whose attributions are inspectable. The fault is introduced
*after* the surrogate, so a single field prediction can be re-scored against thousands of
fault realisations in milliseconds.

### The 30-second stage version

"Hydrogen is the storage medium for seasonal renewables, and the only containers big
enough are old gas reservoirs. The thing that ruins one is a fault you didn't know about
cutting the seal. Nobody knows those faults' properties — permeability is uncertain by
three orders of magnitude — so the honest question isn't 'will it leak', it's 'across
every fault this site could plausibly have, how much of that space is dangerous?' That is
a Monte-Carlo question, and Monte-Carlo needs a fast forward model. We built one. And
because we could not find honest ground truth for hydrogen leakage — nobody publishes it —
we spent as much effort proving what our numbers *don't* mean as producing them."

---

## 2. The honesty contract — read before writing a single slide

This is the part of the project that will win or lose the room. Do not soften it.

### The split

| | Status |
|---|---|
| **Porosity, permeability, pressure, H₂ saturation fields** | **Real.** Mao et al. (2025), 1,000 tNavigator physics simulations, Zenodo 14029514, CC-BY-4.0/MIT. |
| **Faults, caprock properties, leakage flux** | **Ours.** The source dataset contains none of them. Leakage is a semi-analytical Darcy flux through a *hypothetical* fault whose position, permeability, length and width we sample. |

So the correct description is **"physics-guided screening tool"**, never **"calibrated
leak-rate predictor."**

### Why this is not a weakness on stage

Say it in this order and it becomes the strongest thing about the project:

1. No public dataset contains hydrogen leakage measurements. Underground hydrogen storage
   has a handful of pilot projects worldwide and none publish continuous leakage
   monitoring. That absence is the *premise*, not an oversight.
   (`Data_sources_research.md` §1 — the doc is superseded but §1–§3 still stand.)
2. Given that, you have two choices: invent a label and call it ground truth, or derive a
   label from stated physics and label it as derived. We did the second and wrote down
   every assumed constant with a tag.
3. `src/config.py` tags **every** constant `[DATASET]` / `[DERIVED]` / `[ASSUMED]`. That
   taxonomy is promoted into the UI as a chip on every number — see `docs/FRONTEND.md`
   §"Provenance is the design system." Judges can audit a claim in one glance.

### The three things a judge could catch us on, that we caught first

These are in `docs/FINDINGS.md` and they are the deck's credibility spine. Full treatment
in §7 below.

- **T1 (lateral containment loss) is dropped.** 0/1000 simulations show the plume reaching
  the open boundary. We measured it and killed the target rather than lowering the
  threshold until labels appeared.
- **A binary "caprock breached" label is not defensible.** It flips from "never happens" to
  "sometimes happens" on one assumed fracture gradient. We report a continuous margin
  instead and never a breach rate.
- **Our own headline number was wrong, and we withdrew it.** An earlier AUC 0.9999 at a
  12-month horizon was mostly the reservoir's annual periodicity: a trivial persistence
  baseline scored 0.9918 there. We re-ran at a half-cycle horizon where persistence
  collapses to 0.0218 and reported that instead.

### The one sentence that must appear on a slide

> The features are real physics. The leakage labels are ours, derived from a hypothetical
> fault. This screens risk; it does not predict how much hydrogen will leak.

---

## 3. Geology, in depth

This section is background for the presenter, so they can answer follow-ups with fluency.
**Most of it is textbook subsurface engineering, not something we measured** — say so if
asked where a number comes from. Anything we actually measured is flagged **[OURS]**.

### 3.1 Why underground, why hydrogen, why depleted gas fields

Hydrogen's problem is volumetric energy density. At atmospheric conditions it carries about
0.01 MJ/L; even at 200 bar in a reservoir, storing a season's worth of grid energy means
millions of cubic metres of gas. Surface tanks and salt caverns are the only *proven*
hydrogen containers, and salt caverns are capacity-limited (typically 10⁵–10⁶ m³ each) and
geographically restricted to salt basins. Porous media — depleted gas reservoirs and saline
aquifers — offer two to three orders of magnitude more capacity and already exist in the
places that produced hydrocarbons.

Three storage classes, and the trade they present:

| Class | Proven for H₂? | Capacity | Main risk |
|---|---|---|---|
| **Salt cavern** | Yes — Teesside (UK), Clemens Dome / Moss Bluff / Spindletop (Texas) | Small per cavern | Salt creep, brine disposal, geography |
| **Depleted gas reservoir** | Not yet at commercial purity; Underground Sun Storage (Austria) injected an H₂/CH₄ blend into a depleted field | Very large | **Legacy wells, faults, heterogeneous seal, gas mixing** |
| **Saline aquifer** | Town gas (~50% H₂) was stored in aquifers historically — Beynes (France), Lobodice (Czech Republic) | Very large | No proven trap, microbial consumption (documented at Lobodice), water production |

HyLeakAI targets the **depleted gas reservoir** case, because that is where the risk is
both largest and *actionable*: the trap is proven (it held gas for millions of years) but
it has been perforated by decades of drilling and is being re-pressurised in an operating
mode nature never applied to it — cyclically, ten times a decade.

### 3.2 The trap: what holds gas underground

A hydrocarbon trap is four things at once, and hydrogen needs all four:

1. **Reservoir rock** — porous, permeable, usually sandstone or carbonate. Porosity φ is the
   fraction of rock that is void space (the storage volume); permeability k is how easily
   fluid moves through it (the injectivity).
2. **Seal / caprock** — a low-permeability unit above, usually shale, or evaporite (halite,
   anhydrite — the best seals on Earth). Typically tens to hundreds of metres thick.
3. **Structural closure** — a geometry (an anticline, a fault-bounded block) that stops
   buoyant gas from migrating updip forever. The **spill point** is the structural low
   beyond which further gas escapes laterally.
4. **Charge** — historically, a source rock. For storage, it's the compressor.

Break any one and the site is not a store. HyLeakAI's leakage model concerns itself with
failure of **(2)**, via a fault that cuts it.

### 3.3 How a caprock actually seals — and the two ways it fails

A caprock does not seal because it is impermeable in the absolute sense. It seals because
its pores are so small that gas cannot physically push water out of them. This is a
**capillary** seal.

**Capillary entry pressure:**

```
P_ce = 2 σ cos θ / r
```

- σ — gas/brine interfacial tension
- θ — contact angle (wettability; a water-wet rock has θ near 0)
- r — the largest connected pore-throat radius in the seal

Gas columns build buoyancy pressure against the seal at `Δρ · g · h`, where h is the column
height. When buoyancy exceeds P_ce, gas enters the seal — **capillary breakthrough**.

> **Hydrogen-specific correction that will impress a geologist and that this repo already
> caught:** an earlier AI-generated research doc in this project claimed hydrogen lowers
> caprock capillary entry pressure relative to methane. The literature does not support
> that — H₂/CH₄ wettability against water-wet caprock is comparable, and caprock stays
> water-wet. It also claimed H₂ is ~10× less viscous than CH₄; the actual viscosity ratio
> at reservoir conditions is **1.3–2.1×**, and the ~10× figure is the *density* ratio.
> Both errors were found and corrected (`Data_sources_research.md` §3). **Mentioning that
> we fact-checked our own research doc and found two inverted physics claims is a strong
> credibility move.**

The **second** failure mode is mechanical, and it is the one HyLeakAI models. If pore
pressure inside the reservoir rises high enough, the rock fails in tension and the caprock
**hydraulically fractures**. The threshold is the **fracture pressure**, estimated in
screening as `depth × fracture gradient`. Typical sedimentary-basin fracture gradients are
**0.15–0.20 bar/m**; **0.17 bar/m** is a common screening default and is our
`[ASSUMED]` value (`src/config.py:166`). Hydrostatic — the normal fluid pressure gradient —
is about **0.105 bar/m** for a ~1,050 kg/m³ brine, which is what we use to back out depth
(`src/config.py:137`).

**These two mechanisms are the reason the deck should show pressure, not saturation, as the
danger variable.** Hydrogen doesn't break the seal. Pressure does.

### 3.4 Faults: the seal's weakest link

A fault is not a plane. It has architecture, and the architecture decides whether it seals
or leaks:

- **Fault core** — comminuted, clay-smeared gouge. Usually *lower* permeability than the
  host rock. Seals *across* the fault.
- **Damage zone** — a halo of fractures either side of the core, metres to hundreds of
  metres wide, scaling roughly with fault displacement. Often orders of magnitude *more*
  permeable than the host rock, **along** the fault plane.

So the same fault can be a lateral barrier and a vertical conduit at the same time. That is
exactly the geometry that matters for storage: the conduit direction is *up*, through the
seal. This is why our fault model uses a **damage-zone width** as the conduit's
cross-section (`src/config.py:186`, 1–10 m `[ASSUMED]`) and a permeability sampled
**log-uniformly over three orders of magnitude**, 1e-15 to 1e-12 m² ≈ 1–1000 mD
(`src/config.py:183`). Log-uniform because a uniform draw would put almost all the
probability mass at the high end — a small but decisive modelling choice, worth one line
on the methods slide.

Fault-seal analysis in industry uses **Shale Gouge Ratio** (the clay fraction dragged into
the fault) to predict whether a fault seals. We do not compute SGR — we do not have
lithology logs. Say that if asked.

**Fault reactivation** is the other half of the fault story and is the mechanism behind
induced seismicity. Raising pore pressure lowers the *effective* normal stress on a fault
plane (`σ'ₙ = σₙ − P_pore`), sliding the Mohr circle toward the failure envelope. A fault
that is **critically stressed** in the current stress field can slip — and a slipping fault
transiently becomes far more permeable. Cyclic hydrogen storage pressurises and
depressurises the reservoir ten times per decade, which is exactly the loading history that
makes this a live concern rather than a textbook footnote. **We do not model geomechanics.**
The honest framing: our pressure-based caprock margin is a *screening proxy* for the same
underlying quantity, and full Mohr-Coulomb reactivation analysis is named future work.

### 3.5 Multiphase flow: the equations the pipeline actually uses

**Darcy's law**, single phase:

```
q = − (k/μ) ∇P
```

**Multiphase**, with gravity, which is what a reservoir simulator solves:

```
q_g = − (k · k_rg / μ_g) (∇P − ρ_g g)
```

The new term, **relative permeability `k_rg`**, is the single most important concept for
understanding our leakage label. When two fluids share a pore network they get in each
other's way; each phase only gets a *fraction* of the absolute permeability, and that
fraction depends on saturation. Below a **residual gas saturation** `S_gr`, the gas is
disconnected into isolated bubbles and cannot flow **at all**, no matter the pressure.

We use a **Corey** model (`src/leakage/labels.py:287`):

```
k_rg = ( (S_g − S_gr) / (1 − S_wr − S_gr) ) ^ n_g,   clipped to [0,1]
```

with `S_wr = 0.20` (irreducible water), `S_gr = 0.05` (residual gas), `n_g = 2.0` — all
`[ASSUMED]`, all in `src/config.py:176–178`.

> **This is the single best physics detail to put on a slide.** Without `k_rg`, a fault far
> from the plume would "leak" every time the reservoir pressurised, and the model would
> learn to be a pressure gauge. With it, leakage requires **both** overpressure **and**
> mobile hydrogen sitting on the fault. That's not a regularisation trick; it's the
> physics, and it's asserted in code (`check_monotonicity()` in
> `src/leakage/labels.py:368` verifies flux is exactly zero below residual gas saturation).

**Residual trapping and hysteresis.** During withdrawal (imbibition), brine re-invades and
snaps off gas into isolated ganglia. That gas is permanently lost to the working inventory —
up to ~41% residual saturation is reported for aquifers. In cyclic storage this both costs
you inventory *and* stabilises the plume. We do not model hysteresis; the dataset's
simulations already contain whatever relative-permeability treatment tNavigator applied,
which the paper does not fully specify.

### 3.6 What makes hydrogen different from methane or CO₂

Get these right; a reservoir engineer on the panel will check.

| Property | H₂ vs CH₄ at reservoir conditions | Consequence |
|---|---|---|
| **Viscosity** | H₂ is only **1.3–2.1× less viscous** (µ ≈ 9.8–10.9 µPa·s vs 14.5–23.3) | Mobility contrast against brine (µ ≈ 500 µPa·s) is severe → **unfavourable mobility ratio → viscous fingering**, an unstable displacement front |
| **Density** | H₂ is **~9–10× less dense** (≈12.5 kg/m³ at 350 K/200 bar vs ≈119 kg/m³ for CH₄) | This is the big one. Δρ against brine ≈ 985 kg/m³ → **strong buoyancy / gravity override**. Hydrogen rises and pools directly under the caprock. |
| **Molecular diffusivity in brine** | ~5×10⁻⁹ m²/s, **3–4× methane's** | Slow but non-zero loss into formation water over decades |
| **Microbial reactivity** | H₂ is an electron donor for methanogens, sulfate reducers, acetogens (below ~90–120 °C) | Documented conversion of stored H₂ to CH₄ at **Lobodice**. Sulfate reducers make **H₂S** — a corrosion and safety problem, not just a loss |
| **Steel compatibility** | Hydrogen embrittlement of high-strength casing/completion steels | Well-integrity problem specific to H₂ |
| **Joule–Thomson** | **Negative** JT coefficient above ~193 K — H₂ *warms* on throttling, unlike CH₄ | Surface-facility design detail; a nice one-liner, it surprises people |

Source for the viscosity/density table: `Data_sources_research.md` §3, computed with
CoolProp and **fact-checked against the original AI-generated version, which had the
ratio inverted.**

### 3.7 Where hydrogen actually goes — ranked, and why we model the least likely one

From `Data_sources_research.md` §3, ranked as the literature reports:

1. **Leakage through old / badly sealed wells** — the most likely *engineered* leak path
2. **Residual trapping** — gas immobilised in pores, up to ~41% residual saturation
3. **Dissolution + diffusion into brine**
4. **Microbial consumption** — methanogens and sulfate reducers
5. **Caprock capillary breakthrough** — the *least* likely; H₂ and CH₄ wettability are
   comparable and caprock stays water-wet

> **Put this list on a slide and then say the uncomfortable thing:** "Leakage through the
> seal is not the largest hydrogen loss. Cushion gas, residual trapping and dissolution are
> all bigger. We model the fault-conduit path because it is the one that is *actionable* —
> you can de-rate injection pressure, or not pick the site — and because it is the one with
> a safety and permitting consequence rather than just an inventory consequence."

Volunteering that you are not modelling the biggest loss term is precisely the move that
makes a technical panel trust everything else you said. It also pre-empts the question.

### 3.8 Cushion gas — the economics fact that reframes the whole problem

Roughly **half** of the gas in a porous storage site is **cushion gas**: permanently
immobilised inventory whose only job is to hold reservoir pressure high enough that the
working gas can be produced at rate. For hydrogen at ~$5/kg this is the single largest
capital item in a porous store, and it is why the economics module never prices the store
itself. The built module (`src/economics/voi.py`) goes further than the differential that
was originally specced: it reports a **dimensionless** ratio, so cushion gas, drilling and
facilities do not merely *cancel* — they never enter at all. The superseded differential
spec is in `Build_Plan.md` §Economics. Scale anchor from that doc, still unverified and
not to be quoted as a point value:
**~10,000 t working gas at ~$5/kg ≈ $50M inventory, so 1% annual loss ≈ $500k/yr.**

### 3.9 Cyclic operation — why the time axis is the interesting one

Seasonal storage means **inject through summer, withdraw through winter**. That is a
12-month period, and it is stamped through everything in this project:

- 6 months injection, 6 months withdrawal, **10 annual cycles** `[DATASET]`
- Output every 2 months → **60 timesteps** `[DATASET]`
- During injection the reservoir over-pressures above initial; during withdrawal it drops
  *below* initial. Our flux model clips the driving overpressure at zero, so **leakage is
  exactly zero throughout every withdrawal stage by construction** — fluid would flow the
  other way, which is not leakage (`src/leakage/labels.py:305`, asserted in
  `check_monotonicity()`).

This periodicity is also the trap that our own earlier result fell into — see §7.3. **The
annual cycle is simultaneously the physics, the demo's best visual, and the source of our
most important negative result.** That triple use is worth building the deck around.

---

## 4. The dataset, read as a geological object

Source: Mao, S., Carbonero, A., & Mehana, M. (2025). *Deep learning for subsurface flow: A
comparative study of U-Net, Fourier neural operators, and transformers in underground
hydrogen storage.* JGR: Machine Learning and Computation, 2, e2024JH000401.
<https://doi.org/10.1029/2024JH000401> · Data: <https://zenodo.org/records/14029514>
(CC-BY-4.0 / MIT), 12.38 GB, MD5 verified `6bc841f02ad3f40c9a8ef8ad187edf43`.

### 4.1 The domain

| Property | Value | Tag |
|---|---|---|
| Grid | 128 × 128 × **1** cells | `[DATASET]` |
| Extent | 7,680 m × 7,680 m | `[DATASET]` |
| Thickness | 100 m | `[DATASET]` |
| Cell | 60 m × 60 m × 100 m = 3.6×10⁵ m³ | `[DERIVED]` |
| Initial pressure | 197.2 bar | `[DATASET]` |
| Inferred depth | ~1,878 m (197.2 bar ÷ 0.105 bar/m hydrostatic) | `[ASSUMED]` — depth is never stated |
| Well | one central vertical well at cell (63,63) | `[DATASET]` (described only as "a central well"); location **confirmed empirically** — see below |
| Top / bottom boundaries | no-flow (sealed caprock and baserock) | `[DATASET]` |
| Side boundaries | outflow | `[DATASET]` |
| Simulations | 1,000 realisations of the same domain | `[DATASET]` |
| Timesteps | 60, one every 2 months, 10 annual cycles | `[DATASET]` |

**~1,878 m is a completely typical depleted gas reservoir depth**, which is a good sanity
line to deliver out loud — the assumption lands where a geologist would expect it.

**The 128 × 128 × 1 is a limitation you must state, not hide.** A single vertical layer
cannot resolve gravity override *within* the reservoir — the very buoyancy behaviour §3.6
says dominates hydrogen. What the simulations represent is effectively a vertically
averaged, areal view. The correct phrasing: *"this is a 2.5D areal model; we do not predict
3D reservoir maps, and `docs/FINDINGS.md` §10 says so explicitly."*

### 4.2 The rock

Measured across all 1,000 realisations from `outputs/site_suitability_features.csv`. **[OURS]**

| Quantity | Min | Median | Max |
|---|---|---|---|
| Mean porosity per realisation | 0.2523 | 0.2801 | 0.3084 |
| Within-realisation porosity σ | 0.0177 | 0.0264 | 0.0350 |
| Mean log₁₀ k (mD) per realisation | 1.006 | 1.461 | 1.879 |
| → geometric-mean permeability | **10.1 mD** | 28.9 mD | **75.6 mD** |
| Peak pressure per realisation | 249.9 bar | 275.9 bar | **293.8 bar** |
| Peak caprock margin (at 0.17 bar/m) | 0.431 | 0.645 | **0.792** |

Full-dataset cell-level permeability range: **1.03 – 738.8 mD** (`docs/FINDINGS.md` §5).
Permeability is in **millidarcy, not m²** — the normaliser takes log₁₀ before standardising
because the range spans 716×.

**Geological read:** ~25–31% porosity and tens of millidarcy is a good-quality but not
spectacular clastic reservoir — the kind of unit that hosts a real depleted gas field. This
is a plausible domain, not a toy.

### 4.3 The φ–k relationship, and the one artefact worth confessing

**[OURS] — measured, `docs/SITE_SUITABILITY.md` §3:**

```
                     poro_mean  poro_std  logk_mean  logk_std  caprock_margin_peak
poro_mean                 1.00      0.25       1.00      0.01                 0.12
poro_std                  0.25      1.00       0.24      0.97                 0.01
logk_mean                 1.00      0.24       1.00      0.00                 0.12
logk_std                  0.01      0.97       0.00      1.00                -0.02
caprock_margin_peak       0.12      0.01       0.12     -0.02                 1.00
```

`poro_mean` and `logk_mean` correlate at **r = 1.00**. In this dataset permeability was
generated from porosity by a fixed deterministic transform — they are the same underlying
quantity wearing two names.

**In real rock, φ and k do correlate — through Kozeny–Carman-type relations — but with one
to two orders of magnitude of scatter at any given porosity**, because k depends on pore
*throat* geometry, sorting, cementation and clay content, not just void fraction. A
perfectly deterministic φ–k transform is a synthetic-data artefact.

This has a direct engineering consequence we acted on: the suitability score uses
`poro_mean` **only**, because summing porosity and permeability terms would double-count
one signal (`src/site_suitability.py:83`, and the module docstring says exactly this).

**Say this on stage.** "We checked whether our two headline geological criteria were
independent. They correlate at 1.00, so we dropped one. A weighted score that
double-counted would have looked more sophisticated and been less correct."

### 4.4 Validations that passed **[OURS]**

From `docs/FINDINGS.md` §4 and `outputs/explore_report.json`:

- **Well location.** The paper says only "a central well." We located it empirically:
  pressure maximum during injection *and* minimum during withdrawal both land on cell
  (63,63), 0.71 cells from the grid centre. This matters — the paper attributes **24
  percentage points** of pressure accuracy to the distance-to-well input channel, so an
  incorrectly anchored distance map would have quietly destroyed the surrogate.
- **Cyclic indexing.** On injection steps, well pressure exceeds **100.0%** of the field;
  on withdrawal steps, **0.0%**. Exactly reproduces the paper's §5.8 description.
- **Architecture.** Our U-Net matches the paper's Table 1 weight counts to three figures
  (7.76M / 31.04M / 124.12M vs 7.7M / 31M / 124M) — checked **before** any training ran.
- **Storage precision.** float16 round-trip error verified against the source LMDB, with
  tolerances *derived from float16 resolution* rather than chosen to pass: pressure
  3.12e-2 bar against a 4.69e-2 limit, saturation 2.44e-4 against 7.32e-4. Pressure error
  is 0.027% of the peak excursion — ~300× smaller than the surrogate's own error, so it
  cannot affect any downstream result.

### 4.5 The undocumented third channel — a small find worth 20 seconds **[OURS]**

Both the Zenodo record and the upstream README describe each timestep value as a 2-tuple
`(pressure, saturation)`. **It is a 3-tuple.** We characterised the third channel across
timesteps and simulations (`docs/FINDINGS.md` §1):

- corr(aux, pressure) = **−0.993 to −0.999** at every timestep
- aux / (P − P_init) = **−1.17×10⁻⁴ per bar, constant across time** = 1.17×10⁻⁹ /Pa

That coefficient is a **compressibility**, the right order of magnitude for brine plus pore
compressibility. About 10% of its variance is not explained by pressure and tracks the H₂
plume; its sign flips between injection and withdrawal.

**We cannot name it definitively, so we don't.** It is preserved under a neutral name
(`aux_undocumented`) and is not used as a model target. This is a good 20-second story: it
shows we read the bytes rather than the description, and it shows restraint — we identified
its physical *units* and stopped there rather than guessing a label.

---

## 5. The pipeline, end to end

```
1,000 geological realisations (porosity φ, permeability k)
        │
        ▼
  U-Net surrogate  ──── 5 input channels: φ, k, time, cyclic index (+1/−1), distance-to-well
        │                7.76M params · trained on Kaggle T4 · 120 epochs · 4.23 h
        ▼
  predicted pressure + H₂ saturation fields  (128×128, per timestep)
        │
        ▼
  physics feature extraction → 41 scalars   (never raw maps: 2×128×128 = 32,768 columns
        │                                    would destroy interpretability)
        ▼
  + hypothesised fault realisation (position, permeability, length, width, orientation)
        │                          20 Monte-Carlo faults per simulation
        ▼
  XGBoost → P(elevated leakage 6 months ahead)  +  log-flux regression
        │
        ▼
  TreeSHAP attribution  ·  spatial risk map  ·  fault-ensemble sweep
```

### 5.1 Stage 1 — the U-Net surrogate

**What it does:** learns the map from static geology to the evolving flow field, so you
never have to run the simulator again for a new realisation.

**Why U-Net-Small (7.76M) and not U-Net-Large (124M):** the paper's own result gives the
escape route. U-Net-Small **with cyclic and distance channels** reaches 8.6% pressure error,
level with U-Net-Large's 8.61% at 124M parameters and 35 GB. Without those two channels,
Small degrades to 32.7%. **The input representation, not the parameter count, carries the
accuracy.** So a 7.7M model on a free T4 is a legitimate reproduction, not a compromise.
(`src/config.py:206`, `docs/FINDINGS.md` §6.) This is a genuinely good slide — it is a
result about *what to feed a model*, which generalises beyond this project.

**Result, held-out test set of 150 simulations never seen in training:**

| | Ours | Paper U-Net-**Small** | Paper U-Net-Large |
|---|---|---|---|
| Pressure rel. L2 | **0.1640** | **0.086** | 0.0861 |
| Saturation rel. L2 | **0.1101** | ~0.06–0.07 | 0.0577 |

**We are ~1.9× the paper's Small error. Say that number out loud.** It is a working
surrogate and a faithful implementation — the parameter counts match Table 1 exactly — but
it is *not* a reproduction of the paper's accuracy and must not be described as one.

**And we know why the curve stopped, which is the more impressive part.** Pressure fell
steeply to 0.186 by epoch 76, then oscillated between 0.19 and 0.22 for 44 more epochs;
neither learning-rate halving (epochs 50 and 100) broke through. So a longer run would not
help. Ranked suspects (`docs/FINDINGS.md` §8):

1. **Our own deviation — the shared two-head trunk.** The paper trains a *separate* model
   per state variable; we emit both from one two-channel head to halve training cost. The
   targets conflict: pressure is smooth, global and sign-flipping between stages;
   saturation is local with a sharp front. A shared trunk must compromise. **This is the
   experiment to run next, and naming your own shortcut as the top suspect is exactly the
   kind of thing judges remember.**
2. Batch 48 vs the paper's 128 — noisier gradients, and the LR schedule was tuned at 128.
3. Mixed precision; the paper reports consistent precision throughout.

### 5.2 Stage 2 — the leakage label, T3

The core equation. Put it on a slide **with units**; it's five symbols and it earns trust:

```
Q  =  k_f · k_rg(S_fault) · A_f / μ_H₂  ·  max(P_fault − P_init, 0) / L_caprock

     m²   ·  [–]          · m²  / Pa·s  ·         Pa               / m     =  m³/s
```

| Symbol | Meaning | Value / source |
|---|---|---|
| `k_f` | fault damage-zone permeability | sampled log-uniform 1e-15 – 1e-12 m² `[ASSUMED]` |
| `k_rg` | Corey gas relative permeability at the fault | computed from simulated saturation; `S_wr`=0.20, `S_gr`=0.05, `n_g`=2.0 `[ASSUMED]` |
| `A_f` | conduit cross-section = length × damage-zone width | length 200–2000 m, width 1–10 m, sampled `[ASSUMED]` |
| `μ_H₂` | hydrogen dynamic viscosity | 9.5e-6 Pa·s `[ASSUMED]`, mid-range for ~200 bar |
| `P_fault` | pressure at the fault trace | **from the simulated/predicted field — real physics** |
| `P_init` | initial reservoir pressure | 197.2 bar `[DATASET]` |
| `L_caprock` | vertical path length through the seal | 50 m `[ASSUMED]` |

Two consequences of the `max(…, 0)` clip, both intended and both asserted in code:

- **Withdrawal produces exactly zero leakage.** The field drops below initial pressure;
  fluid would flow the other way, which is not leakage.
- **A pressurised fault with no plume on it leaks nothing**, because `k_rg` is zero below
  residual gas saturation.

**Why overlaying a hypothetical fault is not circular** — this is *the* methods question and
the answer is clean: **the fault is not an input to the U-Net.** The U-Net predicts the flow
field from geology alone; the fault is introduced afterwards. So the system answers *"given
this fault hypothesis, how bad is it?"* — which supports Monte-Carlo over unknown fault
properties in milliseconds. That is a real capability, not a restatement of the simulator.
(`src/leakage/labels.py:30`.)

**The physics self-checks.** `python -m src.leakage.labels` runs six monotonicity assertions
and exits non-zero if any fail:

1. Flux increases with fault permeability
2. Flux increases with overpressure
3. Flux is exactly 0 during withdrawal
4. Flux is exactly 0 below residual gas saturation
5. A fault on the plume leaks more than one outside it
6. Corey endpoints: `k_rg(S_gr) = 0`, `k_rg(1 − S_wr) = 1`

**Slide-worthy line:** "If the label doesn't respond to its drivers in the physically
correct direction, every SHAP attribution built on it is noise. So it's an assertion in the
code, not a paragraph in a report."

### 5.3 Stage 3 — 41 features

Two rules govern feature extraction (`src/leakage/features.py:1`):

1. **Never feed raw maps to XGBoost.** Two 128×128 fields = 32,768 columns, which destroys
   the interpretability that is the entire reason for using a gradient-boosted model.
2. **The target is a forecast, not a description of the present.** Features observed at
   timestep t, labelled with flux at t+h. Labelling a row with its own timestep's flux
   would let XGBoost rediscover the label's arithmetic and score near-perfectly while
   predicting nothing.

The 41 features, by family:

| Family | Count | Examples |
|---|---|---|
| Pressure | 8 | `p_max_bar`, `p_p95_bar`, `p_well_bar`, `delta_p_bar`, `p_grad_max_bar_per_m`, `dp_dt_bar_per_year` |
| Plume | 9 | `s_max`, `hpv_total_m3`, `plume_area_m2`, `plume_max_radius_m`, `plume_front_speed_m_per_year`, `plume_centroid_offset_m` |
| Seal / boundary | 3 | `caprock_margin`, `boundary_saturation_max`, `boundary_hpv_fraction` |
| Geology (static) | 4 | `poro_mean`, `poro_std`, `logk_mean`, `logk_std` |
| Fault-conditional | 13 | `fault_p_bar`, `fault_s`, `fault_krg`, `fault_overpressure_bar`, `distance_plume_to_fault_m`, `fault_log10_perm_m2`, `fault_area_m2` |
| Operational | 4 | `timestep`, `cycle_number`, `cycle_index`, `step_in_cycle` |

**Table size:** 1,000 sims × 20 faults × 59 timesteps = **1,180,000 rows × 41 features**,
built in one pass in ~2 minutes with 12 workers. At the reported horizon (h=3), 1,140,000
rows are usable (rows whose label runs past the end of the simulation are dropped).

**Two features are vestigial and we said so** (`docs/FINDINGS.md` §9):
`boundary_hpv_fraction` and `boundary_saturation_max` are leftovers from the dropped T1
target and are near-zero everywhere. They should be removed. Naming dead code in your own
findings doc is cheap credibility.

### 5.4 Stage 4 — XGBoost, and the baselines that make its score mean something

Two models on the same feature table: a **classifier** for P(elevated leakage at t+h) and a
**regressor** for log₁₀ flux. Attribution via **exact TreeSHAP** using XGBoost's own
`pred_contribs` (the `shap` package 0.49 cannot parse xgboost 3.2's `base_score` — same
algorithm, no version conflict; `src/train_xgb.py:111`).

**"Elevated" is defined as the 90th percentile of non-zero fluxes**, computed per horizon so
class balance stays comparable across the sweep. This gives a **2.2% positive rate** at the
reported horizon. The threshold is a *quantile*, not an absolute m³/s value, because the
absolute scale is set by the assumed fault permeability and caprock thickness and therefore
carries no independent meaning. (The concrete value at h=3 is 1.733 m³/s — report it as a
derived scale, never as a physically calibrated leak rate.)

**Three controls are reported alongside every score:**

| Control | What it is | Score at h=3 |
|---|---|---|
| **Full model** | all 41 features | PR-AUC **0.9931** |
| **Weak baseline** | XGBoost on *two* features only: `p_max_bar`, `distance_plume_to_fault_m` | PR-AUC 0.1546 |
| **Persistence** | "next period looks like this period" — carry today's flux forward | PR-AUC **0.0218** |

**Splits are by simulation, never by sample**, at *both* the U-Net and XGBoost stages, and
disjointness is asserted at runtime — a simulation is never in one stage's training set and
another's test set. Splitting by sample would put timestep t in train and t+1 in test, which
leaks almost everything (`src/config.py:247`).

### 5.5 Stage 5 — the spatial risk map

`src/leakage/risk_map.py` answers the question the rest of the pipeline can't: not *"is this
fault dangerous"* but ***"where would a fault be dangerous here?"***

It sweeps a hypothetical fault across a 32×32 grid of candidate positions, scores each with
the trained classifier, and returns a heatmap in about a second.

Two design decisions worth a sentence each:

- **Fault properties are marginalised, not fixed.** Permeability, length, width and
  orientation are all unknown; holding them fixed would produce a map of one arbitrary
  fault, and a fixed orientation in particular *streaks* the result along that direction.
  Each cell is scored over `n_samples` random property draws and reduced (mean, or a high
  quantile for a worst-case view). The reduction is stated in the output.
- **The same property draws are shared by every cell**, so differences across the map come
  from *location alone*, not sampling noise. Without this a coarse grid looks speckled and
  the speckle gets mistaken for structure.

**Read it as:** *"if a fault existed at this location, how likely is elevated leakage one
horizon ahead?"* It is a **conditional** risk surface, not a prediction that faults exist
anywhere in particular — the simulations contain no faults at all. That is exactly the
question site screening asks. **This is the closest thing in the repo to the "leakage
probability heatmap" the original pitch (`Document 9.pdf`) promised — make sure the deck
connects those two explicitly.**

### 5.6 Module 1 — site suitability

`src/site_suitability.py` ranks all 1,000 realisations 0–100 on a weighted multi-criteria
score:

| Criterion | Weight | From | Direction |
|---|---|---|---|
| Capacity | 0.5 | mean porosity (storage volume / injectivity proxy) | higher is better |
| Seal risk | 0.3 | peak pressure vs. assumed caprock fracture pressure | higher is **worse** |
| Heterogeneity | 0.2 | within-realisation porosity σ | higher is **worse** |

All three weights are `[ASSUMED]` and exposed on the CLI (`--w-capacity` / `--w-seal` /
`--w-het`) so the weighting is a stated, sweepable choice rather than a buried constant.

**Why a weighted score and not clustering:** clustering was tried **first** and dropped.
KMeans over k=2..6 never beat silhouette **0.263** (the conventional floor for "real cluster
structure" is ~0.25). PCA puts 99.9% of variance in 3 components with **no gap** between
them. The population is a continuum along three continuous axes, not discrete site types —
and a weighted score is also what real CO₂/H₂ storage atlases actually use to screen
prospects. **The clustering code wasn't wrong; the premise was.**

**Robustness, checked before shipping:**

| Weight variant | Spearman ρ vs. default | Top-10 overlap |
|---|---|---|
| Equal weights (.34/.33/.33) | 0.912 | 7/10 |
| Capacity-only (1/0/0) | 0.730 | 5/10 |
| Seal-heavy (.3/.6/.1) | 0.800 | 6/10 |
| Drop heterogeneity (.6/.4/0) | 0.957 | 8/10 |

**The rule this produces, and it must be obeyed on stage:** report which *tier* or
percentile a site lands in. **Never say "site #468 is the best site."** Broad ordering is
robust (ρ 0.73–0.96); the exact top-10 shifts by 2–5 seats under re-weighting.

**And the honest limit, stated before anyone asks:** these are 1,000 synthetic realisations
of *one* domain, not 1,000 real-world locations. This ranks candidate **rock properties**,
not places on a map.

---

## 6. Every number, with provenance

Copy-paste source of truth for the deck. **If a number is not here, do not put it on a
slide without finding its source first.**

### 6.1 Headline results

| Claim | Value | Source file |
|---|---|---|
| Reported forecast horizon | 3 steps = **6 months** = half a storage cycle | `outputs/xgb_results.json` |
| Model PR-AUC (test) | **0.9931** | `outputs/xgb_results.json` |
| Model AUC (test) | 0.9998 | `outputs/xgb_results.json` |
| Persistence PR-AUC | **0.0218** | `outputs/xgb_results.json` |
| Gain over persistence | **+0.9714 PR-AUC** | `outputs/xgb_results.json` |
| Weak 2-feature baseline PR-AUC | 0.1546 | `outputs/xgb_results.json` |
| Model log-flux R² | 0.9711 | `outputs/xgb_results.json` |
| Persistence log-flux R² | **−0.7642** (worse than predicting the mean) | `outputs/xgb_results.json` |
| Positive-class rate | 2.2% | `outputs/xgb_results.json` |
| Test rows | 171,000 (150 sims × 20 faults × 57 steps) | `outputs/xgb_results.json` |
| Usable rows at h=3 | 1,140,000 | `outputs/xgb_results.json` |
| Full feature table | 1,180,000 rows × 41 features | `README.md`, `src/leakage/features.py` |

### 6.2 The horizon sweep — the honesty table

| Horizon | Months | Cycle phase | Model PR-AUC | Persistence PR-AUC | Gain |
|---|---|---|---|---|---|
| 1 | 2 | different | 0.9949 | 0.4224 | +0.5725 |
| **3** | **6** | **different** | **0.9931** | **0.0218** | **+0.9714** |
| 6 | 12 | **SAME** | 0.9975 | 0.9918 | +0.0057 |
| 12 | 24 | **SAME** | 0.9960 | 0.9758 | +0.0202 |
| 30 | 60 | **SAME** | 0.9918 | 0.9125 | +0.0792 |

Source: `outputs/xgb_horizon_sweep.json`, `docs/FINDINGS.md` §7.

### 6.3 Does the surrogate's error matter?

Risk model trained **once** on simulator features and **never retrained**, then scored on
both field sources. Labels come from the simulator in both arms (asserted at runtime), same
leak thresholds, rows aligned on `(sim_id, fault_id, timestep_observed)` — so only surrogate
error can explain the difference. 150 held-out simulations, 15,911 aligned rows.

| Field source | PR-AUC | AUC | log-flux R² | RMSE |
|---|---|---|---|---|
| Simulator | 0.9941 | 0.9999 | +0.9714 | 0.739 |
| **U-Net surrogate** | **0.9842** | 0.9996 | **+0.9200** | **1.236** |
| Cost of using the surrogate | **−0.0099** | −0.0003 | −0.0514 | +0.497 |

**The surrogate retains 99.0% of the simulator's PR-AUC.** That is the number that justifies
the entire architecture. But **magnitude estimation degrades materially**: log-flux RMSE
0.739 → 1.236, i.e. from predicting flux within ~5.5× to within ~17×.

**Therefore: screening, not quantitative leak-rate prediction.** The project committed to
that framing before the measurement; now it has evidence for it.

**Which features absorb the error** (`outputs/source_comparison.json`): 15 of 41 features
are **bit-identical** — geology and fault properties never pass through the surrogate. The
distortion concentrates in **time-derivative** features, because differencing amplifies
field noise:

| Feature | mean abs error / scale |
|---|---|
| `plume_front_speed_m_per_year` | 0.493 |
| `dp_dt_bar_per_year` | 0.186 |
| `hpv_rate_m3_per_year` | 0.178 |
| `plume_centroid_offset_m` | 0.122 |
| `fault_delta_p_bar` | 0.121 |

**The punchline:** the top-attributed features (`fault_overpressure_bar`, `fault_p_bar`,
`fault_log10_perm_m2`) are among the ones the surrogate **cannot corrupt** — which is
precisely *why* PR-AUC barely moves. That's a mechanistic explanation of a result, not just
a result. Put it on the slide.

### 6.4 Feature attribution (XGBoost gain, `outputs/xgb_results.json`)

| Rank | Feature | Gain | Physical reading |
|---|---|---|---|
| 1 | `fault_overpressure_bar` | 428.0 | the driving force in Darcy's law |
| 2 | `fault_p_bar` | 334.3 | absolute pressure at the fault trace |
| 3 | `fault_delta_p_bar` | 269.7 | pressure above initial |
| 4 | `fault_log10_perm_m2` | 151.6 | the conduit's own permeability |
| 5 | `fault_width_m` | 41.9 | damage-zone width → conduit area |
| 6 | `fault_krg` | 40.9 | is the hydrogen mobile at all? |
| 7 | `fault_length_m` | 31.8 | conduit area |
| 8 | `fault_area_m2` | 29.9 | conduit area |
| 9 | `fault_s` | 22.7 | saturation at the fault |
| 10 | `fault_logk` | 15.4 | host-rock permeability at the fault |

**Read this as a validation, not a discovery, and say so.** The ranking recovers exactly the
terms of the Darcy equation in roughly the right order — overpressure, then permeability,
then area, then mobility. That is the model *agreeing with the physics we wrote down*, which
is what you want from an interpretability check.

> **Caveat you must volunteer** (`docs/FINDINGS.md` §7): the model is given the fault's
> permeability and area *exactly*, and those are multiplicative constants in the label.
> Real fault properties are uncertain by orders of magnitude. This is why the honest
> framing is *"given this fault hypothesis, how does risk evolve?"* and why Monte-Carlo
> over the hypothesis space — which is what the dashboard and risk map do — is the actual
> product.

### 6.5 Compute and engineering

| Claim | Value | Source |
|---|---|---|
| U-Net training | Kaggle T4, 120 epochs, **4.23 h**, 127 s/epoch, batch 48 | `docs/FINDINGS.md` §8 |
| Local CPU training | ~4 h **per epoch** on 16 cores — no local GPU path worth taking | `README.md` |
| Dataset download + convert (Kaggle) | **6.6 min** total: 4.6 min download at up to 51 MiB/s, 66 s conversion | `docs/SITE_SUITABILITY.md` §1 |
| Feature table build | ~2 min, 12 workers | `README.md` |
| XGBoost sweep + SHAP | ~10 min | `README.md` |
| Risk map (32×32) | ~1 s | `src/leakage/risk_map.py` docstring |
| Deployable frontend | one self-contained HTML file, **no server, no build step, no dataset** | `docs/FRONTEND.md` |

### 6.6 Numbers to verify before quoting

**Do not put these on a slide until checked.** Listed here so nobody assumes they're clean.

1. **"Multi-hour reservoir simulation."** We never timed tNavigator ourselves. The claim is
   inherited framing. Either cite the paper's reported simulation cost with a page
   reference, or soften to "a full reservoir simulation, which is orders of magnitude
   slower than a forward pass." Do not invent a number of hours.
2. **"Sub-second screening."** True for U-Net inference plus feature extraction plus an
   XGBoost call, and the frontend times every recompute with `performance.now()` and prints
   it — but if you want a specific millisecond figure, measure it and show the on-screen
   readout rather than asserting it.
3. **Peak caprock margin.** `docs/FINDINGS.md` §3 pairs peak pressure 293.8 bar (full
   dataset) with margin 0.759 — but 0.759 corresponds to `outputs/explore_report.json`'s
   289.9 bar over a **100-simulation sample**. The full-1,000 value in
   `outputs/site_suitability_features.csv` is **0.792**. Quote **293.8 bar → margin 0.79**,
   or quote the 100-sim pair together. Don't mix them.
4. **Any $/kg, $/workover, or ROI figure.** The economics module now exists
   (`src/economics/`) and this restriction is unchanged — the module deliberately produces
   no currency figure, because every route to one runs through a leak rate nobody can
   calibrate. Quote the **dimensionless** efficiency ratio (VOI/VOPI = 0.9974 screened,
   0.00 unaided), and the one money figure we own end to end: our own compute, 0.652
   vCPU-seconds per screening pass. The $/kg and workover-cost entries are still marked
   UNVERIFIED in `src/economics/assumptions.py`, which **refuses to give them a point
   value** — the register raises on import if you try. See `Economics_and_impact.md`.
5. **Working-gas tonnage.** Derivable from `hpv_total_m3` × H₂ density, but reservoir
   temperature is never stated in the paper, so the density is an assumption. If you want a
   tonnage on stage, derive it live from stated assumptions or leave it out.

---

## 7. The three negative results — and why they are the strongest slides

Most hackathon decks have no negative results, which is precisely why yours will land. Give
these real slide time; do not bury them in a "limitations" footer.

### 7.1 T1 is dropped — 0 out of 1,000

The one leakage signal genuinely present in the data was **lateral containment loss**: the
paper states outflow boundaries on the sides, so hydrogen reaching the domain edge really
does leave. The build plan made this an explicit **go/no-go checkpoint** *before* the work
was done, precisely because it might not happen.

It doesn't happen.

| Quantity | Value |
|---|---|
| Simulations reaching the boundary | **0 / 1000** |
| Highest boundary saturation anywhere | 0.00390 |
| Threshold for mobile H₂ | 0.05 |
| Largest equivalent plume radius | ~1,454 m |
| Domain half-width | 3,840 m |
| Fraction of the way to the boundary | **37.9%** |

The plume peaks at **6.06 km²** after ten years (from 0.80 km² at the first step) and stays
well inside the domain. Peak boundary saturation is **13× below** threshold — not a marginal
call a different threshold would rescue.

**The line:** *"We did not lower the threshold until it produced labels."*

**Geological interpretation to add:** a plume reaching only 38% of the way to the boundary
after a decade of cycling is actually the *expected* behaviour for a well-contained store —
each withdrawal pulls the plume back, and residual trapping plus the cyclic reversal keeps
it compact. The negative result is physically sensible, not a data problem.

### 7.2 The binary caprock label is an artefact of our own assumption

| Fracture gradient | P_frac at ~1,878 m | Peak margin | Binary label |
|---|---|---|---|
| 0.15 bar/m | 281.7 bar | 1.097 | some exceedances |
| **0.17 bar/m** (our default) | 319.3 bar | 0.759–0.792 | **identically zero** |
| 0.20 bar/m | 375.6 bar | 0.519 | identically zero |

**Flipping one assumed constant flips the label from "never happens" to "sometimes
happens."** A binary caprock-breach label is therefore an artefact of our own assumption,
not a finding, and we do not report one.

The **continuous** margin `(P_max − P_init)/(P_frac − P_init)` is monotone in pressure
*regardless* of the gradient, so it is kept as a model feature and as the seal-risk
criterion in the suitability score.

**The line:** *"We asked what happens if we're wrong about the one number we made up. The
answer changed the label completely — so we don't report that label."*

### 7.3 We withdrew our own headline number

The original run used horizon 6 = one full storage cycle, so the observed and labelled
timesteps sat at the **same phase** of consecutive annual cycles. It scored AUC 0.9999 and
looked spectacular.

Then we ran the persistence baseline. **Persistence — literally copying today's value
forward — scored 0.9918 PR-AUC at that horizon.**

Every horizon that is a multiple of 6 lands at the same cycle phase, and persistence scores
0.91–0.99 at *all* of them. Horizon length does not fix it — even at five years persistence
reaches 0.9125. **Phase does.**

At horizon 3 (half a cycle), persistence collapses to **0.0218 PR-AUC — below the 2.2% base
rate.** It is actively *anti*-correlated, because half a cycle later injection has become
withdrawal and high flux has become zero. Its log-flux R² is **−0.7642**, worse than
predicting the mean.

Consequences, all shipped in code:

- Horizon 3 is the reported task — and it's also the operationally meaningful one:
  ***"will risk be elevated at the next stage change?"***
- The earlier headline is **withdrawn**.
- `train_xgb.py` now selects the shipped model by **largest gain over persistence**, not by
  longest horizon, and **flags any horizon where persistence exceeds 0.9 PR-AUC as "not a
  forecasting task."** The lesson is enforced by the tooling, not by memory.

**The line, and it should be the emotional peak of the deck:** *"Our best number was mostly
the reservoir's annual periodicity. We found that ourselves, threw it away, and wrote the
check into the training script so we can't make the mistake again."*

---

## 8. Visuals: what to draw, from what data, to prove what

Every visual below is buildable from a file that exists in this repo. **Priority column: P0
= the deck fails without it.**

| # | Visual | Priority | Data source | The one claim it makes |
|---|---|---|---|---|
| V1 | **Geological cross-section hero** | **P0** | hand-drawn SVG from `src/config.py` constants | "Here is the physical system, with our real numbers on it" |
| V2 | **The pipeline diagram** | **P0** | the ASCII block in `README.md:11` | "Geology → fields → features + fault → risk. The fault enters *after* the surrogate." |
| V3 | **Horizon-sweep paired bars** | **P0** | `outputs/xgb_horizon_sweep.json` | "Our score only means something where persistence fails" |
| V4 | **Simulator vs surrogate** | **P0** | `outputs/source_comparison.json` | "99.0% PR-AUC retention — screening survives, magnitude doesn't" |
| V5 | **Storage Atlas scatter** | P1 | `outputs/site_suitability_ranking.csv` (1,000 rows) — already live in `app/web/index.html` | "1,000 candidates screened, and the weighting is a knob you can turn" |
| V6 | **Breathing plume / cycle ribbon** | P1 | live in `app/web/index.html` — ⚠️ currently a labelled mockup | "Storage breathes on a 12-month rhythm" |
| V7 | **φ–k crossplot, r = 1.00** | P1 | `outputs/site_suitability_features.csv` | "We checked our criteria for independence and dropped one" |
| V8 | **Spatial leakage-risk heatmap** | P1 | `src/leakage/risk_map.py` (needs the dataset) | "Where would a fault be dangerous *here*?" — the promised heatmap, delivered |
| V9 | **Darcy + Corey equation panel** | P1 | `src/leakage/labels.py` | "The label is physics we wrote down, not a black box" |
| V10 | **Feature attribution bars** | P1 | `outputs/xgb_results.json` → `importance_gain` | "The model rediscovered Darcy's law" |
| V11 | **T1 null-result diagram** | P2 | `outputs/explore_report.json` | "0/1000. We measured and killed a target." |
| V12 | **Provenance chip legend** | P2 | `src/config.py` tag taxonomy | "Every number on this deck carries its source" |
| V13 | **Where hydrogen goes, ranked** | P2 | `Data_sources_research.md` §3 | "We model the actionable path, not the biggest one" |

### V1 — the geological cross-section (build this one carefully; it carries the geology)

Vertical section, ground surface at top, annotated with **real values from `src/config.py`**:

```
  ── ground surface ─────────────────────────────────────────────────────
        │
        │  overburden  ~1,828 m          [ASSUMED depth, from hydrostatic]
        │
  ══════╪═══════════ CAPROCK ═══════════════════════════╪═══════════════
        │            50 m  [ASSUMED]                     ║  ← fault plane
        │            sealed: no-flow in the simulation   ║    cutting the seal
        │            P_frac = 319.3 bar @ 0.17 bar/m     ║    k_f: 1e-15…1e-12 m²
  ──────┼────────────────────────────────────────────────╫───────────────
        ▼   ░░░░▒▒▓▓███ H₂ PLUME ███▓▓▒▒░░░░             ║   RESERVOIR
      well      (pools at the top — buoyancy)            ║   100 m thick
        │   φ 0.25–0.31 · k 1–739 mD · P_init 197.2 bar  ║   7,680 m across
  ──────┴────────────────────────────────────────────────╨───────────────
                            baserock (no-flow)
```

Annotations to include, because each one is a talking point:
- **Peak overpressure: 293.8 − 197.2 = +96.6 bar** — that's the danger variable
- Caprock margin at peak: **0.79** — "we got to 79% of the assumed fracture pressure"
- Plume max equivalent radius **1,454 m** vs domain half-width **3,840 m** (the T1 story)
- The fault as a **vertical plane piercing the seal** — this is the entire physics argument
  made in one picture (`docs/FRONTEND.md` design decision #2)

**Make an inject/withdraw variant** — plume large + red pressure halo, vs plume retracted +
blue — and either animate or show side by side. That single toggle communicates cyclic
storage faster than any sentence.

### V3 — the horizon-sweep chart (the most important chart in the deck)

Grouped bars, 5 horizon groups, two bars each (model PR-AUC, persistence PR-AUC). Shade the
three same-phase horizons (6, 12, 30) in a "disqualified" grey and annotate:

> *"At any horizon that is a whole number of storage cycles, copying today's value already
> scores ~0.99. A high score there measures the reservoir's annual periodicity, not
> forecasting skill."*

Highlight horizon 3 in the accent colour with the gain callout **+0.9714**.

**This chart is the deck.** Everything else supports it.

### V8 — the spatial risk map

Regenerating this needs the converted dataset (12.38 GB — it is **not** in the repo). Two
options:

- **Best:** run `src/leakage/risk_map.py` on Kaggle where the converted arrays already
  exist as a kernel output (see `docs/SITE_SUITABILITY.md` §1 for the pattern — attach the
  previous kernel's output as an input, no re-download). Export a PNG.
- **Fallback:** show the Streamlit dashboard's "Where would a fault be dangerous?" panel
  (`app/dashboard.py:315`) as a recorded screen capture, and say it's a recording.

Overlay the plume outline and the well. **The expected geological story — verify before
asserting it — is that the hotspot sits on the plume front near the pressure ridge**, i.e.
where mobile hydrogen and overpressure coincide, which is exactly what the Darcy × Corey
product predicts. If the map shows that, it is a beautiful validation slide. If it doesn't,
say what it does show.

### General rules for every chart

- **Provenance chip on every number**: `[DATASET]` / `[DERIVED]` / `[ASSUMED]`. This is the
  design system, not decoration (`docs/FRONTEND.md` decision #4).
- **Colormap discipline**: viridis for saturation/hydrogen, inferno for pressure — matching
  what `app/dashboard.py` already uses. A legend colour and a UI colour meaning the same
  thing is free coherence.
- **Never a chart without its baseline.** Every model score gets its persistence bar beside
  it. That's the whole brand.
- Wide tables and diagrams must scroll inside their own container, never the page.

---

## 9. Deck structure and narrative arc

**The arc:** *Big problem → the thing that kills sites → nobody can compute it fast enough →
we made it fast → here's proof it's real → here's proof we checked ourselves → here's what
it can't do → here's what's next.*

The self-audit is not an appendix. It is **Act III**, and it is the reason to believe Acts I
and II.

### 5-minute version (typical hackathon pitch slot)

| # | Slide | Time | Content |
|---|---|---|---|
| 1 | **Hook** | 0:20 | Hydrogen is how you store a season of renewables. The only containers big enough are old gas fields. What ruins one is a fault you didn't know about. |
| 2 | **The geology** | 0:50 | **V1 cross-section.** Reservoir, caprock, plume pooling by buoyancy, fault piercing the seal. Two failure modes: capillary breakthrough (unlikely for H₂) and **pressure exceeding fracture pressure** (the one we model). |
| 3 | **Why it's unsolved** | 0:30 | Fault permeability is uncertain over **three orders of magnitude**. The honest question is a Monte-Carlo over thousands of hypotheses. A simulator can't do thousands. |
| 4 | **The system** | 0:45 | **V2 pipeline.** The load-bearing sentence: *the fault is not an input to the U-Net* — so one field prediction re-scores against thousands of faults in milliseconds. |
| 5 | **The physics label** | 0:30 | **V9.** Darcy × Corey, five symbols with units. "Leakage needs overpressure **and** mobile hydrogen. Both, or nothing — and it's asserted in code." |
| 6 | **Does it work** | 0:45 | **V3 horizon sweep.** PR-AUC 0.9931 vs persistence 0.0218. Then immediately: "and here's why three of these five horizons are meaningless." |
| 7 | **Does the shortcut cost anything** | 0:30 | **V4.** 99.0% PR-AUC retention. *"Screening survives. Magnitude doesn't — so we claim screening."* |
| 8 | **What we caught ourselves on** | 0:40 | 0/1000 on T1. The withdrawn headline. The check now written into the training script. |
| 9 | **Live demo** | 0:30 | The weight toggle reshuffling 1,000 sites, with the latency readout on screen. |
| 10 | **Honest close** | 0:20 | What's real, what's next, one ask. |

### 10-minute version — insert after slide 5

| Slide | Content |
|---|---|
| **The data** | 1,000 tNavigator simulations, 12.38 GB, MD5-verified. **And the undocumented third channel** — we measured its compressibility and declined to name it. |
| **The rock** | φ 0.25–0.31, k 1–739 mD, ~1,878 m depth. **V7:** φ and k correlate at r = 1.00, so we dropped one criterion rather than double-count. |
| **Site screening** | **V5 Storage Atlas.** 1,000 candidates ranked. Clustering was tried and dropped (silhouette 0.263) — a continuum, not discrete types. Weights are `[ASSUMED]`; sensitivity ρ 0.73–0.96; **report tiers, not "site #468."** |
| **Where, not just whether** | **V8 risk map.** The conditional risk surface. Fault properties marginalised, not fixed. |
| **What we deliberately did not build** | Economics — scoped as a *differential*, so cushion gas and drilling cancel. `Build_Plan.md` §Economics. Presented as a spec, not a result. |

### Slide-writing rules for this project

1. **Every model number appears with its baseline in the same visual field.** No exceptions.
2. **Every assumed constant is visibly tagged.** If a slide has an assumption and no chip,
   it's not finished.
3. **State the limitation before the judge does.** The pre-emptive version reads as rigour;
   the reactive version reads as damage control. Same sentence, opposite effect.
4. **Never a superlative you can't source.** No "state-of-the-art", no "industry-leading",
   no invented comparison to "traditional monitoring." Real sites already run downhole
   gauges, DTS/DAS, integrity logging and soil-gas sampling — HyLeakAI is a forecasting
   layer *on top of* that stack, not a replacement for a strawman (`Build_Plan.md` §Economics).
5. **Say the ~1.9× surrogate gap out loud.** Somebody will find it in the docs. Getting
   there first converts a weakness into evidence of honesty.

---

## 10. Live demo script

The deployable frontend is `app/web/index.html` — **one self-contained file, no server, no
build step, no dataset, no external requests.** It opens straight from disk if venue Wi-Fi
dies. That resilience is itself worth one sentence.

Deployment: GitHub Pages via `.github/workflows/pages.yml` on every push to `main`. Needs
one manual step that cannot be done from code — **Settings → Pages → Source → GitHub
Actions** — after which the site is at `https://sonil15.github.io/HyLeakAI/`. Fallbacks:
drag `app/web/` onto Netlify Drop, or `npx vercel deploy app/web`.

```bash
open app/web/index.html
```

### ⚠️ Read this before demoing — what is real on that page

| Panel | Status | Source |
|---|---|---|
| **1. Storage Atlas** | ✅ **Real** | All 1,000 rows of `outputs/site_suitability_ranking.csv`, embedded. Real scores, real ranks. The weight toggle re-scores live with the same formula as `src/site_suitability.py`. |
| **2. Breathing reservoir** | ⚠️ **Mockup, both modes** | Procedural stand-in fields. Correct *qualitative* behaviour, **not model output** — even in Live model mode, this visual is illustrative, scaled to match the live plume summary. |
| **3. Risk / attribution** | ⚠️ **Mockup in Preview** · ✅ **Real in Live model** | Preview: real feature names from `outputs/shap_features.json`, invented magnitudes, layout only. Live model: calls the deployed FastAPI service (`api/`) and shows genuine U-Net + XGBoost risk score and SHAP attribution — confirmed in `test_results/judge-live-production-e2e-2026-08-12.md`. |

**The page states this on itself** — a per-panel badge (the risk badge reads "Preview
values · illustrative" or "Live API · U-Net surrogate + XGBoost" depending on mode) and a
footer naming exactly which data is real. **Do not remove those badges, and do not demo
panel 2 (or panel 3 in Preview mode) without saying "this panel is a mockup" in the same
breath.** If a judge spots an undisclosed mock, every real number in the deck becomes
suspect. If *you* disclose it, the badges become evidence of the same discipline the rest
of the deck claims.

### The 60-second demo

1. **Open on the Storage Atlas.** "1,000 geological realisations, scored on capacity against
   seal risk. Every point is real output."
2. **Hit the weight toggle.** The ranking reshuffles live. *"Those weights are assumptions —
   we tagged them `[ASSUMED]` in the config. Here's what happens when you disagree with us.
   The tiers hold; the exact top-10 moves by two to five seats. So we report tiers."*
   **This is the demo moment** — it converts a footnote caveat into the thing they remember.
3. **Point at the latency readout.** Every recompute is timed with `performance.now()` and
   printed. "Sub-second isn't a claim in a README; it's on screen."
4. **Scroll to the reservoir slab.** *"This panel is a labelled mockup — the geometry and the
   cycle behaviour are right, the fields are procedural stand-ins. The real version needs a
   ~2 MB-per-simulation sprite-sheet export that's specced in `docs/FRONTEND.md` and is the
   next thing we build."* Then use it to **narrate the physics**: the plume breathing on the
   cycle ribbon, the fault plane piercing the seal.

### The local research dashboard — know when *not* to use it

`app/dashboard.py` (Streamlit) has the genuinely real panels — risk trajectory, fault-ensemble
sweep, spatial risk map, SHAP attribution — but it needs `torch`, `xgboost` and the converted
**12.38 GB** dataset, and calls `st.stop()` when `data/states.npy` is absent. **It cannot be
deployed and will not run on a laptop that hasn't done the full download.** If you want its
panels on stage, use a **screen recording** and say it's a recording.

---

## 11. Q&A bank — hostile questions and honest answers

### On the data and labels

**"So you don't actually have any leakage data."**
Correct, and neither does anyone else — that's the premise. No public dataset contains
hydrogen leakage measurements; UHS has a handful of pilots worldwide and none publish
continuous monitoring. Our features are real physics from 1,000 published tNavigator
simulations. Our leakage label is a semi-analytical Darcy flux through a hypothetical fault,
and we label it as derived everywhere it appears. What we're claiming is a screening tool,
not a calibrated leak-rate predictor.

**"Isn't your label circular? You compute flux from pressure and then predict it from pressure."**
At the same timestep it *would* be — the label is a closed-form function of quantities in the
feature vector. Which is exactly why we don't do that. The task is a **forecast**: features
at t, label at t+6 months. The only learning content is how the fields evolve, and we proved
that's a real task by showing persistence scores 0.0218 there. We also documented this exact
trap in `docs/FINDINGS.md` §7 before anyone asked.

**"You give the model the fault permeability, which is a multiplicative constant in your own label."**
Yes, and it's the top-4 attributed feature as a result — we say so in the findings doc. The
honest framing is that this answers *"given this fault hypothesis, how does risk evolve?"*
Real fault properties are uncertain by orders of magnitude, which is why the product is the
**Monte-Carlo over the hypothesis space** — 20 fault realisations per simulation in training,
and a risk map that marginalises fault properties at every location rather than fixing them.

**"Your labels are synthetic, so your model just learned your own equation."**
Partly, and we measured how much. The two-feature weak baseline (`p_max`,
`distance_plume_to_fault`) gets PR-AUC 0.155, so the answer isn't trivially in the pressure
field. And the equation's inputs at *time t+6 months* aren't known at time t — that's the
part that has to be learned, and it's the part persistence fails at.

### On the models

**"Your U-Net is 1.9× worse than the paper. Why should I trust the rest?"**
Because we measured it and told you. Our parameter counts match the paper's Table 1 exactly,
so it's a faithful implementation; the accuracy gap is real and we ranked the causes. The top
suspect is our own deviation — we use one two-headed trunk to predict pressure and saturation
together, where the paper trains separate models per variable. Pressure is smooth, global and
sign-flipping; saturation is local with a sharp front. A shared trunk must compromise. That's
the next experiment. And critically, we measured whether the gap *matters*: it costs 1% of
PR-AUC on the risk screening task.

**"PR-AUC of 0.99 sounds too good."**
It should. That reaction is why we report the persistence baseline next to every score.
Three of our five horizons are meaningless for exactly that reason — persistence scores
0.91–0.99 at any horizon that's a whole number of storage cycles, because the fields repeat
annually. We withdrew our own earlier 0.9999 headline over this. The one we report is at a
half-cycle horizon where persistence collapses to 0.0218, *below* the 2.2% base rate.

**"Why XGBoost and not a neural network / GNN / PINN?"**
Interpretability is the point of that stage. Exact TreeSHAP gives per-prediction attribution
in physical units, and the attribution ranking recovers Darcy's law — overpressure, then
permeability, then area, then mobility — which is a check on the whole pipeline. It's also
2 MB and runs in milliseconds, so a Monte-Carlo over thousands of fault hypotheses is free.
The original pitch proposed LSTMs, GNNs and PINNs; we scoped to what the available data
could actually support.

**"Why is your grid only one cell thick?"**
It's the published dataset's geometry, not our choice. And it's a real limitation we state:
128×128×1 cannot resolve gravity override *within* the reservoir, which is the dominant
hydrogen transport mechanism. This is an areal, vertically-averaged model. `docs/FINDINGS.md`
§10 explicitly lists "we predict 3D reservoir maps" as a claim this project will not make.

### On the geology

**"How do you know the reservoir depth?"**
We don't — it's never stated. We infer ~1,878 m by assuming the reservoir is initially at
hydrostatic pressure, which is standard for a depleted-then-repressurised gas reservoir,
using a 0.105 bar/m brine gradient. It's tagged `[ASSUMED]` in `src/config.py:137` and it's
only used for the caprock fracture criterion. It lands at a typical depleted-gas-reservoir
depth, which is a weak but real sanity check.

**"Your fracture gradient is made up."**
It is, and we swept it. 0.15 / 0.17 / 0.20 bar/m. **Flipping that one constant flips the
binary caprock-breach label from "never happens" to "sometimes happens"** — so we don't
report a binary breach label at all. We report the continuous margin, which is monotone in
pressure regardless of the gradient. That sweep is in `docs/FINDINGS.md` §3.

**"Caprock capillary breakthrough is the least likely leak path. Why model the seal?"**
Agreed, and we say so unprompted — the ranked pathway list puts caprock breakthrough last,
behind cushion gas, residual trapping, dissolution and microbial consumption. We model the
**fault-conduit** path because it's the *actionable* one: you can de-rate injection pressure
or not select the site. It's also the one with a safety and permitting consequence rather
than only an inventory consequence.

**"What about fault reactivation and induced seismicity?"**
Not modelled, and it's the most important geological gap. Raising pore pressure lowers
effective normal stress and can slip a critically stressed fault, which transiently raises
its permeability — and cyclic storage applies exactly that loading ten times a decade. Our
pressure-based caprock margin is a screening proxy for the same underlying quantity. Proper
Mohr-Coulomb reactivation analysis needs a stress tensor and fault orientations we don't
have, and it's named future work.

**"What about legacy wells? You said they're the most likely leak path."**
They are, and we model a fault instead — because the dataset has neither, and a fault gives
us a *spatial* hypothesis to sweep, which produces the risk map. The Darcy conduit model
transfers almost directly to a leaky well: swap the damage-zone cross-section for an annulus
area and the equation is the same. That's a genuinely small change and a good next step.

**"Your porosity and permeability correlate at 1.00. Real rock doesn't do that."**
Correct, and we caught it. In this dataset permeability is generated from porosity by a
deterministic transform. Real rock correlates through Kozeny–Carman-type relations but with
one to two orders of magnitude of scatter, because permeability depends on pore-throat
geometry, sorting and cementation, not just void fraction. We acted on it: the suitability
score uses porosity only, because summing both would double-count one signal. It also means
we can't claim the model learned anything about porosity–permeability structure.

### On scope and honesty

**"The original proposal had four modules. How many did you build?"**
Two and a half, and the README has a status table saying exactly which. Module 2 (leakage
prediction) is built at a narrower scope. Module 1 (geological intelligence) has a working
prototype with a live frontend. Module 3 (dashboard) is partial — one deployable frontend
whose risk panel is real in Live model mode but whose reservoir visual is still a labelled
mockup, plus one local research tool that can't be deployed. Module 4 (economics) is built
for the finals, but not as Document 9 asked: it returns no ROI, because an ROI needs a leak
rate and no ground truth for one exists anywhere. It computes Value of Information instead —
20,000 screened fault hypotheses capture 0.9974 of the available decision value, two exact
simulator runs capture 0.00. We think an accurate status table beats four half-claims.

**"Two of your three frontend panels are fake."**
Only in Preview mode, and it's labelled — a badge per panel and a footer naming exactly
what's real. The Storage Atlas runs on all 1,000 rows of real output in both modes. Switch
to **Live model** and the risk/attribution panel calls our deployed FastAPI service and
shows genuine U-Net + XGBoost output — see `docs/PRODUCT_API_PLAN.md` and the production
smoke tests in `test_results/`. The reservoir visual is still illustrative in both modes;
making that real too is a demo pack (~24 held-out simulations exported as quantised PNG
sprite sheets, ~2 MB each, removing the 12.38 GB dependency from the deployed site
entirely). The arithmetic and the plan are in `docs/FRONTEND.md`. Estimated half a day plus
one Kaggle run.

**"What's the actual novelty here?"**
Three things. First, decoupling the fault from the surrogate, so one field prediction serves
thousands of fault hypotheses — that's what makes Monte-Carlo screening tractable. Second, we
measured how much surrogate error propagates into the risk estimate, with the risk model
trained once on simulator features and never retrained, which is the actual deployment
situation — and got 99.0% PR-AUC retention. Third, and honestly the one we'd defend hardest:
a methodology where every score ships with a baseline that could invalidate it, and the
tooling refuses to report horizons where that baseline wins.

**"If I gave you real data tomorrow, what breaks?"**
The label, entirely — and that's the point of building it as a swappable module. The
features are geology and flow-field descriptors that transfer directly. The surrogate would
need retraining on the new geology. The XGBoost stage would be retrained on real observed
leakage instead of our derived flux, and at that point the assumed constants (fault
permeability range, caprock thickness, viscosity) stop being assumptions and become fitted
or measured. The architecture is designed for that swap; the physics self-checks would still
apply as sanity constraints.

**"What would you do with another week?"**
In order, and it's written down in the README: make the frontend's reservoir and risk panels
real via the demo-pack export; derive an explicit safe-injection-pressure limit from the
caprock margin feature that already exists (that closes most of the remaining gap in module
2); build the economics differential; and run the separate-heads U-Net experiment to test
our top suspect for the accuracy gap.

---

## 12. Design system for the deck

Inherit it from the frontend so the deck and the product look like one thing. Thesis, from
`docs/FRONTEND.md`: **an instrument, not a dashboard.**

### Palette (from `app/web/index.html`, sampled from the scientific colormaps the pipeline uses)

| Token | Light | Dark | Meaning |
|---|---|---|---|
| `--h2` | `#10836A` | `#35D0A5` | viridis mid — **hydrogen, capacity, "good"** |
| `--h2-glow` | `#22A884` | `#6BF0C8` | highlight |
| `--press` | `#C4471B` | `#FF7A45` | inferno mid — **pressure, flux, "hot"** |
| `--caution` | `#A5720A` | `#E8B33A` | assumption / caveat |
| `--critical` | `#C31F3C` | `#FF4D6A` | breach, failure |
| `--text` | `#131C20` | `#DCE8EC` | body |
| `--text-dim` | `#4E626A` | `#8CA3AC` | secondary |
| `--ground` | `#EDF1F2` | `#080D10` | page |
| `--panel` | `#FFFFFF` | `#0E161A` | card |
| `--line` | `#CBD6D9` | `#22323A` | rule |

Type: `ui-monospace / SF Mono / Menlo` for **all numbers and units**; Helvetica Neue /
system sans for prose. Numbers in mono is the single cheapest thing that makes a deck read
as an instrument.

### The five design rules that carry over

1. **The plume is the hero, and it breathes.** Ten annual cycles is a rhythm. Timeline is a
   *cycle ribbon* — 60 ticks banded by stage — not a generic slider.
2. **A 2.5D slab, not three flat heatmaps.** Rendered as an extruded slab with a translucent
   lid, the fault becomes a vertical plane *piercing the seal* — the entire physics argument
   in one picture.
3. **The fault swarm replaces the histogram.** A histogram of N probabilities abstracts away
   something inherently spatial. Drawn as segments on the plan view, coloured by risk, you
   *see* that the dangerous faults sit on the plume front near the pressure ridge.
4. **Provenance is the design system.** `[DATASET]` / `[DERIVED]` / `[ASSUMED]` as a chip on
   every number. The honesty stops being a yellow warning banner nobody reads.
5. **The latency is on screen.** "Sub-second instead of multi-hour" is the core claim and it
   currently lives in a README. Time every recompute and print it.

---

## 13. Glossary for a non-geologist judge

Keep these one-liners ready; drop them inline rather than as a slide.

| Term | One-line explanation |
|---|---|
| **Porosity (φ)** | The fraction of rock that is empty space. How much you can store. ~25–31% here. |
| **Permeability (k)** | How easily fluid moves through the rock. How fast you can inject or produce. Measured in darcies; 1–739 millidarcy here. |
| **Caprock / seal** | The impermeable lid — usually shale or salt — that stopped gas escaping for millions of years. |
| **Trap** | Reservoir + seal + a geometry that stops buoyant gas migrating away, all at once. |
| **Fracture gradient** | Pressure per metre of depth at which the rock cracks. ~0.15–0.20 bar/m. Exceed it and you break your own lid. |
| **Hydrostatic gradient** | Normal fluid pressure with depth, ~0.105 bar/m. What the reservoir sits at before you touch it. |
| **Fault core / damage zone** | A fault's low-permeability gouge, and the fractured halo around it. The halo is the leak path — and it points *up*. |
| **Relative permeability** | When two fluids share a pore network they block each other. Below a residual saturation, gas can't flow at all. |
| **Residual / cushion gas** | Gas permanently stuck in the rock, or deliberately left to hold pressure. Roughly half your inventory, and you never get it back. |
| **Plume** | The body of injected hydrogen in the rock. It breathes — grows on injection, retreats on withdrawal. |
| **Buoyancy / gravity override** | At reservoir conditions hydrogen is ~80× lighter than brine (≈12.5 vs ≈1,050 kg/m³), so it floats to the top of the reservoir and pools against the seal. |
| **Darcy's law** | Flow = permeability × area × pressure difference ÷ (viscosity × length). The whole leakage model is one line of it. |
| **Persistence baseline** | "Assume tomorrow looks like today." If your model can't beat it, you haven't forecast anything. |
| **PR-AUC** | Accuracy measure for rare events. Only 2.2% of our cases are elevated-risk, so plain accuracy or ROC-AUC would flatter us. |
| **Surrogate model** | A fast approximation of a slow simulator. Ours is a U-Net; it turns hours into milliseconds and costs 1% of screening accuracy. |
| **SHAP** | Per-prediction credit assignment: exactly which feature pushed *this* risk score up, and by how much. |

---

## 14. Forbidden claims

From `docs/FINDINGS.md` §10 and the docs' own rules. If any of these appears in the deck,
the deck is wrong.

- ❌ "We predict 3D reservoir maps" — the grid is 128×128×**1**.
- ❌ "Trained on simulated leakage ground truth" — there is none; T3 is a derived
  semi-analytical label.
- ❌ "Real-time sensor fusion" — there is no sensor data.
- ❌ A binary caprock-breach rate — it flips on one assumed constant.
- ❌ A lateral containment-loss result — 0/1000.
- ❌ Any leakage score quoted at a horizon that is a whole number of storage cycles.
- ❌ "Predicts hydrogen leakage" without stating that the label is ours, from a hypothetical
  fault, on real simulated flow fields.
- ❌ "Site #468 is the best site" — report tiers or percentile rank; the top-10 shifts 2–5
  seats under re-weighting.
- ❌ Any ROI, $/kg, or avoided-cost number. **Module 4 now exists** (`src/economics/`)
  but this claim does not change, because the module deliberately does not produce
  one — no leak-rate ground truth exists to price. Quote the **dimensionless**
  efficiency ratio (VOI/VOPI) instead, and the only real money figure we own: our
  own compute cost, 0.652 vCPU-seconds per screening pass. See
  `Economics_and_impact.md`.
- ❌ Any capability for CO₂ / CCUS. At reservoir conditions CO₂ is 61× denser than
  H₂ with a 5× weaker buoyancy contrast against brine, and it is injected
  monotonically rather than cyclically — an H₂-trained model would mis-rank its
  risk systematically. Natural gas storage (CH₄, 1.93× viscosity, 0.88× buoyancy)
  is the defensible next market. Computed in `src/economics/fluids.py`.
- ❌ "AI surrogate for storage" as our novelty. Stanford's CCSNet published one for
  CO₂ in 2021. Our novelty is the **fault-hypothesis layer**, which sits on top of
  any surrogate.
- ❌ That we timed 20,000 hypotheses. We timed 50 — the API's own cap — and the
  architecture carries the rest.
- ❌ "Traditional monitoring catches it at day 40, we catch it at day 5" — this exact
  comparison is called out in `Build_Plan.md` as an invented number. Real sites run downhole
  gauges, DTS/DAS, integrity logging and soil-gas sampling.
- ❌ Reproduction of the paper's accuracy — we are ~1.9× the paper's U-Net-Small error.
- ❌ Naming the undocumented third channel. We know its units. We don't know its name.

---

## 15. File map — where everything lives

### Read these first

| File | What it gives the presenter |
|---|---|
| `README.md` | The pitch, the results tables, the module status table vs the original scope, the path ahead |
| `docs/FINDINGS.md` | **Every measurement, including all negative results.** The credibility spine. Anything reported must be consistent with this file. |
| `docs/SITE_SUITABILITY.md` | Module 1's working log — the dropped clustering, the correlation matrix, the weight sensitivity table |
| `docs/FRONTEND.md` | Design thesis, what's real vs mocked on the page, deployment, the demo-pack plan |
| `Document 9.pdf` | The original 4-module pitch. Read it to know what you promised, so the status table lands as candour rather than shortfall. |

### Superseded, but useful

| File | Still valid for |
|---|---|
| `Data_sources_research.md` | **§1–§3 only** — the physics research, including the fact-checked H₂ vs CH₄ property table and the ranked leak-pathway list. §4–§6 describe a simulator that was never built. |
| `Build_Plan.md` | The **Economics** section — the differential-ROI scope decision, the assumption register, the compressor-energy first-principles check. Part I compute benchmarks are for a different machine and a different plan. |
| `Feasibility_assessment.md` | M1 hardware benchmarks (import-order segfault, thermal throttling, parallel scaling). Its "skip Colab/Kaggle" conclusion **no longer applies** — the project pivoted and Kaggle is now the proven path for both training and data prep. |

### Code

| Path | Contents |
|---|---|
| `src/config.py` | **Every constant, tagged `[DATASET]` / `[DERIVED]` / `[ASSUMED]`.** Start here for any physical number. |
| `src/leakage/labels.py` | T1/T2/T3 targets, the Darcy + Corey flux model, the six physics self-checks |
| `src/leakage/features.py` | 41 features, multi-horizon label construction, the forecast-framing rationale |
| `src/leakage/risk_map.py` | Spatial "where would a fault be dangerous" surface |
| `src/site_suitability.py` | The 0–100 ranking, weights on the CLI |
| `src/train_xgb.py` | Horizon sweep, persistence + weak baselines, exact TreeSHAP |
| `src/models/unet.py` | U-Net, relative-L2 loss, paper parameter-count check |
| `src/explore.py` | Dataset validation and the T1 go/no-go |
| `app/web/index.html` | The deployable frontend — self-contained, no external requests |
| `app/dashboard.py` | Streamlit research tool — **needs the 12.38 GB dataset, cannot be deployed** |

### Data you can use without downloading 12.38 GB

All in `outputs/`, all tracked in git:

| File | Rows / contents |
|---|---|
| `site_suitability_ranking.csv` | **1,000 rows** — the full ranking, with normalised criteria. Powers the live Storage Atlas. |
| `site_suitability_features.csv` | 1,000 rows — raw geology per realisation (φ mean/σ, log k mean/σ, p_max, caprock margin) |
| `site_suitability_summary.json` | Top/bottom 10, score distribution, weights used |
| `xgb_results.json` | Reported-horizon metrics, all 41 feature names, gain-based importance, table metadata |
| `xgb_horizon_sweep.json` | All five horizons, model + weak + persistence baselines |
| `source_comparison.json` | Simulator vs U-Net, plus per-feature distortion |
| `explore_report.json` | Well-location validation, cyclic-index validation, plume geometry, T1 verdict |
| `shap_features.json` | The 41 feature names in order |
| `xgb_classifier.ubj` / `xgb_regressor.ubj` | Trained models, 2.0 / 2.8 MB |
| `checkpoints/unet_small_best.pt` + `unet_small_history.json` | Trained surrogate and its full training curve |

### Verification built into the pipeline — a slide in itself

Each of these is an **assertion in code**, not a manual step. Listing them is one of the
fastest ways to establish engineering credibility with a technical panel:

- Download checked against the published Zenodo MD5
- Conversion round-tripped against the source LMDB, with tolerances **derived from float16
  resolution** rather than chosen to pass
- Architecture checked against the paper's reported weight counts **before** any training
- Overfit test on 4 simulations, to catch channel-ordering and normalisation bugs before
  committing hours of GPU time
- Split disjointness asserted **by simulation ID at both stages**
- Leakage physics monotonicity — flux must rise with fault permeability and overpressure,
  and be exactly zero during withdrawal and below residual gas saturation
- Persistence baseline reported alongside every risk score, with horizons where persistence
  exceeds 0.9 PR-AUC **flagged as "not a forecasting task"**

---

## Appendix — one-line source of truth

> Mao, S., Carbonero, A., & Mehana, M. (2025). *Deep learning for subsurface flow: A
> comparative study of U-Net, Fourier neural operators, and transformers in underground
> hydrogen storage.* JGR: Machine Learning and Computation, 2, e2024JH000401.
> <https://doi.org/10.1029/2024JH000401> · Dataset: <https://zenodo.org/records/14029514>
> (CC-BY-4.0 / MIT)

Cite it on the data slide and in the credits. It is 100% of the real physics in this
project, and saying so is both correct and disarming.
