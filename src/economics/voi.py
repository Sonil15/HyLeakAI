"""Value of Information — what the screen is worth, without inventing a price.

WHY NOT ROI

Document 9 asked for ROI. An ROI here needs a leakage loss fraction, and no
ground truth for one exists anywhere in the world — that absence is the premise
of this project. Multiplying an uncalibrated label by a hydrogen price does not
produce knowledge, it produces an order-of-magnitude uncertainty wearing a
currency symbol.

Value of Information is the framework the petroleum industry already uses for
this exact question. It prices information by how much it changes a decision,
which needs the decision structure and the reliability of the test — not the true
leak rate. Its headline output here is a ratio, so it carries no price at all.

WHAT IS ACTUALLY BEING ESTIMATED

A site has ONE unknown fault. Nobody observes it — not the simulator, not us. The
pitch says this exactly: twenty thousand guesses about one crack. So both parties
are estimating the same quantity,

    theta = P(this site's fault is conductive enough to matter)

over the uncertainty in the fault's position, permeability, length and width.
Neither party ever resolves it. They differ in how well they estimate it:

    unaided     k ~ 2 hypotheses, simulated exactly.
                Unbiased, and hopeless variance — at k = 2 the only estimates
                available are 0, 1/2 and 1.

    screened    N = 20,000 hypotheses at measured classifier skill.
                Sampling noise is negligible at that N, so the error is not
                variance at all: it is the bias from imperfect calibration, and
                its size is set by how well Se and Sp themselves were measured
                (on 15,911 held-out rows).

That is a bias-variance trade, and it is the honest form of the comparison. The
unaided operator is not modelled as ignorant or as using a worse tool — they are
modelled as using a *better* tool on a sample far too small to cover the
uncertainty. And our advantage is capped by our own calibration, so more
hypotheses cannot rescue a poorly characterised classifier.

WHY NOT THE OBVIOUS FRAMING

Running VOI on the raw classifier score would return "we capture ~100% of perfect
information", because AUC is 0.9996 against our own T3 label and `train_xgb.py`
says plainly that T3 is a closed-form function of quantities in the feature
vector — at a fixed timestep it is algebra. That number would be a restatement of
the label, not a result. Coverage is what the product actually sells, so coverage
is what gets valued.

Usage:
    python -m src.economics.voi
    python -m src.economics.voi --self-test
"""

from __future__ import annotations

import argparse
import json

import numpy as np

from src import config as C
from src.economics import assumptions as A

# Costs are relative to the containment-failure loss, which is therefore 1. Every
# economic input then enters as the ratio r = mitigation_cost / loss, so the two
# unverifiable costs collapse into one unknown number, which we sweep.
LOSS = 1.0

# [ASSUMED] Concentration of the Beta prior over theta. 4 is deliberately
# diffuse: we are claiming ignorance about site risk, not a calibrated prior.
PRIOR_CONCENTRATION = 4.0

# [DATASET] Held-out rows behind the Se/Sp estimates — outputs/source_comparison.json.
# The positive count is what limits sensitivity, and it is small.
N_TEST_ROWS = 15911
POSITIVE_RATE = 0.019357677549123764
N_TEST_POSITIVE = int(round(N_TEST_ROWS * POSITIVE_RATE))
N_TEST_NEGATIVE = N_TEST_ROWS - N_TEST_POSITIVE

# No quadrature anywhere in this module. A diffuse Beta prior with mean below 0.5
# has shape a < 1, so its density diverges as theta -> 0; integrating that on a
# grid produced small NEGATIVE values of information, which is impossible and was
# pure numerical error. Every quantity here has a closed form under a Beta prior,
# so the grid was removed rather than refined.


# ---------------------------------------------------------------------------
# Turning a measured AUC into an operating point
# ---------------------------------------------------------------------------

def binormal_dprime(auc: float) -> float:
    """Discriminability d' implied by an AUC, under the equal-variance binormal model.

    We measured AUC and PR-AUC but never dumped held-out scores, so no
    sensitivity/specificity pair is recorded at any threshold. The binormal model
    is the standard way to recover a full ROC from a single AUC, and it is stated
    as an assumption rather than hidden: AUC = Phi(d' / sqrt(2)).

    `src/train_xgb.py --dump-predictions` writes the real scores if an exact
    empirical ROC is wanted later.
    """
    from scipy.stats import norm

    assert 0.5 < auc < 1.0, f"AUC {auc} outside (0.5, 1.0)"
    return float(np.sqrt(2.0) * norm.ppf(auc))


def roc_point(dprime: float, specificity: float) -> float:
    """Sensitivity attainable at a given specificity, on the binormal ROC."""
    from scipy.stats import norm

    return float(norm.cdf(norm.ppf(1.0 - specificity) + dprime))


# ---------------------------------------------------------------------------
# The two estimators of theta
# ---------------------------------------------------------------------------

def expected_cost_threshold_rule(a: float, b: float, cost_ratio: float,
                                 theta_star: float) -> float:
    """E[cost] under Beta(a,b) when the policy is "mitigate iff theta > theta_star".

    Closed form. Proceeding costs theta, mitigating costs the ratio, so

        E[cost] = E[theta . 1{theta <= t}] + r . P(theta > t)
                = mean . I_t(a+1, b)  +  r . (1 - I_t(a, b))

    with I the regularised incomplete beta. Every arm in this module reduces to
    this function with a different threshold, which is what makes the comparison
    exact rather than approximate:

        perfect information   theta_star = r      (mitigate exactly when it pays)
        screened              theta_star solved from the Rogan-Gladen inversion
        no information        handled separately — there is no threshold at all
    """
    from scipy.stats import beta as beta_dist

    t = float(np.clip(theta_star, 0.0, 1.0))
    mean = a / (a + b)
    return float(mean * beta_dist.cdf(t, a + 1, b)
                 + cost_ratio * (1.0 - beta_dist.cdf(t, a, b)))


def expected_cost_prior_only(a: float, b: float, cost_ratio: float) -> float:
    """No test at all: commit on the prior mean, one decision for every site."""
    return float(min(a / (a + b), cost_ratio))


def expected_cost_perfect(a: float, b: float, cost_ratio: float) -> float:
    """Knowing theta exactly before deciding. The ceiling on any screen."""
    return expected_cost_threshold_rule(a, b, cost_ratio, cost_ratio)


def expected_cost_unaided(a: float, b: float, cost_ratio: float, k: int) -> float:
    """k exact simulator runs, folded into the prior. Exact, via Beta-Binomial.

    The operator is not modelled as naive — they update properly. What limits
    them is that k is 2: the posterior mean can take only k+1 distinct values, so
    the decision can only move if one of those few crosses the cost ratio.
    """
    from scipy.stats import betabinom

    successes = np.arange(k + 1)
    probs = betabinom.pmf(successes, k, a, b)
    posterior_means = (a + successes) / (a + b + k)
    return float(np.sum(probs * np.minimum(posterior_means, cost_ratio)))


def screened_threshold(cost_ratio: float, se_true: float, sp_true: float,
                       se_hat: float, sp_hat: float) -> float:
    """The true theta at which the screen's estimate crosses the decision line.

    At N = 20,000 hypotheses the sampling noise on the flagged fraction is
    negligible, so the screen observes its flag rate essentially exactly:

        observed(theta) = theta . Se_true + (1 - theta) . (1 - Sp_true)

    The analyst inverts it with the Se/Sp measured on held-out data
    (Rogan-Gladen prevalence correction). If those estimates were exact the
    inversion would return theta and the screen would be perfect information. So
    the screen's entire error is the gap between true and estimated Se/Sp — NOT
    sampling noise. More fault hypotheses cannot shrink it; only a
    better-characterised classifier can.

    Solving estimate(theta) = r for theta gives the effective policy threshold.
    """
    slope = se_true - (1.0 - sp_true)
    if slope <= 1e-12:
        return 1.0  # a test with no discrimination never triggers mitigation
    denom_hat = se_hat - (1.0 - sp_hat)
    return float((cost_ratio * denom_hat - (1.0 - sp_hat) + (1.0 - sp_true)) / slope)


def expected_cost_screened(a: float, b: float, cost_ratio: float,
                           se_hat: float, sp_hat: float,
                           n_draws: int, seed: int) -> float:
    """Average the exact threshold-rule cost over our uncertainty in Se and Sp.

    The true Se and Sp are drawn from Beta posteriors set by the held-out counts
    they were measured on. Sensitivity is the binding constraint: it rests on
    ~308 positive rows, not on all 15,911.
    """
    rng = np.random.default_rng(seed)
    se_draws = rng.beta(se_hat * N_TEST_POSITIVE + 1,
                        (1 - se_hat) * N_TEST_POSITIVE + 1, n_draws)
    sp_draws = rng.beta(sp_hat * N_TEST_NEGATIVE + 1,
                        (1 - sp_hat) * N_TEST_NEGATIVE + 1, n_draws)

    costs = [expected_cost_threshold_rule(
                 a, b, cost_ratio,
                 screened_threshold(cost_ratio, se, sp, se_hat, sp_hat))
             for se, sp in zip(se_draws, sp_draws)]
    return float(np.mean(costs))


# ---------------------------------------------------------------------------
# The comparison
# ---------------------------------------------------------------------------

def beta_prior(prior_mean: float, concentration: float = PRIOR_CONCENTRATION):
    return prior_mean * concentration, (1.0 - prior_mean) * concentration


def compare(prior_mean: float, cost_ratio: float, auc: float, k: int,
            n_draws: int = 400, seed: int = 20260814) -> dict:
    """Screened versus unaided at one point in the assumption space."""
    a, b = beta_prior(prior_mean)
    dprime = binormal_dprime(auc)

    ev_prior = expected_cost_prior_only(a, b, cost_ratio)
    ev_perfect = expected_cost_perfect(a, b, cost_ratio)
    vopi = ev_prior - ev_perfect

    ev_unaided = expected_cost_unaided(a, b, cost_ratio, k)

    # Operating point: walk the ROC, keep whichever specificity buys most value.
    best = None
    for sp_hat in (0.90, 0.95, 0.99, 0.995, 0.999):
        se_hat = roc_point(dprime, sp_hat)
        ev = expected_cost_screened(a, b, cost_ratio, se_hat, sp_hat, n_draws, seed)
        if best is None or ev < best["expected_cost"]:
            best = {"specificity": sp_hat, "sensitivity": se_hat,
                    "expected_cost": ev}

    voi_unaided = ev_prior - ev_unaided
    voi_screened = ev_prior - best["expected_cost"]

    def eff(v: float) -> float:
        return float(v / vopi) if vopi > 1e-12 else 0.0

    return {
        "vopi": float(vopi),
        "unaided": {"k": k, "voi": float(voi_unaided), "efficiency": eff(voi_unaided)},
        "screened": {
            "n_hypotheses": int(A.get("hypotheses_per_field_prediction").value),
            "voi": float(voi_screened),
            "efficiency": eff(voi_screened),
            "operating_point": {"sensitivity": best["sensitivity"],
                                "specificity": best["specificity"]},
        },
        "efficiency_gain": eff(voi_screened) - eff(voi_unaided),
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def self_test() -> None:
    rng = np.random.default_rng(20260814)

    # Both arms are bounded above by perfect information. Only the unaided arm is
    # bounded below by zero, and the asymmetry is the point:
    #
    #   unaided   an unbiased Bayesian update. Jensen guarantees VOI >= 0 — more
    #             data cannot hurt a decision-maker who updates correctly.
    #   screened  a BIAS-CORRECTED estimate, corrected with an Se/Sp we measured
    #             on finite data. When that correction is off, acting on the
    #             result can be worse than not screening. VOI may be negative.
    #
    # So the screened arm gets the weaker assertion, deliberately. The regime
    # where it goes negative is a real property of the method and is located and
    # reported rather than asserted away.
    for _ in range(40):
        p = float(rng.uniform(0.02, 0.5))
        r = float(rng.uniform(0.005, 0.5))
        auc = float(rng.uniform(0.7, 0.9999))
        k = int(rng.integers(1, 6))
        res = compare(p, r, auc, k, n_draws=60)
        for arm in ("unaided", "screened"):
            assert res[arm]["voi"] <= res["vopi"] + 1e-9, (
                f"{arm} VOI exceeded perfect information: {res}")
            assert res[arm]["efficiency"] <= 1.0 + 1e-9, (
                f"{arm} efficiency above 1: {res}")
        assert res["unaided"]["voi"] >= -1e-9, (
            f"unaided VOI negative — an unbiased Bayesian update cannot lose "
            f"value, so this is an error in the update itself: {res}")

    # More simulator runs cannot make the unaided operator worse off.
    effs = [compare(0.1, 0.05, 0.999, k, n_draws=60)["unaided"]["efficiency"]
            for k in (1, 2, 4, 8, 16)]
    assert all(b >= a - 1e-6 for a, b in zip(effs, effs[1:])), (
        f"unaided efficiency fell as k rose: {effs}")

    # A better classifier cannot make the screen worse off.
    effs = [compare(0.1, 0.05, auc, 2, n_draws=60)["screened"]["efficiency"]
            for auc in (0.80, 0.90, 0.99, 0.999)]
    assert all(b >= a - 1e-3 for a, b in zip(effs, effs[1:])), (
        f"screened efficiency fell as AUC rose: {effs}")

    # The negative regime must actually exist and must be where theory says: at a
    # mitigation cost so low that the right move is to mitigate almost always, so
    # a miscalibrated screen can only talk you out of it. If this stops failing,
    # the calibration error has been dropped from the model by accident.
    harmful = compare(0.10, 1e-4, 0.999628776017932, 2)["screened"]["efficiency"]
    assert harmful < 0, (
        "the screen no longer shows a value-destroying regime at a very low "
        "mitigation/loss ratio. That regime is real — it is what miscalibration "
        f"does — so its disappearance means Se/Sp uncertainty stopped being "
        f"propagated. Got efficiency {harmful:+.4f}.")

    # The binormal inversion must round-trip.
    from scipy.stats import norm
    for auc in (0.60, 0.80, 0.95, 0.99, 0.9996):
        assert abs(norm.cdf(binormal_dprime(auc) / np.sqrt(2.0)) - auc) < 1e-9

    print("OK self-test passed: both arms bounded by VOPI; unaided VOI provably "
          "non-negative;\n   screened arm still shows its value-destroying regime "
          "under miscalibration; monotone in\n   simulator budget and classifier "
          "quality; binormal inversion round-trips.")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_report() -> dict:
    prior = A.get("prior_bad_fault")
    ratio = A.get("mitigation_to_loss_ratio")
    k_q = A.get("hypotheses_simulated_unaided")
    k = int(k_q.value)

    auc_sim = 0.9998657850513263   # outputs/source_comparison.json, simulator fields
    auc_sur = 0.999628776017932    # outputs/source_comparison.json, U-Net fields
    base_ratio = float(np.sqrt(ratio.low * ratio.high))

    headline = compare(prior.value, base_ratio, auc_sur, k)
    with_sim = compare(prior.value, base_ratio, auc_sim, k)

    ratio_grid = np.logspace(np.log10(ratio.low), np.log10(ratio.high), 21)
    prior_grid = np.linspace(prior.low, prior.high, 21)
    k_grid = [1, 2, 3, 5, 10, 20]

    sweep_ratio = [{"cost_ratio": float(r), **_row(compare(prior.value, float(r), auc_sur, k))}
                   for r in ratio_grid]
    sweep_prior = [{"prior": float(p), **_row(compare(float(p), base_ratio, auc_sur, k))}
                   for p in prior_grid]
    sweep_k = [{"k_simulated": kk, **_row(compare(prior.value, base_ratio, auc_sur, kk))}
               for kk in k_grid]

    # How many exact simulator runs would match the screen's decision efficiency?
    target = headline["screened"]["efficiency"]
    breakeven = next((row["k_simulated"] for row in sweep_k
                      if row["unaided_efficiency"] >= target), None)

    # Where does the screen stop being worth running? Below some mitigation/loss
    # ratio the right action is to mitigate almost regardless, and a screen with
    # imperfect calibration can only talk you out of it. Locate that boundary and
    # report it — it is the honest operating limit of the product.
    harmful = [row for row in sweep_ratio if row["screened_efficiency"] < 0]
    harmful_below = max(r["cost_ratio"] for r in harmful) if harmful else None

    return {
        "framing": (
            "Value of coverage, not value of accuracy. A site has one unknown "
            "fault; nobody observes it. The unaided operator estimates its risk "
            "from k exact simulator runs, we estimate it from 20,000 screened "
            "hypotheses whose error is set by our own calibration. Efficiency is "
            "VOI / VOPI and is dimensionless."
        ),
        "inputs": {
            "prior_bad_fault": prior.value,
            "prior_swept": [prior.low, prior.high],
            "prior_concentration": PRIOR_CONCENTRATION,
            "cost_ratio_geometric_mid": base_ratio,
            "cost_ratio_swept": [ratio.low, ratio.high],
            "k_hypotheses_simulated": k,
            "k_swept": [k_q.low, k_q.high],
            "n_hypotheses_screened": int(A.get("hypotheses_per_field_prediction").value),
            "auc_surrogate": auc_sur,
            "auc_simulator": auc_sim,
            "test_rows_behind_sensitivity": N_TEST_POSITIVE,
            "test_rows_behind_specificity": N_TEST_NEGATIVE,
        },
        "headline": headline,
        "with_simulator_fields": with_sim,
        "surrogate_efficiency_penalty": float(
            with_sim["screened"]["efficiency"] - headline["screened"]["efficiency"]),
        "simulator_runs_to_match_screen": breakeven,
        "value_destroying_below_cost_ratio": harmful_below,
        "sweep_cost_ratio": sweep_ratio,
        "sweep_prior": sweep_prior,
        "sweep_k_simulated": sweep_k,
        "caveats": [
            "Efficiency says how much of the available decision value the screen "
            "captures. It does not say the underlying T3 label is correct — that "
            "label is ours, semi-analytical, and uncalibrated against any real "
            "leakage measurement, because none exists.",
            "Sensitivity and specificity come from a binormal ROC fitted to the "
            "measured AUC; held-out scores were never dumped. Run "
            "src.train_xgb --dump-predictions for the empirical ROC.",
            "The screen's ceiling is set by how well Se and Sp are known, and "
            "sensitivity rests on only ~308 positive held-out rows. More fault "
            "hypotheses do not raise that ceiling.",
            "Mitigation is modelled as removing the loss entirely. Partial "
            "mitigation lowers both arms.",
            "The prior over site risk is deliberately diffuse (Beta concentration "
            f"{PRIOR_CONCENTRATION:.0f}); we are claiming ignorance, not calibration.",
            "There is a regime where the screen is worth LESS than nothing: when "
            "mitigation is cheap enough that the right move is to mitigate almost "
            "regardless, an imperfectly calibrated screen can only talk an "
            "operator out of it. See value_destroying_below_cost_ratio. This is a "
            "property of bias-corrected screening, not of this implementation.",
        ],
    }


def _row(c: dict) -> dict:
    return {
        "screened_efficiency": c["screened"]["efficiency"],
        "unaided_efficiency": c["unaided"]["efficiency"],
        "efficiency_gain": c["efficiency_gain"],
        "k_simulated": c["unaided"]["k"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return 0

    self_test()
    report = build_report()
    i, h = report["inputs"], report["headline"]

    print(f"\nPrior site risk {i['prior_bad_fault']:.0%} (Beta, concentration "
          f"{i['prior_concentration']:.0f})   mitigation/loss "
          f"{i['cost_ratio_geometric_mid']:.2%}")

    print(f"\n{'arm':<26} {'hypotheses':>11} {'VOI':>9} {'VOI/VOPI':>10}")
    print("-" * 60)
    print(f"{'unaided (simulator)':<26} {h['unaided']['k']:>11,} "
          f"{h['unaided']['voi']:>9.5f} {h['unaided']['efficiency']:>10.3f}")
    print(f"{'screened (HyLeakAI)':<26} {h['screened']['n_hypotheses']:>11,} "
          f"{h['screened']['voi']:>9.5f} {h['screened']['efficiency']:>10.3f}")
    print(f"{'perfect information':<26} {'-':>11} {h['vopi']:>9.5f} {1.0:>10.3f}")

    op = h["screened"]["operating_point"]
    print(f"\nOperating point: specificity {op['specificity']:.3f}, "
          f"sensitivity {op['sensitivity']:.4f}")

    match = report["simulator_runs_to_match_screen"]
    print(f"\nSimulator runs needed to match the screen's decision efficiency: "
          f"{match if match else '>20'}")
    print(f"Cost of using U-Net fields instead of the simulator's: "
          f"{report['surrogate_efficiency_penalty']:+.4f} efficiency")

    harmful_below = report["value_destroying_below_cost_ratio"]
    if harmful_below:
        print(f"\nWHERE IT STOPS BEING WORTH RUNNING")
        print(f"  Below a mitigation/loss ratio of {harmful_below:.1e}, screening "
              f"is worth LESS than nothing:")
        print(f"  mitigation is then cheap enough that the right move is to "
              f"mitigate almost regardless,")
        print(f"  and an imperfectly calibrated screen can only talk you out of it.")

    print("\nSWEEP over mitigation/loss ratio")
    print(f"{'ratio':>10} {'screened':>10} {'unaided':>10} {'gain':>8}")
    print("-" * 42)
    for row in report["sweep_cost_ratio"][::4]:
        print(f"{row['cost_ratio']:>10.2e} {row['screened_efficiency']:>10.3f} "
              f"{row['unaided_efficiency']:>10.3f} {row['efficiency_gain']:>+8.3f}")

    C.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = C.OUTPUT_DIR / "voi_results.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
