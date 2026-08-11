"""Does surrogate error matter? Score the same risk model on both field sources.

This is the measurement the whole surrogate argument rests on. The U-Net has a
~16% relative error on pressure and ~11% on saturation. The question is not
whether those numbers are small — it is whether they change the leakage risk
estimate that the pipeline actually produces.

Design, and why it is set up this way:

  * The risk model is trained ONCE, on simulator-derived features. It is not
    retrained on surrogate features. That is the deployment situation: you fit
    on simulation output, then run against a surrogate in production.
  * Both tables carry labels from the SIMULATOR, so the target is identical and
    only the inputs differ.
  * Both use the same leak thresholds, so class balance is identical too.
  * Rows are aligned on (sim_id, fault_id, timestep_observed), so the per-feature
    diagnostic compares like with like rather than two different populations.

Anything left after that is attributable to surrogate error alone.

Usage:
    python -m src.compare_sources
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src import config as C
from src.leakage.features import feature_columns, label_columns, load_table
from src.train_xgb import classification_metrics, regression_metrics

KEY = ("sim_id", "fault_id", "timestep_observed")


def align(a, ca, b, cb):
    """Return (A, B) row-aligned on the identifier triple, and the shared order."""
    ka = np.stack([a[:, ca.index(k)] for k in KEY], axis=1)
    kb = np.stack([b[:, cb.index(k)] for k in KEY], axis=1)

    def encode(k):
        # sim < 1000, fault < 1000, timestep < 100 -> a collision-free integer key
        return (k[:, 0] * 10**6 + k[:, 1] * 10**3 + k[:, 2]).astype(np.int64)

    ea, eb = encode(ka), encode(kb)
    common = np.intersect1d(ea, eb)
    ia = np.argsort(ea)[np.searchsorted(ea, common, sorter=np.argsort(ea))]
    ib = np.argsort(eb)[np.searchsorted(eb, common, sorter=np.argsort(eb))]
    return a[ia], b[ib], len(common)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--truth-table", type=Path, default=C.DATA_DIR / "features.npy")
    ap.add_argument("--unet-table", type=Path, default=C.DATA_DIR / "features_unet.npy")
    ap.add_argument("--out-dir", type=Path, default=C.OUTPUT_DIR)
    ap.add_argument("--horizon", type=int, default=None)
    args = ap.parse_args()

    import xgboost as xgb

    results_path = args.out_dir / "xgb_results.json"
    saved = json.loads(results_path.read_text()) if results_path.exists() else {}
    horizon = args.horizon or saved.get("report_horizon", 3)
    feats = json.loads((args.out_dir / "shap_features.json").read_text())
    names = label_columns(horizon)

    clf = xgb.XGBClassifier(); clf.load_model(args.out_dir / "xgb_classifier.ubj")
    reg = xgb.XGBRegressor(); reg.load_model(args.out_dir / "xgb_regressor.ubj")

    truth, ct, _ = load_table(args.truth_table)
    unet, cu, mu = load_table(args.unet_table)
    print(f"truth table {truth.shape}   unet table {unet.shape}")
    print(f"unet source: {mu.get('source')}  checkpoint: {mu.get('checkpoint')}")

    # Restrict truth to the simulations present in the U-Net table (its test split).
    unet_sims = set(unet[:, cu.index("sim_id")].astype(int).tolist())
    truth = truth[np.isin(truth[:, ct.index("sim_id")].astype(int), list(unet_sims))]
    print(f"comparing {len(unet_sims)} simulations "
          f"(all held out from XGBoost training)")

    A, B, n = align(truth, ct, unet, cu)
    print(f"aligned {n:,} rows on {KEY}\n")

    # Drop rows whose label is undefined at this horizon.
    yi = ct.index(names["log_q"])
    keep = np.isfinite(A[:, yi]) & np.isfinite(B[:, cu.index(names["log_q"])])
    A, B = A[keep], B[keep]
    y_cls = A[:, ct.index(names["leak"])]
    y_reg = A[:, yi]

    # Labels must be identical: both tables take them from the simulator.
    lb = B[:, cu.index(names["log_q"])]
    if not np.allclose(y_reg, lb, atol=1e-4):
        print(f"WARNING: labels differ between tables (max {np.abs(y_reg-lb).max():.3e}). "
              f"The U-Net table should carry SIMULATOR labels; the comparison is "
              f"invalid otherwise.")
    else:
        print("OK labels identical across both tables (simulator-derived)\n")

    Xt = A[:, [ct.index(f) for f in feats]]
    Xu = B[:, [cu.index(f) for f in feats]]

    print("=" * 74)
    print(f"RISK MODEL TRAINED ON SIMULATOR FEATURES, horizon {horizon} "
          f"({horizon * C.MONTHS_PER_STEP} months)")
    print("=" * 74)
    rows = {}
    for label, X in (("simulator fields", Xt), ("U-Net fields", Xu)):
        cm = classification_metrics(y_cls, clf.predict_proba(X)[:, 1])
        rm = regression_metrics(y_reg, reg.predict(X))
        rows[label] = (cm, rm)
        print(f"  {label:20s} PR-AUC {cm['pr_auc']:.4f}  AUC {cm['auc']:.4f}   "
              f"log-flux R2 {rm['r2']:+.4f}  RMSE {rm['rmse']:.3f}")

    (cm_t, rm_t), (cm_u, rm_u) = rows["simulator fields"], rows["U-Net fields"]
    d_pr = cm_u["pr_auc"] - cm_t["pr_auc"]
    d_r2 = rm_u["r2"] - rm_t["r2"]
    print(f"\n  cost of using the surrogate: PR-AUC {d_pr:+.4f}   R2 {d_r2:+.4f}")
    retention = cm_u["pr_auc"] / cm_t["pr_auc"] if cm_t["pr_auc"] else float("nan")
    print(f"  the surrogate retains {100 * retention:.1f}% of the simulator's PR-AUC")

    # -- which features does surrogate error actually distort? --
    print("\n" + "=" * 74)
    print("PER-FEATURE DISTORTION (surrogate vs simulator, same rows)")
    print("=" * 74)
    diffs = []
    for f in feats:
        a, b = A[:, ct.index(f)], B[:, cu.index(f)]
        scale = np.abs(a).mean() or 1.0
        diffs.append((np.abs(a - b).mean() / scale, f, np.abs(a - b).mean()))
    diffs.sort(reverse=True)
    print(f"  {'feature':34s} {'mean |err| / scale':>18} {'mean |err|':>12}")
    for rel, f, absolute in diffs[:10]:
        print(f"  {f:34s} {rel:>18.4f} {absolute:>12.4g}")
    unaffected = sum(1 for rel, _, _ in diffs if rel < 1e-6)
    print(f"\n  {unaffected}/{len(feats)} features are identical "
          f"(geology and fault properties do not pass through the surrogate)")

    payload = {
        "horizon": horizon,
        "n_rows": int(len(A)),
        "n_simulations": len(unet_sims),
        "simulator": {"classification": cm_t, "regression": rm_t},
        "unet": {"classification": cm_u, "regression": rm_u},
        "delta": {"pr_auc": d_pr, "r2": d_r2, "pr_auc_retention": retention},
        "feature_distortion": {f: rel for rel, f, _ in diffs},
    }
    # numpy scalars are not JSON-serialisable; coerce on the way out.
    (args.out_dir / "source_comparison.json").write_text(
        json.dumps(payload, indent=2, default=lambda o: float(o)))
    print(f"\nSaved {args.out_dir / 'source_comparison.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
