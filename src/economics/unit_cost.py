"""What a screening pass costs to run — the one money figure measured end to end.

WHY THIS IS THE ONLY PRICE IN THE PROJECT

Everything else in the economics is a ratio, because the quantities that would
turn it into currency — a hydrogen price, a workover cost, the value of a
containment failure — have no source we have opened. Compute cost is different.
We can time our own service, and cloud pricing is published. So this module
produces the cost side of a business model without assuming anything about the
value side.

WHAT WAS MEASURED (2026-08-14, against the deployed demo API)

Cold start:              63.3 s   — Render free tier, spun down after 15 min idle
Warm assessment, by fault count, seconds of wall clock including network:

     1 hypothesis    8.30, 5.17
    10 hypotheses    6.41, 6.77
    25 hypotheses    5.60, 6.37
    50 hypotheses    7.10, 6.52, 6.88

There is no detectable trend across a 50x range in the number of fault
hypotheses. The marginal cost of a hypothesis is below the noise floor of the
measurement; the whole cost is the field prediction.

That is the decoupling claim showing up directly in wall clock. The fault is not
an input to the U-Net, so hypotheses are overlaid on a field that has already
been predicted, and adding more of them does not re-run the network.

WHAT WAS NOT MEASURED, AND IS THEREFORE NOT CLAIMED

  * The 50-hypothesis ceiling is the API's own cap. Extrapolating a flat cost out
    to 20,000 hypotheses rests on the architecture — per-hypothesis work is
    feature extraction plus one gradient-boosted scoring call — not on this
    measurement. Stated as an architectural consequence, with the 1-to-50
    measurement as the evidence that the architecture behaves as designed.
  * Cost relative to a reservoir simulator. We have never timed tNavigator
    ourselves, so no speedup ratio and no cost comparison against it appears
    here. docs/PRESENTATION_CONTEXT.md forbids that claim and this module
    respects it.

Usage:
    python -m src.economics.unit_cost
"""

from __future__ import annotations

import json

import numpy as np

from src import config as C

# --- [MEASURED] wall clock against https://hyleak-api-demo.onrender.com --------

COLD_START_S = 63.3

TIMINGS_S: dict[int, list[float]] = {
    1: [8.297, 5.168],
    10: [6.411, 6.771],
    25: [5.599, 6.368],
    50: [7.101, 6.521, 6.878],
}

# [DATASET] Render free web service allocation. Documented in
# docs/PRODUCT_API_PLAN.md as suitable for a preview, not production.
INSTANCE_VCPU = 0.1
INSTANCE_RAM_GB = 0.5

# [ASSUMED] Published on-demand rates for a general-purpose vCPU-hour across the
# major clouds sit in this band. Swept rather than picked, and it is the only
# input here that is not ours.
VCPU_HOUR_USD_LOW = 0.02
VCPU_HOUR_USD_HIGH = 0.05

# [DERIVED] docs/PRESENTATION_CONTEXT.md — 1,000 realisations x 20 fault draws.
HYPOTHESES_PER_CAMPAIGN = 20_000


def marginal_cost_bound() -> dict:
    """Fit cost against hypothesis count and report the slope with its uncertainty.

    The point of this fit is not the slope, which is indistinguishable from zero.
    It is the confidence interval: it says how large a per-hypothesis cost the
    measurement could still have missed.
    """
    counts = np.array([n for n, ts in TIMINGS_S.items() for _ in ts], dtype=float)
    times = np.array([t for ts in TIMINGS_S.values() for t in ts], dtype=float)
    n = times.size

    slope, intercept = np.polyfit(counts, times, 1)
    fitted = slope * counts + intercept
    resid = times - fitted
    dof = n - 2
    s_err = float(np.sqrt(np.sum(resid**2) / dof))
    ss_x = float(np.sum((counts - counts.mean()) ** 2))
    slope_se = s_err / np.sqrt(ss_x)

    # 95% two-sided t interval. At dof = 7 the critical value is 2.365.
    t_crit = 2.365
    return {
        "slope_s_per_hypothesis": float(slope),
        "slope_se": float(slope_se),
        "slope_ci95": [float(slope - t_crit * slope_se),
                       float(slope + t_crit * slope_se)],
        "intercept_s": float(intercept),
        "residual_sd_s": s_err,
        "n_measurements": int(n),
        "slope_distinguishable_from_zero": bool(
            abs(slope) > t_crit * slope_se),
    }


def cost_per_pass() -> dict:
    all_times = [t for ts in TIMINGS_S.values() for t in ts]
    median_s = float(np.median(all_times))

    # Wall clock on an instance allocated a fraction of a vCPU. Reading it as
    # vCPU-seconds assumes the request was compute-bound and got its full share,
    # which for a U-Net forward pass on CPU is the right way round: if anything
    # this OVERSTATES the compute, because it also contains network time.
    vcpu_seconds = median_s * INSTANCE_VCPU
    vcpu_hours = vcpu_seconds / 3600.0

    return {
        "median_wall_clock_s": median_s,
        "wall_clock_iqr_s": [float(np.percentile(all_times, 25)),
                             float(np.percentile(all_times, 75))],
        "instance_vcpu": INSTANCE_VCPU,
        "vcpu_seconds_per_pass": float(vcpu_seconds),
        "usd_per_pass_low": float(vcpu_hours * VCPU_HOUR_USD_LOW),
        "usd_per_pass_high": float(vcpu_hours * VCPU_HOUR_USD_HIGH),
        "hypotheses_per_campaign": HYPOTHESES_PER_CAMPAIGN,
        "cold_start_s": COLD_START_S,
    }


def build_report() -> dict:
    marginal = marginal_cost_bound()
    cost = cost_per_pass()

    # If the true marginal cost sat at the top of its confidence interval, what
    # would a full campaign cost? This is the pessimistic bound, and reporting it
    # is the difference between "flat" and "flat as far as we looked".
    worst_marginal_s = max(0.0, marginal["slope_ci95"][1])
    worst_campaign_s = cost["median_wall_clock_s"] + worst_marginal_s * (
        HYPOTHESES_PER_CAMPAIGN - 1)

    return {
        "measured": {
            "timings_s": {str(k): v for k, v in TIMINGS_S.items()},
            "cold_start_s": COLD_START_S,
            "endpoint": "https://hyleak-api-demo.onrender.com/v1/assessments",
            "date": "2026-08-14",
        },
        "marginal_cost": marginal,
        "cost_per_pass": cost,
        "pessimistic_campaign": {
            "marginal_s_per_hypothesis_upper95": worst_marginal_s,
            "campaign_wall_clock_s_upper_bound": float(worst_campaign_s),
            "note": (
                "The measurement covers 1 to 50 hypotheses, which is the API's "
                "own cap. This row extrapolates the TOP of the slope confidence "
                "interval to a full 20,000-hypothesis campaign, so it is the "
                "cost if the flatness we measured is an artefact of the range. "
                "The architectural expectation is far below it."
            ),
        },
        "not_claimed": [
            "Any cost or speedup relative to a reservoir simulator. We have never "
            "timed tNavigator, so there is no ratio to quote.",
            "That 20,000 hypotheses were timed. 50 were, and the architecture "
            "carries the rest.",
            "A production cost. This is a 0.1-vCPU free tier with a 63 s cold "
            "start, which is a preview, not a deployment.",
        ],
    }


def main() -> int:
    report = build_report()
    m, c = report["marginal_cost"], report["cost_per_pass"]

    print("MEASURED — deployed API, warm, wall clock including network")
    for n, ts in TIMINGS_S.items():
        print(f"  {n:>3} hypotheses   " + "  ".join(f"{t:5.2f}s" for t in ts))
    print(f"  cold start      {COLD_START_S:5.1f}s")

    print(f"\nDoes cost grow with the number of hypotheses?")
    print(f"  slope        {m['slope_s_per_hypothesis']:+.5f} s per hypothesis")
    print(f"  95% CI       [{m['slope_ci95'][0]:+.5f}, {m['slope_ci95'][1]:+.5f}]")
    print(f"  distinguishable from zero: "
          f"{'YES' if m['slope_distinguishable_from_zero'] else 'NO'}")
    print(f"  -> across a 50x range the marginal cost of a fault hypothesis is")
    print(f"     below the noise floor. The cost is the field prediction.")

    print(f"\nCOST OF ONE SCREENING PASS")
    print(f"  median wall clock      {c['median_wall_clock_s']:.2f} s "
          f"on {c['instance_vcpu']} vCPU")
    print(f"  compute                {c['vcpu_seconds_per_pass']:.3f} vCPU-seconds")
    print(f"  at $0.02-0.05/vCPU-hr  "
          f"${c['usd_per_pass_low']:.6f} - ${c['usd_per_pass_high']:.6f}")

    p = report["pessimistic_campaign"]
    print(f"\nPESSIMISTIC BOUND — if the flatness is an artefact of the 1-50 range")
    print(f"  marginal at top of CI  {p['marginal_s_per_hypothesis_upper95']:.5f} s")
    print(f"  20,000-hypothesis pass {p['campaign_wall_clock_s_upper_bound']:,.0f} s "
          f"upper bound")

    print("\nNOT CLAIMED")
    for line in report["not_claimed"]:
        print(f"  - {line}")

    C.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = C.OUTPUT_DIR / "unit_cost.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
