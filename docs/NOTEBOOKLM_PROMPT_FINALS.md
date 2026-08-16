PROMPT — paste everything below into NotebookLM
--------------------------------------------------------------------------------

You are building a **5-slide presentation deck for the MC²+ Grand Finale** (hackathon final round). There is no separate cover slide and no closing slide: slide 1 is title and problem together, and the talk ends on slide 5 followed by a live demo in a browser.

**Critical constraint — this is the opposite of a read-alone deck.** A presenter stands in front of the judges and speaks continuously for six minutes. The judges are *listening*, not reading. Every sentence of the argument is delivered out loud. The slides exist only to give the ear something for the eye to hold onto.

This changes how you must build every slide:

- **The slide is not the argument. The speaker is.** The slide carries the picture, the number, and the label — never the reasoning.
- **Hard text budget: 45 words maximum of body copy per slide**, and fewer is better. A slide with one diagram, four labels and one number is a *good* slide.
- **Never write a full sentence in body copy.** Fragments and noun phrases only. "Hours per scenario." not "Checking that today means a full reservoir simulation which takes hours per scenario."
- **Slide titles are short — six words or fewer.** They are signposts, not claims. "Which rock is worth storing in", not a full-sentence thesis.
- **Visuals must occupy at least 60% of every content slide.** If a slide has no diagram, chart, number-block or schematic, it is broken — rebuild it.
- **Nothing on a slide may duplicate a sentence the presenter says.** A judge who reads ahead has stopped listening. Slides show *structure and quantity*; the speaker supplies meaning.
- **Every number must be readable from the back of a hall.** Headline numbers set very large (54–72 pt). No number is allowed to hide inside a paragraph.
- Do not add content that is not in this prompt. Do not invent statistics, currency figures, comparisons, speedup ratios or citations. Every number you need is supplied below.

--------------------------------------------------------------------------------
PART 1 — DESIGN THEME AND COLOUR PALETTE
--------------------------------------------------------------------------------

**Theme: "Field Notebook"** — unchanged from the previous round. This deck must be visually continuous with it.

The deck should look like a geologist's field notebook: kraft paper, dark umber ink, forest-green annotations, brick-red markings for danger. It is warm, analog, and precise — the aesthetic of someone who writes measurements down carefully by hand.

This is deliberate. The project's entire argument is that its numbers are honestly sourced and independently checkable. A warm, hand-recorded, notebook aesthetic reinforces that claim; a glossy corporate-tech aesthetic would undercut it.

Hold the theme consistently. Do not mix in gradients, glassmorphism, neon, drop shadows, or stock photography. Flat colour, thin rules, generous margins, and precise typography only.

**Colour palette — use these exact values**

Surfaces and ink

| Role | Hex | Use |
|---|---|---|
| Page background | #EDE4D6 | Kraft paper. Every slide background. |
| Card / panel | #FAF5EC | Aged paper. Content cards, tables, callout boxes. |
| Recessed panel | #E4D9C6 | Sidebars, code blocks, secondary boxes. |
| Rule / border | #C9B79C | Thin 1px rules, table borders, card outlines. |
| Primary ink | #2B211A | Dark umber. Titles and body text. |
| Secondary ink | #6B5844 | Captions, labels, table headers. |
| Faint ink | #9C8871 | Footers, slide numbers, axis ticks. |

Meaning colours — each one means exactly one thing, everywhere

| Role | Hex | Means |
|---|---|---|
| Forest green | #2F6B4F | Hydrogen, storage capacity, "good", our model's result |
| Green highlight | #4A9B71 | Emphasis fills, plume gradient light end |
| Brick red | #B4441C | Pressure, flux, faults, "hot", the danger variable |
| Ochre | #96701A | Assumptions and caution notes |
| Oxblood | #7E1F2E | Failure, breach, negative results |
| Neutral grey | #8C8377 | Baselines and comparison bars — never our own result |

**Rule: our result is always forest green; the baseline it is compared against is always neutral grey.** This must hold on every chart in the deck.

Lithology ramp — use ONLY inside geological cross-sections

| Layer | Hex |
|---|---|
| Overburden | #BCA88E |
| Caprock (shale) | #4A3A2E |
| Reservoir sandstone | #D2A96F |
| Baserock | #7A6450 |
| Hydrogen plume | gradient #2F6B4F → #7FC79E |
| Fault plane | #B4441C |

**Typography & font sizes** — a spoken deck runs larger than a read deck. Sizes below are *increased* from the previous round; do not shrink them to fit more text in. If text does not fit, delete text.

- Slide titles: 40–44 pt, Humanist Serif (Charter, Source Serif, Georgia), Bold, Primary Ink #2B211A.
- Headline numbers / stat blocks: 54–72 pt, Monospace or Serif Bold, in the meaning colour that applies.
- Sub-headers and card headers: 24–28 pt, Semi-bold Sans, Primary Ink.
- Body fragments and bullets: 22–24 pt, Clean Humanist Sans (Source Sans, Inter, Lato), 1.4 line height.
- Diagram node labels: 18–20 pt Sans; diagram annotations (shapes, latencies, units): 16–18 pt Monospace.
- Figure captions: 16–18 pt, Italic or Semi-bold Sans, Secondary Ink #6B5844. **One line only.**
- Source labels and footers: 14–16 pt, Small Caps / Monospace, Faint Ink #9C8871.
- **Strict floor: nothing below 14 pt anywhere in the deck.**

**Layout**

- 16:9 ratio. Generous margins — at least 6% of slide width on every side.
- A thin #C9B79C rule under every slide title.
- Persistent footer on every slide, in faint ink #9C8871: slide number on the right, and on the left the standing line "Physics-guided screening. Real fields, derived labels."
- Content cards use #FAF5EC on the #EDE4D6 page, with a 1px #C9B79C border. No shadows.
- One idea per slide region. Never more than three regions on a slide.

**No provenance chips, tags or pills anywhere in this deck.** Do not render `[DATASET]`, `[DERIVED]`, `[ASSUMED]`, `[MEASURED]` or any bracketed label of that kind

**Pipeline / flowchart house style** — slides 2 and 3 are carried almost entirely by their diagrams. These are the two most important pictures in the deck; build them with more care than anything else.

- **Node shapes:** rounded rectangles, #FAF5EC fill, 1.5px #C9B79C border, #2B211A text.
- **Connectors:** clean 1.5px solid arrows in #6B5844 with open arrowheads. Never 3D, gradient or filled block connectors.
- **Group enclosures:** enclose each multi-step stage in a dashed #C9B79C container with a small-caps category label in the top-left margin of the container.
- **Annotations along connectors:** tensor shapes, feature counts and latencies in monospace (e.g. `128 × 128`, `41 features`, `< 1 s`, `~ms`).
- **Colour coding:** forest green #2F6B4F for geology and forward prediction; brick red #B4441C for fault parameters and leakage-risk branches; ochre #96701A for assumptions; neutral grey #8C8377 for baselines.
- **Loop markers:** annotate iterative stages with a ⟳ glyph and the iteration count (e.g. `⟳ ×20,000`).
- **Flow direction is left-to-right or top-to-bottom, never both in one diagram.** A judge must be able to trace the path in under three seconds while listening to someone talk.

--------------------------------------------------------------------------------
PART 2 — SLIDE-BY-SLIDE CONTENT
--------------------------------------------------------------------------------

Build exactly these 5 slides, in this order.

--------------------------------------------------------------------------------
SLIDE 1 — TITLE + THE PROBLEM, AND THE SIZE OF THE PRIZE
--------------------------------------------------------------------------------

This slide does two jobs — it introduces the team and it states the problem — so it must stay unusually light. Build it as a **masthead band across the top third, and the problem below it.** Nothing else.

**Masthead band** (on a #FAF5EC card, with a thin #C9B79C rule under it):

- Wordmark, 54 pt, left-aligned: **HyLeakAI**
- Subtitle, 22 pt, directly beneath the wordmark: Physics-guided leakage-risk screening for underground hydrogen storage
- **Team row, right-aligned in the same band, 20 pt — the names must be plainly legible from the back of the hall, not a decorative footnote.** Render as four small badge pills, each with the person's discipline beneath their name in 16 pt secondary ink:

  | Name | Discipline |
  |---|---|
  | Aryan Kandpal | Geology |
  | Brajesh Kumar Patel | Geology |
  | Sonil Negi | Economics |
  | Sourav Choudhary | Economics |

  Group the two Geology badges together and the two Economics badges together, and set a single label above the row, 18 pt small caps in secondary ink: `AN ALL-STUDENT TEAM · GEOLOGY + ECONOMICS`. Tint the two Geology badges' borders in the reservoir-sandstone tone #D2A96F and the two Economics badges' borders in forest green #2F6B4F, so the two disciplines read as a pairing at a glance. No photos, no logos, no role titles.

**Problem block** — a title line, three fragments, and the storyboard:

Title (40 pt): **Store it for months. Underground.**

Body — exactly three fragments, 24 pt, as a single numbered vertical column down the left third (never a paragraph):

1. Surplus in summer, demand in winter → **months, not hours**
2. Only porous rock is big enough → depleted gas fields
3. Pressure cracks the seal. **One unknown fault is enough.**

Visual — a **three-panel horizontal storyboard** occupying the right two-thirds of the problem block, panels separated by thin #C9B79C rules:

**Panel A — "seasonal mismatch".** A simple two-curve area chart, no axis numbers, axis labelled `Jan … Dec` in faint ink. Renewable supply curve peaking mid-year, demand curve peaking at both ends. Fill the summer surplus region in forest green #2F6B4F at 40% opacity, the winter deficit region in oxblood #7E1F2E at 40% opacity. Label the two regions in 16 pt: "surplus" / "deficit". No legend, no gridlines.

**Panel B — "the only container".** A small vertical cross-section using the lithology ramp: overburden, caprock (thin dark band), reservoir sandstone with a forest-green hydrogen plume flattened under the caprock, baserock below. One brick-red #B4441C fault plane cutting from reservoir up through the caprock, drawn as a jagged line with a small upward arrow head. Three labels only, 16 pt: `caprock`, `H₂ plume`, `fault — unknown`. Nothing else.

**Panel C — "the size of the prize".** A single broken-axis bar comparison, drawn very simply:
- one hairline bar labelled `≈ 8,000 t/yr commissioned today` in neutral grey #8C8377
- one full-width bar labelled `5,000,000 t/yr target · 2030` in forest green #2F6B4F
- above the green bar, a headline number block: **5 MMT/yr** at 60 pt, with `National Green Hydrogen Mission` beneath it at 16 pt in secondary ink.
Mark the axis break explicitly with a zigzag glyph so the comparison cannot be read as linear.

Caption (17 pt, single line, spanning all three panels): The storage layer for that target does not exist yet — and screening the fields is the first thing it needs.

Bottom strip — thin full-width band beneath the caption, 15 pt, left border in ochre #96701A:
Features are real physics: 1,000 published tNavigator simulations. Leakage labels are ours, derived from a hypothetical fault. This screens risk; it does not predict leak rates.

*This slide is allowed one extra region beyond the usual three, because it carries the masthead. It is not allowed extra words: the masthead, the three fragments and the caption are the entire text budget. Do not add a mission statement, a tagline, an institution name or a date.*

--------------------------------------------------------------------------------
SLIDE 2 — MODULE ONE: WHICH ROCK IS WORTH STORING IN
--------------------------------------------------------------------------------

Title (44 pt): **Module 1 — which rock is worth it**

Body: **no bullet list at all.** The pipeline diagram *is* the content. Only two pieces of text sit outside the diagram:
- a small kicker above the diagram, 20 pt, secondary ink: `1,000 candidates in · 1 ranked database out`
- the caption below it (see below).

Visual — **the site-suitability pipeline**, drawn left-to-right across the full slide width, in the flowchart house style. Four stages, three connectors. Build it to this wireframe (this is structure, not literal ASCII — render it as proper rounded-rectangle nodes with the specified colours):

```
 ┌──────────────────┐      ┌──────────────────────┐      ┌───────────────────────────────┐      ┌────────────────────────┐
 │ 1,000 geological │      │ 3 numbers per grid   │      │ 3 criteria, weighted          │      │ Ranked database        │
 │ grids            │ ───▶ │                      │ ───▶ │                               │ ───▶ │                        │
 │                  │      │  mean porosity  φ̄   │      │  ⊕ CAPACITY          0.50     │      │  score  0 – 100        │
 │ φ, k fields      │      │  peak inj. pressure  │      │  ⊖ SEAL RISK         0.30     │      │  1,000 candidates      │
 │ published sims   │      │  porosity std-dev σ(φ)│     │  ⊖ HETEROGENEITY     0.20     │      │  reported as TIERS     │
 └──────────────────┘      └──────────────────────┘      └───────────────────────────────┘      └────────────────────────┘
                                                          AHP pairwise weights
```

Diagram rules for this slide:
- `⊕ CAPACITY` and its weight in forest green #2F6B4F. `⊖ SEAL RISK` in brick red #B4441C. `⊖ HETEROGENEITY` in neutral grey #8C8377. The ⊕ / ⊖ glyphs must be visible at the back of a hall — they carry the "adds / subtracts" idea without a sentence.
- Under each criterion name, one three-word gloss in 16 pt secondary ink, and nothing longer: `more pore space` / `peak P vs fracture gradient` / `uneven rock` .
- Beneath the weights column, one small-caps line in 16 pt ochre #96701A: `AHP · PAIRWISE COMPARISON · OUR WEIGHTS, SWEPT`. No pill, no bracket.
- Enclose stages 2 and 3 in a dashed #C9B79C container labelled in the top-left margin, small caps: `SCORING · NO FAULT QUESTION ASKED YET`. This enclosure is the point of the slide — make the label legible.
- On the final node, render a small **tier ladder** instead of a list of site IDs: four stacked bands (Tier 1 → Tier 4) in a forest-green-to-kraft gradient, with `× 1,000` in monospace beside it. Do not print any site ID anywhere.
- Annotate the last connector in monospace: `Spearman ρ 0.73 – 0.96 across 4 weightings`.

Caption (17 pt, one line): Re-weight it and the tiers hold — which is why we report tiers, never a winner.

--------------------------------------------------------------------------------
SLIDE 3 — MODULE TWO: WILL IT LEAK
--------------------------------------------------------------------------------

Title (44 pt): **Module 2 — will it leak**

Body: again **no bullets.** The two-part flowchart is the slide. The only text outside the diagram is the caption.

Visual — **one diagram in two stacked halves**, each inside its own dashed #C9B79C container, Part A above Part B, with a single vertical connector between them. The visual contrast between the two halves is the entire message: A is a wide fan-in to one box; B is one box exploding into thousands of arrows.

**PART A container — small-caps label top-left: `PART A · RUNS ONCE PER SITE`. Right-margin annotation in monospace: `< 1 s`.**

```
   [ porosity map  φ ]  ┐
   [ permeability  k ]  ├──▶ ┌─────────────────────────┐ ──▶ [ pressure field   P(x,y,t) ]
   [ distance to well ] │    │  TWO U-NETS             │ ──▶ [ saturation field S(x,y,t) ]
   [ cycle index      ] ┘    │  P-net  ·  S-net        │
                             │  128 × 128 · 10 years   │
                             └─────────────────────────┘
                        ⚑  NO FAULT ENTERS THIS NETWORK
```

- The four input nodes: geology inputs (φ, k) in forest green #2F6B4F, the two positional/temporal inputs in secondary ink.
- The U-Net node is the largest node in the deck. Inside it, show the two sub-boxes `P-net` and `S-net` side by side, split by a thin rule, with a 16 pt monospace note beneath: `pressure is smooth & global · saturation has a sharp front`.
- Beneath the U-Net node, one line in monospace faint ink: `learned from 1,000 published tNavigator runs — Mao et al. (2025)`.
- The `NO FAULT ENTERS THIS NETWORK` flag is a full-width ochre-bordered strip, 20 pt small caps, sitting on the boundary between Part A and Part B. It is the hinge of the architecture — give it real visual weight, but keep it as a strip, not a box.

**PART B container — small-caps label top-left: `PART B · RUNS 20,000× PER SITE`. Right-margin annotation in monospace: `~ms`.**

```
   [ 41 physics features ]  ──┐
                              ├──▶ [ DARCY'S LAW ] ──▶ [ XGBoost ] ──▶  P( elevated leakage )
   [ supposed fault:          │      Q = k_f·k_rg·A_f          ⟳ ×20,000        + 6 months ahead
     length · width · perm ] ─┘      ────────────────
     ⟳ ×20,000                            μ · L
```

- The supposed-fault node is brick red #B4441C bordered and carries the `⟳ ×20,000` loop marker. Beneath it, one 16 pt ochre small-caps line: `HYPOTHESISED · NOT MEASURED`.
- The Darcy node shows the equation only, in monospace, no prose. Colour `k_f`, `A_f`, `μ`, `L` in ochre (assumed); colour the pressure and saturation terms in forest green (predicted).
- The output is a headline number block at the right end: **0.9931** at 60 pt in forest green, labelled beneath in 18 pt `PR-AUC · 6-month horizon`, with two small grey comparison bars stacked under it: `persistence 0.0218` and `weak baseline 0.1546`, both in neutral grey #8C8377. Bars must be to scale so the gap is visible without reading the numbers.
- Draw the fan-out in Part B literally: the arrow leaving the fault node splits into many thin repeated strokes before reaching XGBoost, so the eye sees "thousands" without a word being written.
- **Two validation lines, in small type, placed so a judge finds them while the presenter is talking about something else.** These answer the "0.99 is suspiciously high — what leaked?" reflex before it forms, so they must be present and legible, but never large enough to compete with the headline number:
  - Directly beneath the 0.9931 block, one 16 pt monospace line in secondary ink #6B5844: `real simulator maps 0.9941 · our predicted maps 0.9842`. Set the two values level with each other so their closeness is the visible message.
  - Beneath the XGBoost node, one 16 pt small-caps line in secondary ink: `SPLIT BY SIMULATION, NOT BY ROW`.

Caption (17 pt, one line): The fault was never an input — which is why 20,000 hypotheses cost about the same as one.

--------------------------------------------------------------------------------
SLIDE 4 — WHAT THAT IS WORTH
--------------------------------------------------------------------------------

Title (44 pt): **What that is worth**

Body — three fragments only, 24 pt, stacked in a narrow left column:
- Not "what does it save" → **what does it change**
- **Value of information** — the seismic-survey question
- Mitigation is cheap. Failure is not.

Visual — **the VOI sweep chart**, dominant, right two-thirds:
- X axis (log scale): `mitigation cost ÷ failure cost`, running from `1e-4` on the left to moderate ratios on the right. Label the left end in 16 pt: `cheap fix · catastrophic failure`. Label the right end `moderate`.
- Y axis: `decision efficiency` , 0 → 100%.
- **Our curve** in forest green #2F6B4F: rises from **21.5%** at the 1e-4 corner to **99.7%** at moderate ratios.
- **Unaided operator (2 exact simulator runs)** in neutral grey #8C8377: a flat line pinned at ≈ 0 across the entire sweep. Label it once, on the line: `2 simulator runs ≈ 0%`.
- Shade the leftmost corner of the plot with a faint oxblood #7E1F2E wash and pin a callout there: **21.5% vs ≈ 0%** with the sub-label `hardest corner — where the downside is worst`. This callout is the slide's headline number block; set 21.5% at 60 pt.
- No currency symbol appears anywhere on this chart, and no bracketed tag on either endpoint value.

Beneath the chart, a single thin **cost strip** in a recessed #E4D9C6 panel, one line, monospace 20 pt:
`0.652 vCPU-seconds per screening pass — measured` · `+1,000 fault hypotheses ≈ +0 cost`

Right-hand micro-panel, three fragments only, 20 pt, under the small-caps header `WHAT WE SELL`:
- an auditable risk statement
- `exportable · permit- and insurer-ready`
- **co-screening study** — priced under the VOI, per asset

Set the third fragment's lead phrase in forest green #2F6B4F so the commercial line is visibly the panel's conclusion. Do not add a price, a currency, a tier list or a subscription figure — "priced under the VOI" is the entire commercial claim the deck is allowed to make, and the presenter says the rest out loud.

Caption (17 pt, one line): A ratio against perfect information — not an accuracy, and not a currency figure.

--------------------------------------------------------------------------------
SLIDE 5 — SINCE ROUND ONE, AND WHAT'S NEXT
--------------------------------------------------------------------------------

Title (44 pt): **Shipped since round one · next**

Layout: two columns of equal width, separated by a vertical #C9B79C rule. No paragraphs anywhere. Every row is one line.

**Left column — header `SHIPPED` in small caps, forest green #2F6B4F.** Three numbered rows, 22 pt, each row a bold lead phrase followed by a short gloss in secondary ink:

1. **Horizon fixed: 12 mo → 6 mo** — copying today scored 0.99 at a 12-month cycle; at 6 months it scores 0.02 and we still score 0.99
2. **Two U-Nets, not one** — smooth pressure and sharp saturation front get separate models
3. **Caprock weakens with time** — seal strength now time-dependent, no longer a fixed constant

For row 1, render the contrast as a tiny inline bar pair rather than as text where possible: green `0.99` versus grey `0.02` at the 6-month horizon, with `12 mo — disqualified: periodicity` hatched out in neutral grey.

**Build constraint: each of the three rows must be independently deletable without breaking the column layout or leaving an orphaned number.** Rows 2 and 3 may be cut on the day, and the header must still read "shipped" without any count that contradicts what remains. Do not put a total count ("three things") anywhere on the slide.

**Right column — header `NEXT` in small caps, secondary ink.** Two rows only, 22 pt:

1. **Natural gas storage** — India's first strategic reserve · 15% gas by 2030 · depleted fields preferred · methane within 12% of hydrogen's buoyancy → **one retraining run**
2. **Fault self-healing** — faults reseal as minerals precipitate; today we hold them permanently open

Beneath both columns, a full-width band in a #FAF5EC card with a 1px ochre #96701A left border — this is the ask, and it must be the last thing the eye lands on. Keep it plain and short:

- Line 1, 26 pt bold, centred: **What would help most: more field data.**
- Line 2, 20 pt, centred, secondary ink: different reservoir types · real depleted fields · methane, for the gas-storage retrain

Do not phrase the ask as a rejection of anything ("not capital", "no funding needed"), and do not name a funding amount, a partner type or a commercial term. It is a request for data, stated once, in plain words.

Caption: none. Do not add one — the ask is the closing beat and nothing may sit under it.

**This is the last slide.** The presenter switches to a live browser demo immediately after it and says "thank you" there, so build no demo-transition slide, no thank-you slide, and no closing summary. On this slide only, replace the footer's left standing line with `GitHub: Sonil15/HyLeakAI` in the same faint ink #9C8871 — that is the only place a link appears in the deck.

--------------------------------------------------------------------------------
PART 3 — RULES YOU MUST NOT BREAK
--------------------------------------------------------------------------------

Check the finished deck against every line below.

**Spoken-delivery rules**
1. No slide may exceed 45 words of body copy. Count them. If a slide is over, delete — never shrink the font.
2. No body copy may be a complete sentence. Fragments only. (Titles, the honesty strip and the ask on slide 5, and the caption lines are the only exceptions.)
3. No slide may contain more than one headline number block.
4. Every slide must carry a diagram, chart, schematic or number block occupying at least 60% of its area.
5. Captions are one line, and there is at most one caption per slide. Slide 5 has none.
5b. Slide 1's team badges are content, not decoration: four names, each with its discipline, at the specified size. Do not shrink them to make room for the storyboard — shrink the storyboard.

**Claim rules**
6. Do not include any ROI, cost-per-kg, avoided-cost, revenue or price figure anywhere in the deck. The efficiency ratio is the answer; a currency figure contradicts slide 4. The words "co-screening study — priced under the VOI, per asset" on slide 4 are the deck's only commercial claim, and they carry no number.
7. The only currency-adjacent figure permitted is our own measured compute cost — `0.652 vCPU-seconds per screening pass`. Do not convert it into money.
8. Do not quote any speedup ratio against tNavigator, ECLIPSE, or any commercial simulator. We never timed one. "Hours per scenario" is their published framing; it may appear only as a fragment, and only on slide 1.
9. Never name a best site. No site IDs anywhere in the deck. Tiers or percentiles only.
10. 99.7% and 21.5% must never appear without their cost-ratio position on the same chart. They are two points on one sweep, not two competing claims.
11. Do not describe the efficiency ratio as an accuracy. Label it `decision efficiency` and nothing else.
12. Do not claim 3D reservoir prediction. The grid is 128 × 128 × 1.
13. Do not say the model was trained on leakage ground truth. There is none — leakage labels are derived from a stated physics model and tagged.
14. Do not state a binary caprock-breach rate anywhere.
15. Do not quote any PR-AUC at a 12-, 24- or 30-month horizon without its persistence baseline beside it, and mark those horizons as disqualified by periodicity wherever they appear.
16. Do not claim to reproduce the source paper's accuracy.
17. Do not include a screenshot, mockup or still frame of the live demo page anywhere in the deck. The demo is live; a preview competes with it and the reservoir panel in that page is a labelled procedural illustration, not model output.
18. Do not put feature-attribution magnitudes on any slide — those values are placeholders in the current build.
19. Do not add any statistic, citation, company name, logo or comparison that does not appear in this prompt.

**Craft rules**
20. Our result is forest green; the baseline it is compared to is neutral grey. No exceptions, on any chart.
21. The deck must remain readable in greyscale and when printed — every colour distinction must also be carried by position, label or hatching.
22. Slide 5's three "shipped" rows must each be deletable on the day without breaking the layout, and no count of them may appear on the slide.
22b. No provenance chips, pills or bracketed tags anywhere — `[DATASET]`, `[DERIVED]`, `[ASSUMED]`, `[MEASURED]` and any equivalent are banned in every slide, diagram, chart label, table cell and caption. Sources and caveats appear as plain small-caps lines only.
22c. Slide 3's two validation lines (`real simulator maps 0.9941 · our predicted maps 0.9842` and `SPLIT BY SIMULATION, NOT BY ROW`) are not decoration and may not be dropped for space. They are small type by design — if the slide is crowded, shrink the diagram's white space, not these.
23. Slides 2 and 3 are the two diagrams the whole talk rests on. If anything in this deck gets extra design attention, it is those two — trace-in-three-seconds legibility, generous white space, and no annotation smaller than 16 pt.
24. Five slides. No cover slide, no agenda slide, no demo-transition slide, no thank-you slide, no appendix. If a piece of content has nowhere to live in these five, it does not go in the deck.
