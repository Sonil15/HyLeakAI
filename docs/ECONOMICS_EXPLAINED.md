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

## 6. When our tool could actually hurt (and why that's fine)

There's a mathematically real corner case: if fixing a potential leak is
extremely cheap compared to the cost of a failure, the safest move is basically
"always mitigate, don't even bother checking." In that narrow situation, our
tool could talk someone out of mitigating when they shouldn't be talked out of
it — making things slightly worse.

We calculated exactly where that boundary is, and it sits **way below** any
realistic cost scenario we'd actually see in practice. We report it anyway,
because knowing your tool's limits is more trustworthy than pretending it has
none.

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
guesses:

| Fluid | How similar to hydrogen | Can we use our model? |
|---|---|---|
| Natural gas (CH₄) | Very similar behavior underground | **Yes** |
| CO₂ | Behaves quite differently (weaker buoyancy, injected differently) | **No, not yet** |

We're deliberately **not** claiming we can do CO₂ storage risk assessment, even
though CO₂ storage (CCUS) is a bigger funded market in India right now. Our
physics doesn't transfer cleanly to CO₂, and claiming it does would be
dishonest. We'd rather say "not yet" than oversell.

**Our near-term plan:**
1. **Now:** hydrogen storage (small market today, but where our tool was built for).
2. **Next:** natural gas storage — India is actively building strategic gas
   storage in old depleted gas fields, which is the exact same kind of
   underground reservoir our tool understands. Big near-term opportunity.
3. **Not yet:** CO₂ storage — physics doesn't transfer, so we don't claim it.

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
