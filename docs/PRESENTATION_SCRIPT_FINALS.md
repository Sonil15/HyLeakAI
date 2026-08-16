# MC²+ Grand Finale — finals script (restructured)

**Five slides, then a live demo.** New structure, replacing the round-one narrative
arc entirely:

| # | Slide | Spoken words | Time @160 wpm |
|---|---|---|---|
| 1 | The problem, and the size of the prize | 164 | 1:01 |
| 2 | Module 1 — site suitability (pipeline on screen) | 157 | 0:58 |
| 3 | Module 2 — leakage (two-part flowchart on screen) | 211 | 1:19 |
| 4 | Economic impact, and how it is calculated | 177 | 1:06 |
| 5 | What we shipped since round one, and what's next | 207 | 1:17 |
| — | **LIVE DEMO** — atlas + reservoir, no live mode | 144 + clicking | 1:15 |
| | **Total** | **1,060** | **≈ 6:58** |

**The full text is 6:58 — over the cap. Deliver it with cuts 1 through 5
applied: that is 5:58, and it is the version to rehearse.** All five are now
mandatory, not optional: slide 3 carries the two validation checks and slide 4
carries the pricing sentence, which are what the jury's "technical soundness"
and "industrial / commercial impact" criteria are asking for. Both are worth
more than the spoken geology on slide 2, whose criterion names stay on screen in
the pipeline graphic either way. 5:58 has **no margin at all** — rehearse to the
clock, and if you run long on the day, drop the two-checks lines on slide 3
first (the numbers stay on the slide).

Word counts are measured, not estimated; recount with the snippet at the bottom
after any edit. Slides alone are 5:44 uncut, and the demo's 1:15 is wall-clock: 144
spoken words is ~54 s of it, leaving ~21 s for the orbit, the reshuffle, the
scroll and one cycle of the ribbon. **Don't ad-lib inside the demo** — that 21 s
is the whole budget.

**Demo page:** the Storage Atlas build on `feat/cloud-run-deployment`, **sections
01 and 02, no live mode.** The atlas half is real pipeline output running
client-side, so venue Wi-Fi cannot kill it. The reservoir half is the page's own
labelled illustration and the script narrates it as one — see "How to narrate
section 02" in the checklist, which is the single most important page in this
document. The live model, the geologist site-input screen and the evidence export
are **claims on slides 3 and 5, not clicks**; answers for "show me it running"
are in the judge-questions section.

Two rules carry over from round one and still govern every line: **short
sentences**, and **never say a number without saying what it means.**

Everything above the **"If a judge pushes"** heading is spoken. Everything below
it is reference — do not read it, do not count it in your timing.

---

## SLIDE 1 · The problem, and the size of the prize  *(164 words)*

*On screen: renewable surplus curve → underground storage; the 5 MMT/yr target.*

> We're HyLeakAI.
>
> Wind and solar don't run all the time. The sun sets, the wind drops — and the
> power you need in winter gets made in summer. So you have to **store energy for
> months, not hours.** Hydrogen is the best tool we have for that.
>
> But you have to put it somewhere — millions of tonnes. Only one place is that
> big: **underground, in porous rock.** Depleted gas fields, which held natural
> gas for millions of years.
>
> So: **does it stay down there?** Pressure can crack the seal above it. And an
> old fault — a crack already in the rock, nobody knows where — carries hydrogen
> straight up through it. One is enough.
>
> Checking that today means a full reservoir simulation. **Hours per scenario.**
> So an operator tests one or two cracks and moves on.
>
> Meanwhile the demand is policy: the National Green Hydrogen Mission targets
> **five million tonnes a year by 2030** — all of it stored somewhere.
> **Somebody has to screen those fields first.**

---

## SLIDE 2 · Module one — which rock is worth storing in  *(157 words)*

*On screen: the site-suitability pipeline — 1,000 grids → 3 features → weighted
score → ranked database.*

> We built two modules. The first screens the rock itself.
>
> **The input is a thousand geological grids.** From each we pull three numbers:
> **mean porosity** — how much empty space the rock has; **peak injection
> pressure** — how hard we end up pushing it; and **porosity standard
> deviation** — how uneven the rock is.
>
> Those become three criteria. **Capacity** adds — more pore space, more
> hydrogen, easier injection. **Seal risk** subtracts: peak pressure against the
> **fracture gradient**, the pressure at which the caprock breaks. And
> **heterogeneity** subtracts, because uneven rock makes flow unpredictable.
> **AHP-derived weights** — set by pairwise comparison, not by us picking round
> numbers — into one score out of a hundred.
>
> **The output is a ranked database of all one thousand candidates** — before a
> single fault question is asked.
>
> Those weights are ours, and you're allowed to disagree. We re-scored under four
> different weightings: the tiers hold, so we report tiers — and **I'll hand you
> the weights at the end.**

---

## SLIDE 3 · Module two — will it leak  *(211 words)*

*On screen: the leakage flowchart, Part A above Part B.*

> The second module asks the harder question. Two halves.
>
> **Half one is a U-Net**, run once per site. Its inputs are two maps of the rock
> — **porosity**, the empty space, and **permeability**, how easily fluid moves
> through it — plus distance from the well and where we are in the
> injection-withdrawal cycle.
>
> **It outputs a pressure map and a hydrogen saturation map**, at every step
> across ten years. **One forward pass, under a second**, in place of the
> hours-long simulation it learned from — a thousand published runs by **Mao and
> colleagues.** And notice what's missing: **no fault.** The U-Net has never seen
> one.
>
> **Half two is XGBoost**, running thousands of times on that output. We compress
> the maps into forty-one physics numbers, then **suppose** a fault: this long,
> this wide, this permeable. **Darcy's law** turns that fault plus the predicted
> pressure into a leak rate, and XGBoost forecasts **the probability of elevated
> leakage six months ahead.**
>
> Because the fault was never an input to the U-Net, half two is nearly free —
> **twenty thousand fault hypotheses, where a simulator tests one or two.**
>
> Two checks. Swap our predicted maps for the **real simulator maps** and the
> score barely moves — **0.9941 against 0.9842.** And we split train from test
> **by simulation, not by row.**

---

## SLIDE 4 · What that is worth  *(177 words)*

*On screen: the cheap-mitigation / catastrophic-failure corner of the sweep —
unaided ≈ 0 % vs screened 21.5 %; the measured cost line.*

> So what's that worth?
>
> You already run this calculation before buying a seismic survey: **is the
> information worth more than the survey?** That's **value of information.** Not
> "how much does this save," but **how much does knowing it change what you
> decide.**
>
> So take the case that actually matters here. Mitigation is cheap — re-cement a
> well, lower the injection pressure. A containment failure is not. In that
> corner, an operator working from **two exact simulator runs captures
> essentially zero** of the available decision value. Our screen recovers
> **twenty-one percent.** **The gap is widest exactly where the downside is
> worst.**
>
> And what you'd be buying is **an auditable risk statement** — every input
> tagged **dataset, derived, or assumed**, and exportable. What a permit file, an
> insurer, or an audit actually needs. **We'd sell it as a co-screening study on
> a decision you're already taking — priced under what the information is worth.**
>
> The cost of it is measured, not projected: one screening pass is **a fraction
> of a paisa** of compute, and **a thousand more fault hypotheses cost nothing
> extra.**

---

## SLIDE 5 · Since round one, and what's next  *(207 words)*

*On screen: shipped column vs roadmap column.*

> Four things changed since the last round.
>
> **One** — a geologist can now **enter their own site**: area, thickness,
> porosity, depth, caprock, and get capacity and a pressure ceiling back.
>
> **Two** — we caught our own model scoring too well. We were reporting twelve
> months, but a storage cycle **is** twelve months, so copying today already
> scored 0.99. A calendar, not a forecast. **We moved to six months** — where
> copying today scores **0.02**, and we still score **0.99**.
>
> **Three** — the surrogate is now **two U-Nets, not one**: pressure is smooth and
> global, saturation has a sharp front, so each map gets its own model.
>
> **Four** — the caprock now **weakens with time.** Hydrogen reacts slowly with
> the seal. We used to hold its strength fixed and stay conservative — now we
> model the chemistry.
>
> Next is natural gas storage: the **Ministry of Petroleum and Natural Gas** is
> building strategic natural gas reserves in indicated reservoirs, targeting
> **fifteen percent gas in the energy mix by 2030**. Our model can easily be extended
> for CH4, which is needed in the dataset: methane sits within twelve percent of
> hydrogen's buoyancy, so that is **one retraining run.**
>
> Then **fault self-healing**: faults reseal as minerals precipitate, and today we
> hold them permanently open.
>
> What we want isn't capital. **One real depleted-field dataset, and one pilot
> alongside a decision you're already taking.**

---

## LIVE DEMO — 1:15, hard stop  *(144 words + clicking)*

*Page open at section 01, the Storage Atlas. You use **sections 01 and 02 only**
— stop before section 03. Cycle ribbon left playing so the plume is already
moving when you arrive at it.*

> Both halves of that, live.

**Beat 1 — the atlas (≈12 s).** *One slow orbit. Don't fly it.*

> A thousand realisations, scored by the pipeline you just saw. Right is
> capacity, up is seal risk, colour is the score — real output, embedded in the
> page.

**Beat 2 — the weights (≈20 s).** *Click **Seal-led**. Let the reshuffle land
before you speak again.*

> These weights are ours, and you're allowed to disagree. Watch. [click]
> **The whole ranking reshuffles.** Tiers hold; the top ten moves two to five
> seats. That's why we report tiers, never a winner.

**Beat 3 — take one site down (≈8 s).** *Click a high-scoring point, then scroll
to section 02 in one motion.*

> Click a site, and it becomes the site every panel below is about.

**Beat 4 — the breathing reservoir (≈35 s).** *Let the ribbon run through an
injection-to-withdrawal turn. Then hover a fault segment on the slab.*

> This is the duty cycle, illustrated — ten years of injection and withdrawal.
> **The plume grows and shrinks with it**, and that motion is what half one
> actually predicts.
>
> And the fault hypotheses are drawn **where they are**: the dangerous ones sit
> on the plume front, along the pressure ridge. The worst one punches straight up
> through the caprock — that vertical path **is** the leak.
>
> Thank you.

---

# If a judge pushes

**"Your write-up says 99.7 percent. You quoted twenty-one. Which is it?"**
> Both, at different points of the same sweep. 99.7 % is the efficiency at a
> moderate mitigation-to-failure cost ratio; 21.5 % is the hardest corner we
> swept, where mitigation is nearly free relative to failure. We quote the hard
> corner on stage because that's the regime a containment incident actually sits
> in — and because the unaided baseline is pinned near zero across the entire
> sweep, so the gap is the result either way. It's a ratio against perfect
> information, not an accuracy.

**"Ninety-nine point seven, or twenty-one — either way it sounds too good."**
> It's high because coverage is what's scarce, not accuracy — twenty *exact*
> simulator runs still score essentially zero on the same scale, because two or
> twenty samples can't resolve a continuous fault-property space. And we checked
> it isn't an artefact of our own surrogate: we re-ran the whole calculation on
> true simulator fields instead of predicted ones, and decision efficiency moved
> by 0.0002.

**"What does a screening pass cost us, not you?"**
> We don't have a price for you yet, and I'd rather say that than invent one.
> What we can tell you is the floor, because we measured it: **0.652
> vCPU-seconds** per pass, which is a fraction of a paisa of compute, and the
> marginal cost of an extra fault hypothesis is statistically indistinguishable
> from zero across a fifty-fold range. First engagement would be a paid
> co-screening study alongside a decision you're already taking; the ceiling on
> what it's worth is the VOI number, so the pricing conversation has arithmetic
> on both ends rather than a quote.

**"How do you know the leakage model isn't just memorising the label?"**
> Three controls, reported together at the same six-month horizon. The full
> 41-feature model scores PR-AUC 0.9931. A two-feature weak baseline scores
> 0.1546. And "next period looks like this period" scores 0.0218. We also split
> by simulation, not by sample, at both stages, and assert disjointness at
> runtime.

**"Six months — why that horizon?"**
> Because storage repeats annually, at twelve months "same as today" is right by
> the calendar, not by forecasting. Six months is the point in the cycle where
> the field is doing the *opposite* of today. That's where a forecast has to earn
> it, so that's where we report.

**"Is the fault overlay circular? You add a fault to a model that predicted the field."**
> The fault is not an input to the network — the network sees geology only. The
> fault is introduced afterwards, which is exactly why we can Monte-Carlo over
> unknown fault properties in milliseconds. It answers "given this fault
> hypothesis, how bad is it," which is the question an operator actually has.

**"Your physics label — can it return something impossible?"**
> No, and that's asserted in code, not claimed in a report. Six monotonicity
> checks run as a test: flux rises with fault permeability and with overpressure,
> is exactly zero during withdrawal, is exactly zero below residual gas
> saturation, and is higher on the plume than off it. The suite exits non-zero if
> any fail.

**"What's it cost to run?"**
> 0.65 vCPU-seconds per screening pass. Adding hypotheses doesn't move it — we
> measured across a fifty-fold range and the slope is indistinguishable from
> zero. That flatness *is* the architecture: the fault isn't an input to the
> network, so more hypotheses don't re-run it.

**"How fast versus tNavigator?"**
> We've never timed tNavigator, so we don't quote a ratio. Multi-hour is their
> published framing, not our measurement.

**"So what do you actually sell?"**
> Not a simulator licence — we'd lose to tNavigator on features. We sell an
> auditable containment-risk statement, the thing a permit or an insurance file
> needs, with every input tagged by provenance. VOI is the pricing model: a
> rational operator pays less than the information is worth, so our ceiling is
> arithmetic rather than asserted. First engagement is a paid co-screening study
> alongside a decision you're already taking, then per-asset re-screening as the
> geological model updates.

**"Why not CO₂? That's where the money is."**
> Because we computed it, with CoolProp, at reservoir conditions. CO₂ is 61 times
> denser than hydrogen and its buoyancy contrast against brine is five times
> weaker. Caprock leakage is buoyancy-driven, so an H₂-trained model would
> mis-rank CO₂ risk systematically, not randomly. It's also injected
> monotonically, and our network has a cyclic-index input that would be
> meaningless. Methane, by contrast, sits at 0.88× hydrogen's buoyancy — that one
> transfers with a retrain.

**"Hydrogen storage barely exists in India. Who's the customer?"**
> About eight thousand tonnes a year commissioned against a five-million-tonne
> 2030 target — and that target isn't ours, it's the Ministry of New and
> Renewable Energy's, under the National Green Hydrogen Mission. The storage
> layer for it doesn't exist yet; that's the opportunity, and screening is the
> first thing it needs. It's also why the next market is natural gas storage:
> the Ministry of Petroleum and Natural Gas is building strategic natural gas reserves
> in indicated reservoirs (targeting 15% gas by 2030). Our model can easily be extended
> for CH4, which is needed in our dataset, for the same reservoir types and duty.
> GAIL, ONGC, and Petronet are all in this room.

**"You showed me a ranking. Can you actually run the model live?"**
> Yes — it's deployed, and the endpoint is in the submission: give it a held-out
> realisation and it returns the predicted fields and a scored fault ensemble.
> We kept it off the stage clock deliberately. A screening tool's credibility
> rests on what you can check afterwards, not on whether a request completes over
> conference Wi-Fi, so we showed you the thousand-site ranking that runs in the
> page and exports for you to audit. Happy to run one right now if you want it.

*(Only offer that last sentence if the service is warm and you have checked it
that morning. Cold start is 63 seconds, measured — a promise you can't land in
front of a panel costs more than the demo was worth.)*

**"Why two U-Nets? Wasn't one enough?"**
> Because the two targets fight each other. Pressure is smooth and global and
> flips sign between injection and withdrawal; saturation is local with a sharp
> plume front. A shared trunk has to compromise between those, and our own error
> curve flattened in a way that pointed at exactly that. Splitting them is the
> paper's own configuration — it trains one model per state variable — so this
> brings us back in line with the reference implementation rather than away
> from it.

**"What chemistry, and how fast does the caprock weaken?"**
> Hydrogen is reactive with the seal's mineralogy over storage timescales, so
> treating caprock strength as a constant across a ten-year cycle is an
> assumption we were making silently. It's now explicit and time-dependent, and
> the effect is small — which is the point: previously we absorbed it by staying
> conservative, and a conservative number you can't decompose is not a number an
> operator can act on. The rate parameters are `[ASSUMED]` and swept, same
> convention as every other assumption in the pipeline.

*(Be ready to name the mechanism and the rate you actually implemented. If a
geologist asks and the answer is vague, the honest reply is "the magnitude is
what we've characterised, not the specific reaction path" — do not invent a
mineral.)*

**"Show me the site-input screen you mentioned — I want to enter my own field."**
> It's a separate surface from the atlas you're looking at, and I'd rather walk
> you through it properly than hunt for it in the last thirty seconds. It takes
> area, net thickness, porosity, storage efficiency, depth, allowable
> overpressure, injection rate and years, and caprock thickness, and returns
> effective capacity, planned mass against that capacity, utilisation, and the
> hydrostatic pressure ceiling — a transparent volumetric screen, deliberately
> separate from the surrogate, because scalar inputs don't map into a model
> trained on gridded realisations. Happy to show it right after this.

*(If you can demo it on the day, do — but only if the build you're presenting
actually serves `/v1/site-screen`. Promising a click you can't make is worse than
describing it.)*

**"Is site #468 your best site?"**
> We report tiers, not a winner. Re-scored under four different weightings the
> broad ordering holds — Spearman 0.73 to 0.96 — so which tier a site lands in is
> a robust statement, and that's the statement we make. The weights are on the
> CLI and in the UI precisely so you can disagree with them.

---

# Demo checklist — before you walk up

**Page:** the Storage Atlas build (`feat/cloud-run-deployment`), sections 01 and
02. **No live mode** — the demo touches nothing that needs the API.

1. **You do not need the network, and that is the point.** The 1,000-row ranking
   is embedded in the page (~64 KB, straight from
   `outputs/site_suitability_ranking.csv`), and the re-weighting recomputes in
   the browser. It opens from disk if venue Wi-Fi dies — worth the clause it gets
   in beat 1.
2. **Confirm the 3D atlas actually rendered.** If WebGL is unavailable the page
   falls back to the flat view — same 1,000 points, so the demo still works, but
   beat 1's orbit line becomes "capacity across, seal risk up."
3. **Pick your point beforehand.** Know which high-scoring point you'll click in
   beat 3 and roughly where it sits under the default weighting, so it's one
   confident click and not a hunt in front of the room.
4. **Click Seal-led once in rehearsal, then Reset view** — so the ranking is at
   the default AHP weighting when you walk up, and beat 2's reshuffle is a change
   the audience can actually see happen.
5. **Leave the cycle ribbon playing** before you present, so the plume is already
   in motion when beat 4 arrives. A panel that starts moving *after* you point at
   it costs you five of the twenty-one spare seconds.
6. **Rehearse the scroll from atlas to reservoir as one motion.** It is beat 3's
   whole job, and hunting for the panel is the most likely place this demo eats
   its buffer.
7. **Stop at the end of section 02.** Section 03's attribution values are
   placeholders and section 04 is the internal build plan — neither should ever
   be on the projector.
8. **Slide 5 items three and four are landing an hour before you present.** If
   the split pressure/saturation U-Nets or the time-dependent caprock strength
   are **not** merged and running by the time you walk up, **cut that line from
   the slide and from the script.** Say "four things changed" or "two things
   changed" to match what actually shipped. A judge who asks to see an
   improvement that isn't there costs you more than the improvement was worth,
   and both of these are one-sentence lifts that need no stitching.

## How to narrate section 02 without getting caught

The reservoir panel carries its own badge — **"Preview field · procedural
illustration"** — and its fields, plume and fault swarm are generated, not
predicted. That is fine to show, and the script does show it, because what you
are demonstrating there is **the mechanism**, not a model frame. Two rules make
it safe:

1. **The word "illustrated" is in beat 4's first sentence. Keep it there.** It
   costs one word and it means a judge who reads the badge sees you already said
   it. Never say "this is the model's prediction" over that panel.
2. **Point the claim at the physics, not the picture.** "The plume grows and
   shrinks with it, and that motion is what half one predicts" is true and
   checkable. "Here is our predicted plume" is not.

**If a judge asks directly whether that render is model output:** *"No — that
panel is a procedural illustration of the cycle, and it says so. The model's
fields come from the deployed endpoint, and we can run one for you."* Answering
in one sentence, without flinching, converts the question into evidence of
discipline.

**Still off-screen, both of them:**

- **The "Recompute … measured in this browser" latency readout**, which times
  that procedural redraw and not model inference. Don't point at it and don't
  quote a millisecond figure from it.
- **The attribution chart in section 03** — real feature names, placeholder
  magnitudes. Stop scrolling at the end of section 02.

Everything in beats 1–3 — the atlas, the re-weighting, the per-site breakdown —
is real pipeline output, straight from `outputs/site_suitability_ranking.csv`.

## Three things not to say

- Any ROI, cost-per-kg, or avoided-cost figure. The efficiency ratio is the
  answer; a currency figure contradicts slide 4 two minutes later.
- Any speedup number against tNavigator or ECLIPSE.
- "Site 468 is the best site." Tiers or percentiles.

---

# Cut list

In this order. Each is one clean lift with no stitching. **Never cut the VOI
numbers or the pricing sentence on slide 4, or the ask on slide 5** — those are
the three things that were missing in round one and they are why the score
moves. The pricing sentence is what answers the jury's "industrial / commercial
impact" criterion out loud; nothing on the slides carries it.

Cuts 1–5 are the **delivery version** — take all five. Together they cost you
nothing you asked for: every named criterion still appears in the slide 2
pipeline graphic, all the improvements, both roadmap items, the pricing line and
the ask survive intact.

**Cut 1 — slide 2, the weights paragraph (−31 words → 6:46). Default.**
Lift *"Those weights are ours..."* through *"hand you the weights at the end."*
This loses nothing at all: **demo beat 2 makes the identical point**, with a live
reshuffle instead of an assertion. Take it first, always.

**Cut 2 — slide 1, the simulator paragraph (−22 words → 6:38). Default.**
Lift *"Checking that today means a full reservoir simulation. Hours per scenario.
So an operator tests one or two cracks and moves on."* Safe because slide 3
carries the same contrast — *"one forward pass, under a second, in place of the
hours-long simulation it learned from."*

**Cut 3 — run the demo compact, 1:00 instead of 1:15 (−15 s → 6:23). Default.**
Both panels survive; you just stop narrating the seams.
- **Fold beat 3 into beat 2.** Click your chosen point while the reshuffle is
  still settling, and say only *"— and this one becomes the site below."*
- **Trim beat 4's second half** to: *"And the fault hypotheses are drawn where
  they are — the dangerous ones sit on the plume front. The worst punches
  straight up through the caprock; that vertical path is the leak."*
- Orbit once, not twice, and don't wait for a full ribbon cycle — half a turn
  reads as motion.

**Cut 4 — slide 4, the value-of-information definition (−17 words → 6:17).
Default.**
Lift *"Not 'how much does this save,' but how much does knowing it change what
you decide."* The seismic sentence in front of it already makes that point in the
room's own vocabulary, and this audience does not need VOI defined twice.

**Cut 5 — slide 2, the three-criteria paragraph (−49 words → 5:58). Default.**
Now part of the delivery version, not a reserve. Lift from *"Those become three criteria"* to *"one
score out of a hundred."* You keep the three named inputs, the AHP line and the
ranked output, and the pipeline graphic still shows the criterion names — but you
lose the spoken geology, which is the reason this paragraph exists. This is the
price of the pricing sentence on slide 4, and it is worth paying: the jury scores
commercial impact, and the criterion names stay on screen either way.

---

**The deck is now content-saturated.** At 6:39 of material for a 6:00 slot, every
further addition needs a subtraction of the same size. If something new has to go
in on the day, take it out of slide 5's improvement list — three improvements
delivered well beat four delivered at speed.

**Do not cut the demo.** Four beats in 1:15 is already tight, and the two halves
are load-bearing in different ways: the atlas is the only real output the
audience sees with their own eyes, and the reservoir is the only place the
*mechanism* — plume breathing, faults on the pressure ridge — is visible rather
than described. Dropping either turns a slide claim back into an assertion. If
you are still over after cuts 1–3, take the tier-robustness line off slide 2
before you touch a beat.

---

# Recount after editing

Any edit invalidates the header table. Re-run this from the repo root:

```bash
python3 -c "
import re
b=open('docs/PRESENTATION_SCRIPT_FINALS.md').read().split('\n# If a judge pushes')[0]
w=[x for s in re.split(r'\n## ',b)[1:] for l in s.splitlines() if l.startswith('>')
   for x in l[1:].split() if re.search(r'[A-Za-z0-9]',x)]
n=len(w); print(f'{n} words')
for r in (150,160,170):
    t=int(n/r*60); print(f'  {r} wpm -> {t//60}:{t%60:02d} spoken')
"
```
