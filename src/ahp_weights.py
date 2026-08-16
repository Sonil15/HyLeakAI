"""Derive the suitability weights by AHP, and measure how much the ranking depends on them.

Why this exists
---------------
The three criterion weights were previously picked by hand. That is not
disqualifying — the underground-hydrogen-storage screening literature
deliberately leaves weights project-specific rather than fixing them (the
UHSSI and the depleted-reservoir screening frameworks both define criteria and
0-5 thresholds, then say weights follow the project). But "we picked them"
gives a reader nothing to check.

AHP fixes the *provenance*, not the truth. It takes stated pairwise judgments,
derives weights as the principal eigenvector of the comparison matrix, and
reports a consistency ratio that catches self-contradiction. It does not make
the weights objectively correct: with one team rather than an expert panel,
the honest claim is "derived from these stated judgments, and internally
consistent" — never "these are the right weights".

That is why this module also runs a stability sweep. The question a reader
actually has is not "are your weights right" but "would your conclusion change
if they were somewhat different". The sweep answers it with a number.

    python -m src.ahp_weights
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from src.site_suitability import SuitabilityWeights

CRITERIA = ("capacity", "seal", "heterogeneity")

# Saaty's 1-9 scale: 1 equal, 3 moderately more important, 5 strongly, 7 very
# strongly, 9 extremely; 2/4/6/8 are the intermediate steps.
#
# The three judgments below are ours and are stated so they can be argued with:
#
#   capacity vs seal risk        2  Capacity is slightly more important. Both
#                                   matter, but a site with no usable pore
#                                   volume is not a candidate at all, whereas
#                                   pressure risk is partly manageable through
#                                   operating limits. This ordering also matches
#                                   published AHP work that ranks reservoir
#                                   quality above caprock (0.399 vs 0.274).
#
#   capacity vs heterogeneity    3  Moderately more important. Heterogeneity
#                                   degrades sweep efficiency and recovery, but
#                                   it modifies how well capacity is used rather
#                                   than whether capacity exists.
#
#   seal vs heterogeneity        2  Slightly more important. Containment is a
#                                   safety criterion; heterogeneity is an
#                                   efficiency one.
JUDGMENTS = {
    ("capacity", "seal"): 2.0,
    ("capacity", "heterogeneity"): 3.0,
    ("seal", "heterogeneity"): 2.0,
}

# Saaty's random index: the mean consistency index of randomly generated
# reciprocal matrices of size n. CR = CI / RI(n), and CR < 0.10 is the
# conventional acceptance threshold.
RANDOM_INDEX = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32}


def comparison_matrix() -> np.ndarray:
    """Build the reciprocal pairwise matrix from JUDGMENTS."""
    n = len(CRITERIA)
    index = {name: i for i, name in enumerate(CRITERIA)}
    matrix = np.ones((n, n))
    for (a, b), value in JUDGMENTS.items():
        i, j = index[a], index[b]
        matrix[i, j] = value
        matrix[j, i] = 1.0 / value  # reciprocity is what makes it an AHP matrix
    return matrix


def ahp_weights(matrix: np.ndarray) -> dict:
    """Principal eigenvector weights plus the consistency check.

    The eigenvector method is used rather than the geometric-mean shortcut
    because lambda_max falls out of it directly, and lambda_max is what the
    consistency index is built from.
    """
    values, vectors = np.linalg.eig(matrix)
    k = int(np.argmax(values.real))
    lambda_max = float(values[k].real)

    vector = np.abs(vectors[:, k].real)
    weights = vector / vector.sum()

    n = matrix.shape[0]
    consistency_index = (lambda_max - n) / (n - 1)
    random_index = RANDOM_INDEX[n]
    consistency_ratio = consistency_index / random_index if random_index else 0.0

    return {
        "weights": {name: float(w) for name, w in zip(CRITERIA, weights)},
        "lambda_max": lambda_max,
        "consistency_index": float(consistency_index),
        "consistency_ratio": float(consistency_ratio),
        "consistent": bool(consistency_ratio < 0.10),
    }


def _scores(rows: list[dict], w: tuple[float, float, float]) -> np.ndarray:
    """Recompute 0-100 suitability under an arbitrary weighting."""
    cap = np.array([r["capacity_norm"] for r in rows])
    seal = np.array([r["seal_risk_norm"] for r in rows])
    het = np.array([r["heterogeneity_norm"] for r in rows])
    raw = w[0] * cap - w[1] * seal - w[2] * het
    span = raw.max() - raw.min()
    return 100.0 * (raw - raw.min()) / (span if span else 1.0)


def stability_sweep(rows: list[dict], n_samples: int = 5000, seed: int = 20260816) -> dict:
    """How much of the ranking survives a plausible range of weights?

    Weights are drawn from a Dirichlet centred on the AHP result. This is the
    question a reader actually has — not "are these weights right" but "would
    your conclusion change if they were somewhat different" — and it is
    answerable without claiming any weighting is correct.

    Concentration 40 keeps samples in a believable neighbourhood (roughly
    +/- 0.07 on each weight) rather than sweeping the entire simplex, which
    would include weightings nobody would defend, such as capacity 0.9.
    """
    rng = np.random.default_rng(seed)
    base = ahp_weights(comparison_matrix())["weights"]
    centre = np.array([base[c] for c in CRITERIA])

    n_sites = len(rows)
    decile_cut = max(1, n_sites // 10)

    reference = _scores(rows, tuple(centre))
    reference_order = np.argsort(-reference)
    reference_top = set(reference_order[:decile_cut].tolist())

    top_decile_hits = np.zeros(n_sites, dtype=int)
    jaccard = []
    rank_shift = []

    samples = rng.dirichlet(centre * 40.0, size=n_samples)
    for weights in samples:
        scores = _scores(rows, tuple(weights))
        order = np.argsort(-scores)
        top = set(order[:decile_cut].tolist())
        top_decile_hits[list(top)] += 1
        jaccard.append(len(top & reference_top) / len(top | reference_top))

        rank = np.empty(n_sites, dtype=int)
        rank[order] = np.arange(n_sites)
        reference_rank = np.empty(n_sites, dtype=int)
        reference_rank[reference_order] = np.arange(n_sites)
        rank_shift.append(np.abs(rank - reference_rank).mean())

    frequency = top_decile_hits / n_samples
    always = int((frequency == 1.0).sum())
    robust = int((frequency >= 0.9).sum())

    return {
        "n_samples": n_samples,
        "dirichlet_concentration": 40.0,
        "decile_size": decile_cut,
        "top_decile_jaccard_mean": float(np.mean(jaccard)),
        "top_decile_jaccard_p05": float(np.quantile(jaccard, 0.05)),
        "mean_rank_shift": float(np.mean(rank_shift)),
        "sites_always_in_top_decile": always,
        "sites_in_top_decile_90pct": robust,
        "stable_site_ids": [int(rows[i]["sim_id"]) for i in np.argsort(-frequency)[:robust]],
        "top_decile_frequency": {int(rows[i]["sim_id"]): float(frequency[i])
                                 for i in np.argsort(-frequency)[:50]},
    }


def load_rows(path: Path) -> list[dict]:
    import csv
    with path.open(newline="", encoding="utf-8") as handle:
        return [{k: (float(v) if k != "sim_id" and k != "rank" else int(float(v)))
                 for k, v in row.items()} for row in csv.DictReader(handle)]


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    rows = load_rows(root / "outputs" / "site_suitability_ranking.csv")

    matrix = comparison_matrix()
    result = ahp_weights(matrix)

    print("Pairwise comparison matrix (Saaty 1-9):")
    header = "            " + "".join(f"{c:>16}" for c in CRITERIA)
    print(header)
    for name, row in zip(CRITERIA, matrix):
        print(f"{name:>12}" + "".join(f"{v:>16.4f}" for v in row))

    print("\nDerived weights (principal eigenvector):")
    for name, value in result["weights"].items():
        print(f"  {name:>14}  {value:.4f}")

    previous = SuitabilityWeights()
    print("\nAgainst the previously hand-picked weights:")
    for name, before in (("capacity", previous.capacity), ("seal", previous.seal),
                         ("heterogeneity", previous.heterogeneity)):
        after = result["weights"][name]
        print(f"  {name:>14}  {before:.2f} -> {after:.4f}   ({after - before:+.4f})")

    print(f"\nlambda_max        {result['lambda_max']:.6f}")
    print(f"consistency index {result['consistency_index']:.6f}")
    print(f"consistency ratio {result['consistency_ratio']:.6f}"
          f"   {'PASS (< 0.10)' if result['consistent'] else 'FAIL (>= 0.10)'}")

    print("\nStability sweep...")
    sweep = stability_sweep(rows)
    print(f"  samples                        {sweep['n_samples']}")
    print(f"  mean top-decile overlap        {sweep['top_decile_jaccard_mean']:.3f}")
    print(f"  5th-percentile overlap         {sweep['top_decile_jaccard_p05']:.3f}")
    print(f"  mean rank shift                {sweep['mean_rank_shift']:.1f} places")
    print(f"  always in top decile           {sweep['sites_always_in_top_decile']} sites")
    print(f"  in top decile >= 90% of draws  {sweep['sites_in_top_decile_90pct']} sites")

    out = root / "outputs" / "ahp_weights.json"
    out.write_text(json.dumps({
        "criteria": list(CRITERIA),
        "judgments": {f"{a} vs {b}": v for (a, b), v in JUDGMENTS.items()},
        "matrix": matrix.tolist(),
        "ahp": result,
        "previous_weights": {"capacity": previous.capacity, "seal": previous.seal,
                             "heterogeneity": previous.heterogeneity},
        "stability": sweep,
        "caveat": ("AHP formalises the stated judgments of this team; it is not an expert "
                   "elicitation and does not establish that these weights are correct. "
                   "The stability sweep is the load-bearing result: it reports how much of "
                   "the ranking survives a plausible range of weightings."),
    }, indent=2), encoding="utf-8")
    print(f"\nwrote {out.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
