# MC²+ Grand Finale — 4–5 Minute Script

**Spoken words: 788** (counted, not estimated — recount with the snippet at the
bottom after any edit). Plus ~20 s of clicking in the demo:

| Delivery pace | Total |
|---|---|
| 150 wpm — deliberate | 5:35 |
| **160 wpm — normal** | **5:15** |
| 170 wpm — brisk | 4:58 |

**If your slot is hard-capped at 5:00, take cuts 1 and 2 from the cut list at the
bottom (−78 words) and you land at 4:46 at 160 wpm.** Do not plan to speak at 170
to make the time — nerves make people faster and less clear, and the economics
block is the one that must land.

Compressed from the 912-word round-one script (`PRESENTATION_SCRIPT.md`, 5:52)
using its own prepared cut list, then extended with the economics block. What
changed and why:

- **Slide 6 (six physics rules) cut to one sentence.** It was 60 words defending
  a point nobody challenged.
- **Slide 8 (parameter counts, 124M vs 7M) cut.** The 86.4% and the one-percent
  ranking shift survive; the hardware story does not.
- **Slide 10 (impact) folded into the economics block**, where it now has numbers
  behind it instead of adjectives.
- **New: the economics block.** This is the whole reason we are here — a judge
  asked how we make a business of this and we had nothing.

Two rules, unchanged: short sentences, and never say a number without saying what
it means.

---

## 0:00–0:19 — SLIDE 1 · Why these fields  *(50 words)*

> We're HyLeakAI.
>
> Hydrogen is how you store renewable energy for months instead of hours. But you
> need somewhere to put terawatt-hours of it.
>
> That place already exists: depleted gas fields. Only porous rock works at that
> scale — and that rock held gas for millions of years with nobody watching it.

---

## 0:19–1:07 — SLIDE 2 · The obstacle  *(128 words)*

> So why isn't this happening already?
>
> The seal is the rock above it. Hydrogen doesn't break it — pressure does, and
> storage is pressure.
>
> Then faults. A fault is a crack millions of years old. Nobody put it there, so
> nobody knows where it is.
>
> And here's what surprises people. The middle of a fault is crushed rock, packed
> tight enough to **block** flow sideways. But the rock around it is shattered,
> and that carries gas **upward** — straight through the seal.
>
> So a fault isn't a hole in your seal. It's a chimney through it. And one is
> enough.
>
> Industry checks this with a full simulator, and every new fault is another
> multi-hour run. So operators test one or two guesses and move on. The blocker is
> the clock.

---

## 1:07–2:01 — SLIDES 3 → 5 · How it works  *(143 words)*

> Three steps.
>
> **One — the input is rock.** A site is two maps: how much empty space the rock
> has, and how easily fluid moves through it.
>
> **Two — the AI predicts the physics.** From that rock it predicts pressure and
> hydrogen everywhere, across ten years of filling and emptying. Milliseconds. It
> learned from a thousand published simulations — Mao and colleagues, open
> licence. And notice: no fault in this step.
>
> **Three — the safety question, separately.** Nobody knows whether a fault
> exists, so we suppose one: here, this leaky, this wide. We look up the pressure
> and hydrogen the AI already predicted there, and compute how much escapes.
> Darcy's law.
>
> Step two already happened, so step three is nearly free. That's why we test
> twenty thousand faults instead of one — twenty thousand **guesses about one
> crack**. **That paper stops at step two. Step three is ours.**

---

## 2:01–2:55 — SLIDES 6 → 7 · Why believe it  *(143 words)*

> Why believe the number. Three things.
>
> The physics is enforced, not learned. Spread hydrogen too thin and it's
> isolated bubbles, stuck in the pores. Bubbles don't flow, so the model returns
> **zero**. Six rules like that, and it cannot return an answer physics forbids.
>
> The forecast is tested where it's hard. Storage repeats yearly, so at twelve
> months "same as today" is right nearly every time — a calendar, not a forecast.
> So we test six months out, when the field is doing the **opposite** of today.
> There, "same as today" scores 0.02 out of 1. We score 0.99.
>
> And our AI is blurrier than the simulator — 86 percent, not 99. So we scored
> the risk twice, once on simulator maps, once on ours. **The ranking moved by one
> percent.** Good enough to screen; not to quote leak rates, which is why we don't.

---

## 2:55–3:33 — LIVE SITE  *(49 words + ~20 s of clicking)*

*Tab already open, already scrolled to the atlas.*

> This is deployed. One page, no server.
>
> A thousand candidate sites. Across is capacity, up is seal risk. Real output.

**Click SEAL-LED. Let it reshuffle.**

> How we weight that is our assumption. So watch. [click] The ranking reshuffles.
> That's why we never name one best site.
>
> Every number is tagged: dataset, derived, or assumed.

---

## 3:33–4:44 — SLIDE · The economics  *(197 words)*

**This is the block that did not exist last round. Do not rush it.**

> Last time, one of you asked how we'd make a business of this. We had no answer —
> economics was the one module our README marked *not started*.
>
> So we built it. And it does **not** report an ROI.
>
> An ROI needs a leak rate, and no leakage ground truth exists anywhere in the
> world. That absence is why this project exists. Pricing our own uncalibrated
> label would be a guess wearing a dollar sign.
>
> So we compute what petroleum decision analysis already uses: **value of
> information.** What is knowing this worth, in decisions changed?
>
> A site has one unknown fault, and nobody ever sees it. An operator estimates its
> risk from two exact simulator runs. We estimate it from twenty thousand
> approximate ones.
>
> Two exact samples capture **zero** percent of the available decision value.
> Twenty thousand approximate ones capture **ninety-nine point seven**. It's a
> ratio — no currency in it, because there's nothing honest to put there yet.
>
> We also found where we'd be worth **less than nothing** — when mitigation is so
> cheap you'd do it anyway. It sits outside the range we think is credible, and we
> report it anyway. A test fails if it ever disappears.

---

## 4:44–5:15 — SLIDE · Where this goes, and the ask  *(78 words)*

> Next market is natural gas storage. Same depleted fields, same
> inject-and-withdraw cycle. We computed the fluid properties rather than
> assuming: methane sits at twice hydrogen's viscosity. **Carbon dioxide sits at
> eight times, and five times weaker on buoyancy — so we're not claiming it.**
>
> What we need isn't capital. It's **one real depleted-field dataset**, and **one
> pilot alongside a decision you're already taking.**
>
> We spent as much effort proving what our numbers don't mean as producing them.
> Thank you.

---

# If a judge pushes

**"Ninety-nine point seven percent sounds too good."**
> It's a ratio against perfect information, not an accuracy. And it's high
> because coverage is what's scarce, not accuracy — twenty exact simulator runs
> still score zero on the same scale. The screen's own ceiling is set by how well
> we've measured its error rates, and that rests on about three hundred positive
> held-out rows. More hypotheses can't raise it.

**"Your labels are your own physics. So the economics is circular."**
> The efficiency number says how much of the *available decision value* we
> capture. It does not say the label is right. That's exactly why the ask is a
> real field dataset — we built the label as a swappable module so that
> substitution is a config change.

**"Why not CO₂? That's where the money is."**
> Because we computed it. At reservoir conditions CO₂ is 61 times denser than
> hydrogen and its buoyancy contrast against brine is five times weaker. Caprock
> leakage is buoyancy-driven, so an H₂-trained model would mis-rank CO₂ risk
> systematically, not randomly. It's also injected monotonically, and our network
> has a cyclic-index input that would be meaningless. We'd need to retrain, and
> we'd tell you that before taking your money.

**"What's it cost to run?"**
> One screening pass is 0.65 vCPU-seconds. Adding fault hypotheses doesn't move
> it — we measured across a fifty-fold range and the slope is indistinguishable
> from zero. That flatness *is* the architecture: the fault isn't an input to the
> network, so more hypotheses don't re-run it.

**"How fast versus tNavigator?"**
> We've never timed tNavigator, so we don't quote a ratio. Multi-hour is their
> published framing, not our measurement.

---

# Demo checklist — before you walk up

1. Warm the API. **Cold start is 63 seconds** — measured, free tier. Hit it
   within 15 minutes of presenting or it will spin down mid-demo.
2. Atlas tab open and pre-scrolled. Second tab on the economics panel.
3. If venue Wi-Fi dies: the page opens from disk. Say so — it's a design choice,
   not a save.

## Three things not to say

- Any ROI, cost-per-kg, or avoided-cost figure. The efficiency ratio is the
  answer; a currency figure contradicts the slide four minutes later.
- Any speedup number against tNavigator.
- "Site 468 is the best site." Tiers or percentiles — the top ten moves under
  re-weighting, and you demo exactly that.

---

# Cut list

In this order. Each is one clean lift with no stitching. **Never cut from the
economics block or the ask** — those are the two things that were missing last
round and are the reason the score moves.

**Cut 1 — the physics-rules paragraph, "Why believe it" (−45 words).**
Lift the whole block from *"The physics is enforced, not learned"* to
*"an answer physics forbids."* The forecast test and the one-percent ranking
result are the stronger evidence and they survive intact. If a judge asks whether
the model can return nonsense, the answer is in the Q&A bank.

**Cut 2 — the fault mechanism, slide 2 (−33 words).**
Lift *"And here's what surprises people... straight through the seal."* Keep
*"So a fault isn't a hole in your seal. It's a chimney through it."* — the image
lands without the geology lecture behind it.

> Cuts 1 + 2 = **−78 words → 710 → 4:46 at 160 wpm.** This is the recommended
> pair for a hard 5:00 cap.

**Cut 3 — slide 1's second half (−22 words).**
End at *"you need somewhere to put terawatt-hours of it. That place already
exists: depleted gas fields."* Weakens the "nature already tested the seal"
point, so take cuts 1 and 2 first.

**Cut 4 — "How it works", step one (−25 words).**
Fold into step two: *"From two maps of the rock, the AI predicts pressure and
hydrogen everywhere..."* Only if you are still over after 1–3.

---

# Recount after editing

Any edit invalidates the header. Re-run this from the repo root:

```bash
python3 -c "
import re
b=open('docs/PRESENTATION_SCRIPT_FINALS.md').read().split('# If a judge pushes')[0]
w=[x for s in re.split(r'\n## ',b)[1:] for l in s.splitlines() if l.startswith('>')
   for x in l[1:].split() if re.search(r'[A-Za-z0-9]',x)]
n=len(w); print(f'{n} words')
for r in (150,160,170):
    t=int(n/r*60)+20; print(f'  {r} wpm +20s demo -> {t//60}:{t%60:02d}')
"
```
