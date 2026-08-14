"""Second stage: physics features -> leakage risk, with SHAP attributions.

Two heads on the same feature table:

  classification   will the fault flux one year from now exceed the risk
                   threshold?  (AUC / PR-AUC)
  regression       how large will it be?  (R^2 / RMSE on log10 flux)

Three things here exist to stop the result being flattering but empty:

  * Splits are by SIMULATION and are the SAME splits the U-Net used, so no
    simulation is ever in one stage's training set and another's test set.
  * `_q_now_m3_s` — the same physical quantity one cycle earlier — is excluded
    from the features. Leaving it in would reduce the task to copying it.
  * Every result is reported against a two-feature baseline (peak pressure and
    plume-to-fault distance). If ~30 engineered features cannot beat two
    obvious ones, the feature engineering has not earned its place and the
    honest thing is to say so.

Usage:
    python -m src.train_xgb --table data/features_train.npy
    python -m src.train_xgb --table data/features_train.npy --no-shap
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src import config as C
from src.leakage.features import feature_columns, label_columns, load_table


def split_rows(table: np.ndarray, columns: list[str]) -> dict[str, np.ndarray]:
    """Row masks per split, keyed off sim_id. Disjointness is asserted, not hoped for."""
    sim_col = table[:, columns.index("sim_id")].astype(int)
    splits = C.simulation_splits()
    masks = {name: np.isin(sim_col, ids) for name, ids in splits.items()}

    for a in ("train", "val", "test"):
        for b in ("train", "val", "test"):
            if a < b:
                overlap = set(splits[a]) & set(splits[b])
                assert not overlap, f"{a}/{b} simulation overlap: {sorted(overlap)[:5]}"
    covered = sum(m.sum() for m in masks.values())
    assert covered == len(table), f"{len(table) - covered} rows fell outside every split"
    print("OK splits disjoint and exhaustive: "
          + "  ".join(f"{k} {int(v.sum()):,} rows" for k, v in masks.items()))
    return masks


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    resid = y_true - y_pred
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    return {
        "r2": 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
        "rmse": float(np.sqrt(np.mean(resid**2))),
        "mae": float(np.mean(np.abs(resid))),
        "n": int(y_true.size),
    }


def classification_metrics(y_true: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    from sklearn.metrics import average_precision_score, roc_auc_score

    if len(np.unique(y_true)) < 2:
        return {"auc": float("nan"), "pr_auc": float("nan"),
                "positive_rate": float(y_true.mean()), "n": int(y_true.size)}
    return {
        "auc": float(roc_auc_score(y_true, scores)),
        "pr_auc": float(average_precision_score(y_true, scores)),
        "positive_rate": float(y_true.mean()),
        "n": int(y_true.size),
    }


def persistence_baseline(table, columns, masks, horizon: int) -> dict:
    """The control that actually matters: assume next year looks like this year.

    UHS operates on a 12-month cycle and our forecast horizon is 6 timesteps =
    exactly one cycle, so the observed timestep and the labelled timestep sit at
    the SAME phase of consecutive annual cycles. The fields are therefore highly
    similar year to year, and simply carrying today's flux forward is a strong
    predictor.

    Any model that does not clearly beat this is not forecasting — it is
    re-evaluating the label's own formula on current values and relying on the
    system's periodicity. This baseline is the honest yardstick; the
    (peak pressure, plume distance) one is far too weak to expose the problem.
    """
    names = label_columns(horizon)
    qi = columns.index("_q_now_m3_s")
    out = {}
    for split in ("val", "test"):
        rows = table[masks[split]]
        q_now = rows[:, qi]
        out[split] = {
            "classification": classification_metrics(
                rows[:, columns.index(names["leak"])], q_now
            ),
            "regression": regression_metrics(
                rows[:, columns.index(names["log_q"])],
                np.log10(q_now + 1e-12),
            ),
        }
    return out


def tree_shap(clf, X: np.ndarray) -> np.ndarray:
    """Exact TreeSHAP values, shape (n_rows, n_features).

    Uses XGBoost's own `pred_contribs` rather than the `shap` package: shap
    0.49 cannot parse xgboost 3.2's `base_score`, which it serialises as the
    JSON array '[2.37e-2]' instead of a scalar. Same algorithm, no version
    conflict. The trailing column returned by XGBoost is the bias term, which we
    drop so the array lines up with the feature names.
    """
    import xgboost as xgb

    contribs = clf.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)
    return contribs[:, :-1]


def fit_models(table, columns, masks, feats, args, horizon: int):
    import xgboost as xgb

    names = label_columns(horizon)
    fi = [columns.index(c) for c in feats]
    X = {k: table[m][:, fi] for k, m in masks.items()}
    y_cls = {k: table[m][:, columns.index(names["leak"])] for k, m in masks.items()}
    y_reg = {k: table[m][:, columns.index(names["log_q"])] for k, m in masks.items()}

    common = dict(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        learning_rate=args.learning_rate,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        reg_lambda=1.0,
        n_jobs=args.n_jobs,
        random_state=args.seed,
        early_stopping_rounds=args.early_stopping,
        eval_metric="aucpr",
    )

    clf = xgb.XGBClassifier(objective="binary:logistic", **common)
    clf.fit(X["train"], y_cls["train"], eval_set=[(X["val"], y_cls["val"])], verbose=False)

    reg = xgb.XGBRegressor(
        objective="reg:squarederror", **{**common, "eval_metric": "rmse"}
    )
    reg.fit(X["train"], y_reg["train"], eval_set=[(X["val"], y_reg["val"])], verbose=False)

    return clf, reg, X, y_cls, y_reg


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", type=Path, default=C.DATA_DIR / "features.npy")
    ap.add_argument("--out-dir", type=Path, default=C.OUTPUT_DIR)
    ap.add_argument("--n-estimators", type=int, default=600)
    ap.add_argument("--max-depth", type=int, default=6)
    ap.add_argument("--learning-rate", type=float, default=0.05)
    ap.add_argument("--early-stopping", type=int, default=50)
    ap.add_argument("--n-jobs", type=int, default=12)
    ap.add_argument("--seed", type=int, default=C.SPLIT_SEED)
    ap.add_argument("--shap-samples", type=int, default=5000)
    ap.add_argument("--no-shap", action="store_true")
    ap.add_argument("--dump-predictions", action="store_true",
                    help="write held-out scores and labels for the reported horizon to "
                         "xgb_test_predictions.npz. Needed by src.economics.voi, which "
                         "requires an ROC — the summary metrics in xgb_results.json fix "
                         "AUC and PR-AUC but not the sensitivity/specificity pair at any "
                         "particular operating point.")
    ap.add_argument("--horizons", type=int, nargs="+", default=None,
                    help="horizons to sweep (default: all present in the table)")
    ap.add_argument("--report-horizon", type=int, default=None,
                    help="horizon whose model is saved and explained "
                         "(default: the one with the largest gain over persistence)")
    args = ap.parse_args()

    table, columns, meta = load_table(args.table)
    print(f"Table: {table.shape[0]:,} rows x {table.shape[1]} columns")

    available = sorted(int(c.split("h")[-1]) for c in columns if c.startswith("q_future_h"))
    horizons = sorted(set(args.horizons)) if args.horizons else available
    missing = set(horizons) - set(available)
    if missing:
        ap.error(f"table has no labels for horizons {sorted(missing)}; it has {available}")
    # Which horizon's model do we actually ship? Not the longest — the one where
    # the model adds most over persistence. A horizon at which a trivial baseline
    # already scores ~0.99 is not a forecasting task, however good the model looks
    # on it. Resolved after the sweep; None means "decide from the results".
    report_h = args.report_horizon

    all_masks = split_rows(table, columns)
    feats = feature_columns(columns)
    print(f"Features: {len(feats)}   Horizons available: {available}")

    baseline_feats = [f for f in ("p_max_bar", "distance_plume_to_fault_m") if f in feats]
    results: dict[str, dict] = {}
    sweep_rows = []
    trained: dict[int, tuple] = {}

    for h in horizons:
        names = label_columns(h)
        # Rows whose label ran past the end of the simulation are NaN; drop them
        # per horizon so each uses every row it legitimately can.
        finite = np.isfinite(table[:, columns.index(names["q"])])
        masks = {k: (m & finite) for k, m in all_masks.items()}
        months = h * C.MONTHS_PER_STEP
        cycles = h / C.STEPS_PER_CYCLE

        print("\n" + "=" * 74)
        print(f"HORIZON {h} timesteps = {months} months = {cycles:.2f} storage cycles"
              f"   ({int(finite.sum()):,} usable rows)")
        same_phase = h % C.STEPS_PER_CYCLE == 0
        print(f"  observed and labelled steps are at "
              f"{'the SAME phase of the cycle' if same_phase else 'DIFFERENT phases'}"
              f" -> {'fields nearly repeat' if same_phase else 'fields must actually evolve'}")

        clf, reg, X, y_cls, y_reg = fit_models(table, columns, masks, feats, args, h)
        cm = classification_metrics(y_cls["test"], clf.predict_proba(X["test"])[:, 1])
        rm = regression_metrics(y_reg["test"], reg.predict(X["test"]))

        clf_b, reg_b, Xb, ycb, yrb = fit_models(
            table, columns, masks, baseline_feats, args, h)
        cmb = classification_metrics(ycb["test"], clf_b.predict_proba(Xb["test"])[:, 1])
        rmb = regression_metrics(yrb["test"], reg_b.predict(Xb["test"]))

        pers = persistence_baseline(table, columns, masks, h)["test"]
        cmp_, rmp = pers["classification"], pers["regression"]

        d_pr = cm["pr_auc"] - cmp_["pr_auc"]
        d_r2 = rm["r2"] - rmp["r2"]
        print(f"  full model    PR-AUC {cm['pr_auc']:.4f}  AUC {cm['auc']:.4f}  "
              f"log-flux R2 {rm['r2']:+.4f}")
        print(f"  weak baseline PR-AUC {cmb['pr_auc']:.4f}  AUC {cmb['auc']:.4f}  "
              f"log-flux R2 {rmb['r2']:+.4f}")
        print(f"  persistence   PR-AUC {cmp_['pr_auc']:.4f}  AUC {cmp_['auc']:.4f}  "
              f"log-flux R2 {rmp['r2']:+.4f}")
        print(f"  --> gain over persistence: PR-AUC {d_pr:+.4f}   R2 {d_r2:+.4f}")

        results[str(h)] = {
            "months": months, "cycles": cycles, "usable_rows": int(finite.sum()),
            "same_phase": bool(same_phase),
            "full": {"classification": cm, "regression": rm},
            "weak_baseline": {"classification": cmb, "regression": rmb},
            "persistence": pers,
            "gain_over_persistence": {"pr_auc": d_pr, "r2": d_r2},
        }
        sweep_rows.append((h, months, cm["pr_auc"], cmp_["pr_auc"], d_pr,
                           rm["r2"], rmp["r2"], d_r2))
        trained[h] = (clf, reg, X, masks, y_cls)

    # -- the summary that actually answers the question --
    print("\n" + "=" * 74)
    print("HORIZON SWEEP (test set)")
    print(f"{'steps':>5} {'months':>7} | {'PR-AUC':>7} {'persist':>8} {'gain':>8} "
          f"| {'R2':>8} {'persist':>8} {'gain':>8}")
    print("-" * 74)
    for h, mo, pr, prp, dpr, r2, r2p, dr2 in sweep_rows:
        flag = "  <- same phase" if h % C.STEPS_PER_CYCLE == 0 else ""
        print(f"{h:>5} {mo:>7} | {pr:>7.4f} {prp:>8.4f} {dpr:>+8.4f} "
              f"| {r2:>8.4f} {r2p:>+8.4f} {dr2:>+8.4f}{flag}")

    print("\nHOW TO READ THIS")
    print("  The T3 label is a closed-form function of quantities that appear in the")
    print("  feature vector (fault permeability and area, pressure and saturation at")
    print("  the fault). At the same timestep it is pure algebra. The only real task")
    print("  is predicting how the fields EVOLVE over the horizon, so:")
    print("    - persistence PR-AUC near 1.0 means the horizon is too easy to be")
    print("      informative, whatever the model scores;")
    print("    - the gain over persistence is the only column worth quoting.")
    best = max(sweep_rows, key=lambda r: r[4])
    print(f"\n  Largest gain over persistence: horizon {best[0]} "
          f"({best[1]} months), PR-AUC {best[4]:+.4f}, R2 {best[7]:+.4f}.")
    trivial = [r[0] for r in sweep_rows if r[3] > 0.9]
    if trivial:
        print(f"  Horizons where persistence alone exceeds 0.9 PR-AUC: {trivial}.")
        print("  These are not forecasting tasks. Do not quote a headline score from them.")
    print("=" * 74)

    if report_h is None:
        report_h = best[0]
    clf, reg, X, masks, y_cls = trained[report_h]
    print(f"\nSaving the horizon-{report_h} model "
          f"({report_h * C.MONTHS_PER_STEP} months) — "
          f"{'largest gain over persistence' if report_h == best[0] else 'requested'}.")

    # -- importance / SHAP --
    args.out_dir.mkdir(parents=True, exist_ok=True)
    gain = clf.get_booster().get_score(importance_type="gain")
    ranked = sorted(
        ((feats[int(k[1:])], v) for k, v in gain.items()), key=lambda kv: -kv[1]
    )
    print("\nTop features by gain (classifier):")
    for name, value in ranked[:12]:
        print(f"  {name:34s} {value:10.2f}")

    if not args.no_shap:
        n = min(args.shap_samples, int(masks["test"].sum()))
        rng = np.random.default_rng(args.seed)
        idx = rng.choice(X["test"].shape[0], size=n, replace=False)
        values = tree_shap(clf, X["test"][idx])
        mean_abs = np.abs(values).mean(axis=0)
        order = np.argsort(-mean_abs)
        print(f"\nTop features by mean |SHAP| ({n:,} test rows):")
        for i in order[:12]:
            print(f"  {feats[i]:34s} {mean_abs[i]:10.5f}")
        np.save(args.out_dir / "shap_values_test.npy", values)
        np.save(args.out_dir / "shap_rows_test.npy", idx)
        (args.out_dir / "shap_features.json").write_text(json.dumps(feats, indent=2))

    if args.dump_predictions:
        # `sim_id` travels with the scores because a screening decision is taken
        # per SITE, not per row: a site carries ~20 fault hypotheses x 60
        # timesteps, and pooling them as if they were independent trials would
        # overstate how much the screen actually resolves.
        test_rows = table[masks["test"]]
        scores = clf.predict_proba(X["test"])[:, 1]
        y_true = y_cls["test"]
        assert scores.shape == y_true.shape == (test_rows.shape[0],), (
            f"prediction dump misaligned: scores {scores.shape}, "
            f"labels {y_true.shape}, rows {test_rows.shape[0]}")
        np.savez_compressed(
            args.out_dir / "xgb_test_predictions.npz",
            y_true=y_true.astype(np.int8),
            y_score=scores.astype(np.float32),
            sim_id=test_rows[:, columns.index("sim_id")].astype(np.int16),
            timestep=test_rows[:, columns.index("timestep")].astype(np.int16),
            horizon=np.int16(report_h),
            leak_threshold_m3_s=np.float64(
                meta["leak_thresholds_m3_s"][str(report_h)]),
        )
        print(f"Dumped {y_true.size:,} held-out predictions "
              f"({int(y_true.sum()):,} positive, {y_true.mean():.4%}) "
              f"to {args.out_dir / 'xgb_test_predictions.npz'}")

    clf.save_model(args.out_dir / "xgb_classifier.ubj")
    reg.save_model(args.out_dir / "xgb_regressor.ubj")
    (args.out_dir / "xgb_results.json").write_text(
        json.dumps(
            {"horizons": results, "report_horizon": report_h, "features": feats,
             "importance_gain": dict(ranked), "table_meta": meta},
            indent=2,
        )
    )
    print(f"\nSaved models and results to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
