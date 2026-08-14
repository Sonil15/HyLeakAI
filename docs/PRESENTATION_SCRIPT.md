# Round 1 — 6-Minute Script

> **Historical record — do not deliver this at the finals.** Use
> [`PRESENTATION_SCRIPT_FINALS.md`](PRESENTATION_SCRIPT_FINALS.md) (4–5 min).
> Kept unedited because it is the record of what was actually said in round 1.
>
> Two things in it are now **out of date**: the line *"the economics module is
> planned but not built"* (it is built — `src/economics/`), and the guard-rail
> section's reasoning. The guard-rail's **conclusion still stands** — no ROI, no
> $/kg, no avoided-cost figure — but the reason changed. It was "we haven't built
> the module." It is now "we built it, and it deliberately produces no currency
> figure, because every route to one runs through a leak rate nobody can
> calibrate." Quote the dimensionless VOI/VOPI ratio instead. See
> `Economics_and_impact.md`.

**Spoken words: 912** — or **885** without the optional block in slide 8. Counts
are measured, not estimated.

At 160 wpm, 885 words is **5 min 32 s**, plus ~20 s of clicking in the demo:
**about 5:52**. Rehearse once with a timer; if you run slow, take the top item
off the cut list at the bottom.

**No software jargon anywhere in the spoken script.** Your audience is oil and
gas, not engineering managers — so no builds, no commits, no repositories, no
pipelines. The one exception is "every number is a public file" at the very end,
which is a claim about openness, not about tooling.

Mao et al. are now credited inside slide 3, step two, where the AI is
introduced. That is the right place for it: the judges hear whose simulations
the model learned from at the moment it matters, and the claim that follows —
"that paper stops at step two, step three is ours" — lands harder for sitting
next to it.

Everything above the `═══` line is said out loud. Everything below it is
reference for Q&A — don't read it, and don't count it in your timing.

Timings assume the optional block in slide 8 is dropped.

| Time | On screen | Words |
|---|---|---|
| 0:00–0:25 | Slide 1 | 66 |
| 0:25–1:24 | Slide 2 | 159 |
| 1:24–2:33 | Slides 3 → 5 — **how it works** | 182 |
| 2:33–4:22 | Slides 6 → 7 → 8 | 297 |
| 4:22–5:06 | **LIVE SITE** | 79 + clicking |
| 5:06–5:29 | Slide 10 | 61 |
| 5:29–5:52 | Slides 11 → 12 | 73 |

**Slide 5 no longer has its own block.** Put it on screen while you say the
attribution line in step two, and leave it up through "step three is ours" — the
provenance table on that slide does its own work while you talk. Then move on.

Two rules: short sentences, and never say a number without saying what it means.

---

## 0:00–0:25 — SLIDE 1 · Why these fields

> We're HyLeakAI.
>
> Hydrogen is how you store renewable energy for months instead of hours. But
> you need somewhere to put terawatt-hours of it.
>
> That place already exists: depleted gas fields.
>
> **They're big enough** — only porous rock works at that scale. And **the seal
> is proven** — that rock held natural gas for millions of years with nobody
> watching it.
>
> Huge, and already tested by nature.

---

## 0:25–1:24 — SLIDE 2 · The obstacle

> So why isn't this happening already?
>
> The seal is the rock above it. Hydrogen doesn't break it — pressure does, and
> storage is pressure.
>
> Now, faults. A fault is a crack in the rock, millions of years old. Nobody put
> it there — so nobody knows where it is.
>
> And here's what surprises people. You'd expect a crack to leak in every
> direction. It doesn't. The middle of a fault is crushed rock, packed so tight
> it **blocks** flow sideways. But the rock around it is shattered into
> fractures, and those do carry gas — **upward**, along the fault. Straight
> through the seal.
>
> So a fault isn't a hole in your seal. It's a chimney through it. And one is
> enough.
>
> Industry checks this with a full simulator, tNavigator. It's the ground truth,
> but every new fault means another run, and runs take hours. So operators test
> one or two guesses and move on.
>
> The blocker is the clock.

---

## 1:24–2:33 — SLIDES 3 → 5 · How it actually works

> Here's how it works, in three steps.
>
> **One — the input is rock.** A site is two maps: how much empty space the rock
> has, and how easily fluid moves through it.
>
> **Two — the AI predicts the physics.** From that rock it predicts pressure and
> hydrogen everywhere, across ten years of filling and emptying. Milliseconds.
>
> It learned that from a thousand published simulations — Mao and colleagues,
> last year, under an open licence. And notice: no fault in this step. Those
> simulations don't contain any.
>
> **Three — then the safety question, separately.** Nobody knows whether a fault
> exists. So we suppose one: here, this leaky, this wide. We look up the pressure
> and hydrogen the AI already predicted at that spot, and compute how much
> escapes. That's Darcy's law.
>
> Step two already happened, so step three is nearly free. That's why we test
> twenty thousand faults instead of one — twenty thousand **guesses about one
> crack**.
>
> **That paper stops at step two. Step three is ours.** It gave us the physics;
> the safety decision is ours.

---

## 2:33–4:22 — SLIDES 6 → 7 → 8 · Why believe it

**Slide 6 — the physics is enforced:**

> The risk number comes from that equation, and physics puts hard limits on it.
>
> Here's one. If hydrogen is spread too thin — below about five percent — it
> isn't a body of gas any more. It's isolated bubbles, stuck in the pores.
> Bubbles don't flow, however hard you push. So the model returns **zero**. Not
> a small number. Zero.
>
> There are six rules like that, and the model is held to every one. It cannot
> return an answer the physics forbids.

**Slide 7 — the forecast test:**

> Next, the forecast. Storage repeats every year. So if you ask what happens
> twelve months from now, you can answer "the same as today" and be right nearly
> every time. That's a calendar, not a forecast.
>
> So we test six months out, when the field is doing the **opposite** of what
> it's doing today. There, "same as today" scores 0.02 out of 1. We score 0.99.

**Slide 8 — the AI versus the simulator:**

> Last, the AI itself. It's a stand-in for the simulator, and stand-ins have
> error. Here's how much.
>
> The full-size model has **124 million** settings. Our hardware couldn't hold
> it — a laptop with 8 gigabytes of memory and a free cloud GPU. So we trained a
> **7 million** version, and shrank it further to fit. At full size it should
> reproduce the simulator's maps to about **99 percent**. Ours manages **86.4**.
>
> So we ran the risk scoring twice. Once on the real simulator maps, once on our
> rougher ones. The ranking moved by **one percent**.
>
> Our picture is blurrier; the ranking barely notices. Good enough to screen
> sites — not to quote leak rates, which is why we don't.

**↓ OPTIONAL — 27 words. Drop this first if you are over time.**

> And that's the one thing funding changes. One day on a GPU that holds the full
> model. More training time on the small one won't do it — we checked.

---

## 4:22–5:06 — LIVE SITE

*Tab already open, already scrolled to the atlas. Checklist below the line.*

> This is deployed — one page, no server.
>
> A thousand candidate sites. Across is capacity, up is seal risk. Real output.

**Point at the panel:**

> We score three things. Capacity. Seal risk. And heterogeneity — is the rock
> patchy or uniform? Patchy is worse: you can't predict where the hydrogen goes.

**Click SEAL-LED. Let it reshuffle.**

> How we weight those three is our assumption. So watch. [click] The ranking
> reshuffles. That's why we never name one best site.
>
> And every number here is tagged: dataset, derived, or assumed.

**Back to the slides.**

---

## 5:06–5:29 — SLIDE 10 · The impact

> The output is a risk map. Not "is this fault dangerous", but "**if** a fault
> were here, how bad?" — every point in the field, in a second.
>
> And the saving isn't only time. Monitoring wells and seismic surveys are
> expensive. You find the problem before the money is spent — and a regulator
> gets a number with every assumption tagged.

---

## 5:29–5:52 — SLIDES 11 → 12 · Where we stand, and close

> Where we stand. The risk engine works. The interface is live. The economics
> module is planned but not built — and the slide says so.
>
> We also report what failed. We had a near-perfect twelve-month score, and we
> withdrew it ourselves, because the yearly cycle had earned it, not the model.
>
> Every number is a public file.
>
> We spent as much effort proving what our numbers don't mean as producing them.
> Thank you.

---

# Cut list — if you're still over 6:00

In this order. Each is one clean lift, no stitching needed.

**Already applied:** slide 1 trimmed to two reasons, slide 5 cut to four lines,
the permit line folded into slide 10, and every section tightened once.

Remaining, in order:

1. **Slide 8, the optional block** (−27 words) — marked in the script.
2. **Slide 2, the seal sentence** (−17 words). The chimney carries that section.
3. **Slide 10, the last sentence** (−20 words) — the regulator line.
4. **Slide 1, the second reason** (−22 words) — "the seal is proven". Weakens
   your opening; last resort.

All four takes you to ~868 words, about 5 min 32 s with clicking.

**Never cut:** the fault chimney, the trapped-bubbles rule, the six-month test,
or the weight toggle. Those four are the whole talk.

═══════════════════════════════════════════════════════════════════════

**Everything below is reference. Not spoken. Read it before the presentation,
not during.**

# Demo checklist — before you walk up

1. **Open the tab in advance.** `https://sonil15.github.io/HyLeakAI/`. Alt-tab
   to it. Never type a URL live.
2. **Pre-scroll to the Storage Atlas** (section `01 / SCREEN`). The page opens
   on a design essay with **"NOT THE SHIPPED APP"** in the top-right corner.
   Don't scroll past that live.
3. **Zoom to ~125%.** Hide the bookmarks bar.
4. **Offline fallback.** The page is one self-contained file. If the Wi-Fi
   fails, open `app/web/index.html` from disk. It behaves identically.
5. **Practise the weight-toggle click**, so you know how far the table moves.
6. **Practise the exit** — alt-tab back mid-sentence, not after a pause.

## Three things not to say during the demo

- **Not "our product" or "the app."** The page says *"not the shipped app"* and
  *"nothing on this page should be quoted as a result."* Say "the interface —
  one panel live, the rest labelled."
- **Don't call site #468 the best site.** It's rank 1 under the default
  weighting only. It's the thing that *moves* when you click.
- **Don't quote numbers off the lower panels.** Those are stand-ins. Only the
  atlas is real.
- **Never say "we published."** No paper exists. Say "it's documented in our
  repository."
# What we save besides time

Time is the mechanism, not the benefit. Four things follow from it. The first
three are safe to say; the fourth needs care.

**1. It moves spend to the right place.** Screening is cheap; the decisions it
steers are not — monitoring well placement, seismic survey scope, and the
decision to commit capital to a site at all. Testing a thousand candidates
instead of two means a containment problem shows up during screening rather than
after the money is committed.

**2. It reduces the chance of a leak happening at all.** A dangerous fault
scenario found before injection is a design change. The same scenario found
afterwards is an incident. Right now most scenarios are never tested, because
nobody can afford the simulator runs — so the risk isn't accepted, it's just
unmeasured.

**3. It produces an auditable risk statement.** This is the one operators need
and the one nobody else is offering. A permit or an insurance case needs a
defensible number: a probability, the physics behind it, and a clear line
between what was measured and what was assumed. Every number we output carries
that tag. "We ran two scenarios and they looked fine" does not survive scrutiny;
a swept distribution with tagged assumptions does.

**4. Less compute burned.** True — twenty thousand hypotheses on one forward
pass instead of twenty thousand solver runs. Mention it only in passing. We
never measured either side's energy, so it cannot carry weight.

## The guard-rail

**No money figures. None.** No ROI, no cost per kilogram, no avoided-cost
estimate, no "saves X thousand dollars per site." Module 4 (economics) is *Not
Started* and slide 11 says so. If you invent a number here, slide 11 contradicts
you four minutes later, and the honesty case — which is the strongest thing you
have — collapses.

The correct move is to name *what* gets cheaper and say the number isn't ours to
give yet. That reads as discipline, not as a gap.

**Similarly, don't reach for hydrogen's climate impact as a greenhouse gas.**
It's real science, but it isn't in our repository, we haven't verified it, and a
judge who knows the literature will ask for the figure. Stay with what you
measured: lost product, surface hazard, and containment you can defend.

---

# The fault, if a judge wants more detail

The stage version is deliberately short. This is the backing, from slide 4.

- **A fault is pre-existing.** It is not damage we cause by injecting. That is
  the whole reason it has to be treated as an unknown — if we had made it, we
  would know exactly where it was and how leaky.
- **Two parts, opposite behaviour.** The *core* is crushed, ground-up rock
  (gouge). It is low-permeability and it seals *across* the fault, sideways. The
  *damage zone* is a halo of subsidiary fractures around the core, and it
  conducts *along* the fault — which is to say, vertically.
- **Why that's the worst possible geometry.** Vertical is precisely the
  direction the caprock exists to prevent. The seal can be intact across its
  whole area and still be bypassed at one fault.
- **What the seal actually is.** A capillary seal, not an impermeable one: the
  pore throats are too small for gas to displace the water in them. Hydrogen
  does not defeat that — its wettability against water-wet caprock is comparable
  to methane's. Overpressure defeats it.

**The line, if you only get one sentence:** *the fault is a chimney that was
already there, and the seal only has to fail in one place.*

# What "20,000 fault hypotheses" means

Say this if anyone looks confused, because the phrase is genuinely ambiguous.

It is **not** 20,000 faults in a field. It is 20,000 *hypotheses about one
unknown fault*: a position, a permeability, a width. Fault permeability alone
spans 10⁻¹⁵ to 10⁻¹² m² — three orders of magnitude — and position is unknown
across the whole domain. You cannot resolve that uncertainty, so you enumerate
it and score every combination. That is exactly what a simulator can't afford
and what our decoupling makes cheap.

# The 41 inputs, grouped

From `src/leakage/features.py`. On stage you name the groups, not the features.

| Group | What it is, plainly | Examples |
|---|---|---|
| **Rock** (U-Net input) | How much empty space, and how easily fluid moves | porosity, permeability |
| **Pressure** | How high, how fast rising, how steep, how close to cracking | peak / mean / 95th-percentile pressure, pressure at the well, overpressure vs initial, steepest gradient, rate of change per year, **caprock margin** |
| **Hydrogen plume** | How big it is and how fast it's moving | plume area, max radius, centroid offset, front speed |
| **At the fault** | What conditions the fault actually sees | pressure at the fault, overpressure at the fault, whether the gas there is mobile or trapped, distance from the plume edge to the fault, rock quality at the fault |
| **Fault geometry** `[ASSUMED]` | The hypothesis being tested | permeability, width, length, area, distance from the well |

Two things worth knowing if pressed:

- The rock maps are the **only** input to the AI. Everything else is measured
  from what it predicts.
- The fault group is entirely hypothesis, not observation — which is why the
  output is a conditional risk ("*if* a fault is here") and never a prediction
  that a fault exists.

---

# What is theirs, and what is ours

The full split, for Q&A. On stage you only say the three headline items.

**From the paper (Mao et al., 2025), used under its open licence:**

- The 1,000 tNavigator simulations — the physics, the geology, the fields.
- The U-Net architecture. We matched their reported parameter counts exactly
  before training anything.

**Built by us, and not in the paper:**

1. **A leakage risk model.** Darcy flow up a hypothesised fault, gated so that
   trapped hydrogen can't move. The paper has no leakage model at all.
2. **The decoupling.** The fault sits outside the network, so one field
   prediction serves twenty thousand fault hypotheses. This is the architectural
   idea, and it's ours.
3. **Forecasting, tested honestly.** Elevated leakage six months ahead, with the
   persistence baseline that disqualifies whole-cycle horizons. The paper
   reconstructs fields; it doesn't forecast risk.
4. **The spatial risk map.** A 32 × 32 sweep of "if a fault were here, how bad?"
5. **Site screening.** All 1,000 realisations ranked on capacity, seal risk and
   heterogeneity — plus the finding that they don't form clusters.
6. **Interpretability.** The model's own feature ranking reproduces the term
   order of Darcy's law.
7. **Data forensics.** The undocumented third channel, characterised and written
   up. The well position, which the paper describes only as "a central well",
   located empirically from the data.
8. **A deployed interface**, with per-panel provenance labelling.

**The one-line version if a judge asks directly:** *they showed AI can reproduce
the simulator's physics; we used that to answer whether the site is safe, which
the paper never attempts.*

**Careful with the word "published."** We have not published a paper. The third
channel and every negative result are documented in our public repository
(`docs/FINDINGS.md`). Say "we documented it in the open" or "it's in our repo",
never "we published it."

---

# The constraint beat — the facts behind it

Source: `docs/FINDINGS.md` §8. Don't quote these numbers on stage; know them in
case a judge asks.

| | What we had | What the paper had |
|---|---|---|
| Dev machine | M1 Air, 8 GB RAM, fanless, disk 99% full | — |
| Dataset | 12.38 GB (bigger than our free disk) | same |
| Training hardware | One free Kaggle T4, 12-hour session cap | not stated |
| Training run | 120 epochs, 4.23 h, 127 s/epoch | — |
| Batch size | 48 | **128** |
| Model layout | **One shared network**, two output heads | **Two separate networks** |
| Precision | Mixed | Consistent |
| Test error (pressure) | 0.1640 | **0.086** |
| Test error (saturation) | 0.1101 | **~0.06–0.07** |

**Why "more hours" is the wrong ask, and say so if pressed.** Accuracy fell
steeply to epoch 76, then oscillated for the remaining 44 epochs. Halving the
learning rate twice didn't break through. It is a floor, not an unfinished run —
so a longer job on the same setup buys nothing.

**The right ask, in one sentence:** enough GPU memory to train two separate
networks at batch 128. The shared trunk is our own deviation, made to halve
cost, and pressure and saturation are fighting each other inside it — pressure
is smooth and global, saturation has a sharp moving front. That is the
experiment we'd run first, and it is untested, so say "we expect", never "we
will".

**Framing rule.** This is a resourcing statement, not an excuse. The pattern is:
*here is the gap → here is exactly why → here is the specific fix.* A team that
can name the cause of its own weakness reads as more competent than a team with
no weakness to name.

---

# Us versus what the industry uses today

Keep this in your head. It is the comparison the judges will be making, and it
is also the shape of the answer if they ask directly.

| | tNavigator (a full reservoir simulator) | HyLeakAI |
|---|---|---|
| What it does | Solves the real flow physics on a 3D grid | Learns the pattern from 1,000 of its runs |
| Accuracy | Ground truth. Better than us, always | ~1% behind it for *ranking* risk |
| Cost per fault scenario | A whole new run | Almost nothing — the field is predicted once |
| Scenarios you can afford | One or two, hand-picked | Twenty thousand |
| Answers | How much, exactly | Which sites and which faults deserve a real run |
| Explains itself | It's physics, so yes | Yes — ranks the same terms as Darcy's law |

**The line to land:** *we don't replace the simulator, we tell it where to look.*
Judges respect that far more than a claim to have beaten a commercial solver.

## One honesty guard-rail on this comparison

**We never timed tNavigator ourselves.** "Hours per run" is the industry-known
figure and it's what the source paper's setup implies — it is not a stopwatch
number we measured. So:

- ✅ Say: "every new fault means running it again from scratch." That is a
  structural fact and it's the real argument.
- ⚠️ Avoid: "we're 10,000× faster than tNavigator." We have not measured the
  denominator, and one sharp judge asking "compared to what, on what hardware?"
  undoes the credibility the rest of the talk is built on.

If someone pushes for a speed number, say what's true: our side is measured and
on screen — every recompute on the live page prints its own timing. The
simulator side we take from the literature, not from our own bench.

---

# Demo checklist — do this before you walk up

1. **Open the tab in advance.** `https://sonil15.github.io/HyLeakAI/`. Alt-tab
   to it. Never type a URL live.
2. **Pre-scroll to the Storage Atlas** (section `01 / SCREEN`). The page opens
   on a design essay headed *"An instrument, not a dashboard"*, with **"NOT THE
   SHIPPED APP"** in the top-right corner. Scrolling past that live invites the
   question you don't want.
3. **Zoom the browser to ~125%.** Hide the bookmarks bar. The scatter and the
   tags are small on a projector.
4. **Offline fallback.** The page is one self-contained file with no external
   requests. Keep a copy on the laptop. If the venue Wi-Fi fails, open
   `app/web/index.html` from disk. It behaves identically.
5. **Click the weight toggle once in rehearsal**, so you know how far the table
   moves. That reshuffle is the most memorable second of the demo.
6. **Practise the exit.** Alt-tab back to the deck mid-sentence, on your own
   words. Not after a pause, where someone can interrupt.

## Three things not to say during the demo

- **Don't call it "our product" or "the app."** The page says *"not the shipped
  app"* and *"nothing on this page should be quoted as a result."* If a judge
  reads that corner while you claim a finished product, you lose the credibility
  the rest of the talk is built on. Say "the interface — one panel live, the
  rest labelled."
- **Don't read out site #468 as the best site.** It is rank 1 under the default
  weighting only. Use it as the thing that *moves* when you hit the toggle.
- **Don't quote a number off panels 2 or 3.** Those fields are stand-ins. The
  only quotable numbers on the page are in the atlas.

---

# Cut list — if you run long

Drop in this order. Each is self-contained.

1. Demo beat 3, the breathing reservoir (−20 s). It is already optional in the
   timing above. Beats 1 and 2 carry the point.
2. The "it recovered Darcy's law" line on slide 8 (−15 s).
3. The third-channel discovery on slide 5 (−15 s). But **keep** the "twice their
   error" line. That is the one that buys credibility.

**Never cut:** the six-month versus twelve-month explanation on slide 7, or the
weight toggle in demo beat 2. Those are your two strongest maturity signals.

# Jargon swaps used

| Don't say | Say |
|---|---|
| heterogeneity | "is the rock patchy or uniform? Patchy is worse" |
| PR-AUC 0.9931 vs 0.0218 | "scores 0.99 out of 1, where copying today's answer scores 0.02" |
| persistence baseline | "copying today's answer" |
| surrogate model | "a fast AI stand-in for the simulator" |
| TreeSHAP attribution | "we checked what the model was using" |
| Monte-Carlo sweep | "testing thousands of possible faults" |
| relative permeability gate | "hydrogen trapped in isolated pockets can't flow" |
| iso-score lines / nomograph | "lines of equal score" |
| caprock | "the rock above it" / "the seal" |

# Likely questions

- **"Is this validated against a real leak?"** No, and we don't claim it. No
  public dataset has real hydrogen leakage measurements. The rock physics inputs
  are real published simulations. The leakage labels are ours, derived from a
  stated equation, and tagged as such on every slide.
- **"Why not just use the paper's model?"** We do use their data and their
  architecture. The paper predicts the flow fields. It doesn't score safety. The
  risk layer, the fault sweep and the spatial map are ours.
- **"Why not just run tNavigator?"** You should — on the scenarios that matter.
  The problem is knowing which ones those are. There are thousands of possible
  faults and you can afford a handful of runs. We do the sifting, and the
  simulator does the verdict.
- **"So your model is less accurate than the simulator?"** Yes, and it has to
  be — it's learning from the simulator, not replacing its physics. For ranking
  which sites and faults are risky, we're about 1% behind. For predicting how
  much hydrogen actually escapes, we're clearly worse, and we say so on slide 8.
  That's why we call it screening.
- **"How much of that website is real?"** The 1,000-site atlas is real output —
  scores, ranks, criteria. The reservoir animation and the attribution bars are
  stand-ins, labelled on the page. Making them real is one export run away:
  about 2 MB of pre-rendered fields per site, instead of the 12.38 GB dataset.
- **"Two-dimensional, not three?"** Correct. The grid is 128 × 128 by one layer.
  It is a screening tool, not a substitute for a full 3D study.
- **"How much would a better GPU actually buy you?"** We expect most of the gap
  to the paper — they're at roughly half our error with the same architecture
  and more compute. We won't promise a number, because the experiment hasn't
  been run. What we can say is that it's one day of work, not a research
  programme, and we know which run to do first.
- **"What does this save in money terms?"** We can tell you what gets cheaper —
  fewer simulator runs, better-placed monitoring wells, and catching a bad site
  during screening instead of after commitment. We can't give you a figure,
  because we haven't built the economics module and we're not going to invent
  one. It's scoped and it's the next thing we'd build.
- **"Isn't this just a faster version of what people already do?"** No — people
  don't do this at all today, because they can't afford to. One or two
  hand-picked fault scenarios isn't a faster version of sweeping twenty
  thousand; it's a different question with a much weaker answer.
- **"Does the accuracy gap invalidate your results?"** No, and we measured that
  specifically. The gap is in predicting the fields. For *ranking* which
  scenarios are risky — which is what the tool is for — swapping real simulator
  data for our predictions costs about one percent. It does hurt predicting how
  much leaks, and that's why we don't claim that.
