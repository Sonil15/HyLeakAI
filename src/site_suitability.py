"""Rank the 1,000 realisations by storage suitability. A continuous score, not clusters.

Why not clustering: `poro_mean` and `logk_mean` correlate at r=1.00 in this
dataset (same underlying quantity via a fixed porosity-permeability
transform), and `poro_std`/`logk_std` correlate at r=0.97. PCA on the five
geology/caprock features puts 99.9% of the variance in 3 components with no
gap between them, and a KMeans sweep over k=2..6 never exceeded silhouette
0.263 (weak — the conventional floor for "real structure" is ~0.25). This is
a continuum, not discrete geological types, so a weighted multi-criteria
score is both the honest framing and the standard one: storage-site atlases
for CO2/H2 screen prospects this way (porosity, permeability, seal integrity),
not by clustering candidates into named types.

Inputs, each derived once per realisation in the site-suitability Kaggle
kernel (src/leakage/features.geology_features, src/leakage/labels.caprock_margin):

  poro_mean             storage capacity / injectivity. Stands in for
                         logk_mean too (r=1.00 with it here), so only one is
                         used -- summing both would double-count one signal.
  caprock_margin_peak   (P_max - P_init) / (P_frac - P_init), worst case over
                         all 60 timesteps. Higher = closer to the ASSUMED
                         fracture pressure = worse.
  poro_std              within-realisation heterogeneity. Higher = less
                         predictable injection performance = worse. Minor
                         criterion, not a primary one.

The three weights below are [ASSUMED], not fit to anything -- there is no
ground truth "suitability" label to fit against, same reason the leakage
labels in src/leakage/labels.py are derived rather than trained on. Report the
score as a ranking under a stated weighting, sweep the weights before
claiming a rank order is robust, and say so out loud.

Usage:
    python -m src.site_suitability
    python -m src.site_suitability --w-capacity 0.5 --w-seal 0.3 --w-het 0.2
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FEATURES = REPO_ROOT / "outputs" / "site_suitability_features.csv"
DEFAULT_OUT_DIR = REPO_ROOT / "outputs"


@dataclass(frozen=True)
class SuitabilityWeights:
    capacity: float = 0.5   # [ASSUMED] storage capacity / injectivity, from poro_mean
    seal: float = 0.3       # [ASSUMED] penalty for caprock_margin_peak (higher = worse)
    heterogeneity: float = 0.2  # [ASSUMED] penalty for poro_std (higher = worse)

    def __post_init__(self) -> None:
        total = self.capacity + self.seal + self.heterogeneity
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"weights must sum to 1.0, got {total}")


def _read_features(path: Path) -> list[dict[str, float]]:
    with path.open() as fh:
        return [
            {k: float(v) for k, v in row.items()}
            for row in csv.DictReader(fh)
        ]


def _minmax(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    span = hi - lo
    if span == 0:
        return [0.5] * len(values)
    return [(v - lo) / span for v in values]


def rank_sites(
    rows: list[dict[str, float]], weights: SuitabilityWeights = SuitabilityWeights()
) -> list[dict[str, float]]:
    """Attach normalised criteria and a 0-100 suitability score to each row."""
    capacity = _minmax([r["poro_mean"] for r in rows])
    seal_risk = _minmax([r["caprock_margin_peak"] for r in rows])
    heterogeneity = _minmax([r["poro_std"] for r in rows])

    raw = [
        weights.capacity * cap - weights.seal * risk - weights.heterogeneity * het
        for cap, risk, het in zip(capacity, seal_risk, heterogeneity)
    ]
    score = _minmax(raw)  # rescale to [0, 1] so it reads as a 0-100 score

    out = []
    for row, cap, risk, het, s in zip(rows, capacity, seal_risk, heterogeneity, score):
        out.append({
            "sim_id": int(row["sim_id"]),
            "capacity_norm": cap,
            "seal_risk_norm": risk,
            "heterogeneity_norm": het,
            "suitability_score": round(100 * s, 2),
            "poro_mean": row["poro_mean"],
            "logk_mean": row["logk_mean"],
            "caprock_margin_peak": row["caprock_margin_peak"],
        })
    out.sort(key=lambda r: r["suitability_score"], reverse=True)
    for rank, row in enumerate(out, start=1):
        row["rank"] = rank
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--features", type=Path, default=DEFAULT_FEATURES)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--w-capacity", type=float, default=0.5)
    ap.add_argument("--w-seal", type=float, default=0.3)
    ap.add_argument("--w-het", type=float, default=0.2)
    args = ap.parse_args()

    weights = SuitabilityWeights(args.w_capacity, args.w_seal, args.w_het)
    rows = _read_features(args.features)
    print(f"{len(rows)} realisations loaded from {args.features}")
    print(f"weights: capacity={weights.capacity} seal={weights.seal} "
          f"heterogeneity={weights.heterogeneity}  (ASSUMED, sweep before trusting rank order)\n")

    ranked = rank_sites(rows, weights)

    scores = [r["suitability_score"] for r in ranked]
    print(f"score distribution: min {min(scores):.1f}  p25 {scores[int(0.75*len(scores))]:.1f}  "
          f"median {scores[len(scores)//2]:.1f}  p75 {scores[int(0.25*len(scores))]:.1f}  "
          f"max {max(scores):.1f}\n")

    print(f"{'rank':>5} {'sim_id':>7} {'score':>7} {'poro_mean':>10} "
          f"{'logk_mean':>10} {'caprock_margin':>15}")
    print("-- top 10 (most suitable) --")
    for r in ranked[:10]:
        print(f"{r['rank']:>5} {r['sim_id']:>7} {r['suitability_score']:>7.2f} "
              f"{r['poro_mean']:>10.4f} {r['logk_mean']:>10.4f} {r['caprock_margin_peak']:>15.4f}")
    print("-- bottom 10 (least suitable) --")
    for r in ranked[-10:]:
        print(f"{r['rank']:>5} {r['sim_id']:>7} {r['suitability_score']:>7.2f} "
              f"{r['poro_mean']:>10.4f} {r['logk_mean']:>10.4f} {r['caprock_margin_peak']:>15.4f}")

    out_csv = args.out_dir / "site_suitability_ranking.csv"
    with out_csv.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(ranked[0].keys()))
        writer.writeheader()
        writer.writerows(ranked)
    print(f"\nwrote {out_csv} ({len(ranked)} rows)")

    summary = {
        "n_sites": len(ranked),
        "weights": {"capacity": weights.capacity, "seal": weights.seal,
                    "heterogeneity": weights.heterogeneity},
        "score_distribution": {
            "min": min(scores), "median": scores[len(scores) // 2], "max": max(scores),
        },
        "top_10_sim_ids": [r["sim_id"] for r in ranked[:10]],
        "bottom_10_sim_ids": [r["sim_id"] for r in ranked[-10:]],
    }
    out_json = args.out_dir / "site_suitability_summary.json"
    out_json.write_text(json.dumps(summary, indent=2))
    print(f"wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
