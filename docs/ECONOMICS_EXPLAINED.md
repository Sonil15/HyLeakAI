# Economics and Impact — explained simply

This is a plain-language walkthrough of `Economics_and_impact.md` (the full
technical version) and `docs/COMMERCIAL.md` (the slide-ready version). Read this
one if the other two are hard to follow.

---

## 1. Why we built this at all

A judge asked "how will you make money from this?" and we had no answer. So we
built a module (Module 4) whose whole job is to answer that question honestly.

---

## 2. Why we didn't just calculate ROI ($ saved)

The obvious business pitch is: "our tool saves you $X per year." We can't say
that, because it requires knowing the **real** hydrogen leak rate at a site —
and nobody on Earth has that data. Our leak numbers come from our own physics
simulation, not from a real measurement. Multiplying an unverified number by a
dollar sign would look precise but actually be made up.

So instead of ROI, we use something called **Value of Information (VOI)**. It's
a standard tool from oil & gas decision-making. Instead of asking "how much
money does this save?" it asks:

> **"How much does having this information change what you'd decide to do?"**

This works even without knowing the true leak rate, because it's measuring the
*decision*, not the dollar amount.

---

## 3. The decision being modeled

Imagine a hydrogen storage site. There might be a crack (fault) that leaks. The
operator has two choices:

- **Proceed** with injection as planned.
- **Mitigate** — spend extra money on appraisal, safer pressure, or relocating
  the well.

If they proceed and there really is a dangerous crack, that's a costly failure.
VOI measures how much better their decision gets if they use our tool instead
of guessing.

---

## 4. Our real advantage: we cover more ground, not that we're more "accurate"

This is the part that's easiest to misunderstand, so here's the analogy:

- There's **one** crack at a site, and nobody — not us, not the operator —
  actually knows if it's there or how bad it is.
- An operator, without our tool, can only afford to run **2** expensive physics
  simulations to guess. With only 2 tries, their answer is basically "definitely
  no," "definitely yes," or "50/50" — very crude.
- Our tool can cheaply check **20,000** different guesses about where a crack
  could be and how bad it could be. That's much finer-grained.

So our edge isn't that we're smarter — it's that we can afford to check way more
possibilities. Think of it like: instead of flipping a coin twice to guess a
percentage, we flip it 20,000 times. More flips = a much better estimate, even
with the same coin.

**Important limit:** because we already check so many possibilities, checking
even more won't help further. The thing holding us back now isn't the number of
guesses — it's how well-calibrated our underlying model is. That's a real
ceiling, and we say so upfront instead of waiting for a judge to catch it.

---

## 5. The headline number

- Unaided operator (2 guesses): captures **0%** of the value that perfect
  information would give them.
- Our tool (20,000 guesses): captures **99.74%** of that value.
- Perfect information (impossible in real life): 100%, by definition.

This "99.74%" is a **ratio**, not a dollar figure. It says "we get you almost
all the way to a perfect decision," without claiming to know what a perfect
decision is worth in rupees.

---

## 6. The other side of the ledger: what it costs to miss a leak

What happens if there's no tool at all, and a real leak simply goes unfound?

We still won't invent a dollar figure for this — see [Section 2](#2-why-we-didnt-just-calculate-roi--saved)
for why. But the VOI math already contains this scenario, because "cost ratio"
in our sweep is exactly *mitigation cost ÷ failure cost*. The **worst case for
missing a leak** is where that ratio is smallest: mitigation is cheap, but
failure is enormously expensive relative to it. That's not a hypothetical for
hydrogen storage — it's the realistic shape of the risk. Catching a bad fault
early might mean re-cementing a well or lowering injection pressure. Missing
one can mean an uncontrolled subsurface release, a well integrity failure, an
ignition risk given hydrogen's wide flammability range, site abandonment,
environmental remediation, and the regulatory and reputational fallout of a
storage-safety incident — costs that are categorically larger than the fix
would have been.

At the cheap-mitigation / expensive-failure end of our swept range
(cost ratio **0.0001**, from `outputs/voi_results.json`):

- An **unaided operator** (2 simulations) captures essentially **0%** of the
  value perfect information would give them (efficiency ≈ 2.5 × 10⁻¹⁴) — with
  only two guesses, they are statistically no better than not looking at all.
  In this regime, that near-zero efficiency **is** the cost of not finding the
  leak: whatever the failure ends up costing, an unaided operator's process
  gives them almost no chance of catching it in time to matter.
- **Our tool** (20,000 screened hypotheses) still recovers about **21.5%** of
  that value even in this hardest corner — worse than our headline 99.74%
  (which is measured at a more moderate cost ratio), but nowhere near zero.

The gap between those two numbers *is* the case for the product: it's largest
exactly when the downside of missing a leak is largest. As the cost ratio
moves toward more moderate territory, the unaided operator's efficiency stays
pinned near zero throughout the whole sweep, while ours climbs past 99% — so
the more expensive a missed leak is relative to fixing it, the more that gap
matters.

---

## 7. The one number that's real money: what it costs us to run

Everything above is a ratio (no currency). But we do know exactly what it costs
**us** to operate the service, because we can time it:

- One screening run: about **6.5 seconds** of compute time, on a tiny sliver of
  a processor.
- Checking more fault hypotheses (going from 1 to 50) costs **basically nothing
  extra** — the compute cost doesn't scale up with how many guesses we check.
- Startup delay on our current (free-tier) hosting: about a minute — that's a
  hosting limitation, not a product limitation.

The flat cost per extra hypothesis is the key selling point: our margins get
better, not worse, as we check more possibilities.

---

## 8. Which markets we're going after (and which we're not)

We picked our target fluids using real physics simulations (CoolProp), not
guesses. The test was: does an H₂-trained model transfer to this fluid, or
would it be quietly wrong?

| Fluid | Viscosity vs H₂ | Density vs H₂ | Buoyancy vs brine (vs H₂) | Can we use our model? |
|---|---|---|---|---|
| Natural gas (CH₄) | 1.93× | 10.4× | **0.88×** — close | **Yes** |
| CO₂ | 8.29× | 61.2× | **0.21×** — ~5× weaker | **No, not yet** |

Caprock leakage is a buoyancy-driven process, so that last column is the one
that decides transferability, not the market size. CH₄ sits close enough to
H₂'s buoyancy behavior to interpolate. CO₂ doesn't — its driving force against
brine is roughly five times weaker, so a model trained on hydrogen would
mis-rank CO₂ risk systematically (always in the same direction), not
randomly. CO₂ is also injected in one continuous push rather than the
cyclic inject/withdraw pattern our model is built around, and our network
architecture literally has a cyclic-index input channel that would be
meaningless for it.

### Why this matters: the two markets are very different sizes today

- **Hydrogen storage (our current market)** is small and early. India's
  National Green Hydrogen Mission targets 5 MMT/year by 2030; as of February
  2026, roughly **8,000 t/yr** has actually been commissioned. That gap
  between target and reality is real, and we say so — it's the market we
  were built for, not the market that pays the bills yet.
- **Natural gas storage (our next market)** is happening now, not in 2030.
  India has begun building its first strategic natural gas storage, and
  **depleted gas fields are the stated preferred option** — the same
  reservoir class, with the same cyclic inject/withdraw duty cycle as
  hydrogen storage. This is the market where our physics already applies
  and the buyers already exist.
- **CO₂ storage / CCUS (deliberately not our market, yet)** is the biggest
  funded opportunity in India right now — on the order of **₹20,000 crore**
  of committed CCUS budget. We are naming that we are walking past it. Our
  physics doesn't transfer cleanly, and claiming it does just to chase the
  bigger number would be dishonest — and it's exactly the kind of claim a
  technical judge would test first.

### Our near-term plan

1. **Now — hydrogen storage.** Small market today, but the one our tool was
   built and validated for.
2. **Next — natural gas storage.** Same reservoir class as hydrogen, active
   government buildout, and the fastest path to a paying pilot. This is
   where we're pointed.
3. **Not yet — CO₂ storage.** Bigger budget, wrong physics for our current
   model. We say "not yet," not "no" — see the technical steps below.

### The technical work to actually adapt the product

Moving to a new fluid isn't a rewrite. Most of the product is fluid-agnostic
by design, and only a narrow piece needs redoing per fluid:

| What has to happen | For CH₄ (natural gas) | For CO₂ |
|---|---|---|
| Fault-decoupling method | Transfers fully — it's a method, not a fitted model | Transfers fully |
| Core leakage physics | Transfers fully — swap one config constant (the fluid's viscosity) | Transfers fully |
| Network architecture & training recipe | Reused as-is (~4.2 hours to retrain on a free-tier GPU) | Would need the cyclic-index assumption redesigned first |
| Features, scoring, explainability, provenance tooling, API | Form transfers unchanged; only the fitted weights differ | Same, but only after the physics question above is resolved |
| Trained model weights | **New training run required** — one retrain per fluid, using real or simulated CH₄ leak scenarios | Not attempted until we can show buoyancy-driven leakage transfers, or get real CO₂ field data to fit against directly |

In short: the CH₄ expansion is one retraining run away, not a new product.
The CO₂ expansion would require either new physics work to justify the
transfer, or real observed CO₂ leakage data to train against directly —
which is a materially bigger lift, and why we're not promising it on a
near-term roadmap.

**What "eventually" would actually take, for CO₂ specifically:**

1. **Rebuild the injection-cycle assumption.** Our model assumes cyclic
   inject/withdraw. CO₂ is injected continuously, one direction only — the
   network's cyclic-index input channel would need to be redesigned, not
   just retrained.
2. **Re-derive the buoyancy physics**, not just recalibrate it. CO₂'s driving
   force against brine is ~5× weaker than H₂'s — this isn't a config-constant
   swap like CH₄, it's a genuinely different physical regime.
3. **Retrain from scratch, and validate it separately.** Because the physics
   differs, we couldn't trust a CO₂-trained copy of the same architecture
   without checking it actually captures CO₂'s different failure mode.
4. **Get real CO₂ leakage data to check against.** We can't lean on
   "close enough to H₂" the way we do for CH₄, so we'd need real observed
   data or a validated CO₂-specific simulator to confirm the retrained model
   is right, not just self-consistent.

---

## 9. What we actually sell

Not a simulator (we'd lose to established, feature-rich competitors like
tNavigator or ECLIPSE). Instead, we sell a **documented, provenance-backed
risk statement** — a number an operator can show to a regulator or insurer,
with a clear paper trail of exactly where every input came from.

**Pricing logic:** a customer should never pay more than the decision-value our
tool gives them (the VOI number from above). That keeps our pricing honest and
grounded in math rather than a guess.

**How we'd roll it out:**
1. Start with a paid pilot study alongside a decision a customer is already making.
2. Move to an annual subscription, re-screening as their models update.
3. Eventually take on an advisory role as storage safety regulations are written.

**What we're asking partners for (not money):**
1. One real dataset from an actual depleted field, so our leak-risk labels can
   be grounded in something real instead of pure physics simulation.
2. One real pilot study, run alongside a decision that's happening anyway.

---

## 10. What we explicitly do NOT claim

Being upfront about limits is part of the pitch, not a weakness:

- No dollar savings figure, no cost-per-kg, no "avoided cost" number.
- No speed or cost comparison against competitor tools — we've never run them
  ourselves, so we won't guess.
- No CO₂ storage capability.
- "99.74% efficiency" does **not** mean our leak predictions are correct — it
  means we make near-optimal use of whatever our model already knows. The
  underlying leak model itself is still unverified physics, which is exactly
  why we're asking for real data.

---

## 11. Two mistakes we caught ourselves, and why that matters

**Mistake 1:** Our first version of this analysis made our tool look like it
captured 100% of the value — suspiciously perfect. We dug in and found the setup
was flawed (it assumed there were ~387 leaky faults per site instead of the
realistic "one crack, unknown location"). Fixing the setup gave the more
believable 99.74% number.

**Mistake 2:** A sign error in one formula made our tool look like it could be
*harmful* in a much wider range of situations than it actually is. We caught it
during review, fixed it, and the corrected result was actually better for us —
which is exactly why it was worth double-checking instead of just accepting the
first (worse) answer.

**Why we're telling you this:** a team that finds and documents its own bugs is
more credible than one whose numbers "just look right."

---

## Where to go next

- Full technical detail: [`Economics_and_impact.md`](../Economics_and_impact.md)
- Slide-ready short version: [`docs/COMMERCIAL.md`](COMMERCIAL.md)
- Raw numbers: `outputs/voi_results.json`, `outputs/fluid_properties.json`,
  `outputs/unit_cost.json`, `outputs/assumption_register.json`
