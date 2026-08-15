"""Module 4 — the economics the first-round pitch promised and did not build.

Three modules, in descending order of how defensible their outputs are:

  fluids.py       CoolProp properties behind the "CH4 is the next market, CO2 is
                  not" claim. Self-calibrating against a constant we already
                  committed to in LeakageConfig.
  voi.py          Value of Information. Replaces the ROI that Document 9 asked
                  for and that we cannot honestly compute, with the framework the
                  petroleum industry already uses for exactly this question.
  unit_cost.py    What a screening pass costs us to run. The one money figure
                  that is measured end to end rather than assumed.

WHY NOT ROI

`Build_Plan.md` section Economics settled this before any code existed: an ROI
here rests on a leakage loss fraction for which no ground truth exists anywhere
in the world — that absence is the premise of the whole project. Monetising an
uncalibrated label does not add information, it just puts a currency symbol on an
order-of-magnitude uncertainty.

Value of Information sidesteps that. It prices a piece of information by how much
it changes a decision, which needs the decision structure and the reliability of
the screen, not the true leak rate. And its headline output here is
dimensionless, so it carries no invented price at all.
"""
