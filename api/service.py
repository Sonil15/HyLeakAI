"""Surrogate-only inference service shared by the FastAPI routes."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import asdict
from pathlib import Path

import numpy as np

from src import config as C
from src.leakage.features import fault_features, geology_features, global_features, operational_features
from src.leakage.labels import Fault, distance_to_fault_field, fault_cell_mask, sample_faults


class ArtifactError(RuntimeError):
    """The public inference artifact bundle is incomplete."""


class InferenceService:
    def __init__(self) -> None:
        root = Path(__file__).resolve().parent.parent
        self.data_dir = Path(os.getenv("HYLEAK_DATA_DIR", root / "data"))
        self.checkpoint_path = Path(os.getenv("HYLEAK_CHECKPOINT", root / "checkpoints" / "unet_small_best.pt"))
        self.output_dir = Path(os.getenv("HYLEAK_OUTPUT_DIR", root / "outputs"))
        self._ready = False

    def load(self) -> None:
        required = (self.data_dir / "constants.npy", self.data_dir / "stats.json", self.checkpoint_path,
                    self.output_dir / "xgb_classifier.ubj", self.output_dir / "shap_features.json")
        # The regressor is optional so an older artifact bundle still starts;
        # the flux forecast is simply omitted rather than the service refusing
        # to boot.
        self.regressor_path = self.output_dir / "xgb_regressor.ubj"
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise ArtifactError("Missing inference artifact(s): " + ", ".join(missing))

        import torch
        import xgboost as xgb
        from src.data.dataset import Normalizer, UHSDataset
        from src.models.unet import build_unet, load_state_dict_compat

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        checkpoint = torch.load(self.checkpoint_path, map_location=self.device, weights_only=False)
        self.normalizer = Normalizer.from_file(self.data_dir / "stats.json")
        meta = checkpoint.get("meta", {})
        self.dataset = UHSDataset("test", data_dir=self.data_dir, normalizer=self.normalizer,
                                  use_cyclic=meta.get("use_cyclic", True),
                                  use_distance=meta.get("use_distance", True), sim_ids=[0])
        self.model = build_unet(meta.get("size", "small"), self.dataset.in_channels, 2).to(self.device)
        load_state_dict_compat(self.model, checkpoint["model"])
        self.model.eval()
        self.torch = torch
        self.classifier = xgb.XGBClassifier()
        self.classifier.load_model(self.output_dir / "xgb_classifier.ubj")
        self.regressor = None
        if self.regressor_path.exists():
            self.regressor = xgb.XGBRegressor()
            self.regressor.load_model(self.regressor_path)
        self.feature_names = json.loads((self.output_dir / "shap_features.json").read_text())
        results = json.loads((self.output_dir / "xgb_results.json").read_text())
        self.horizon_steps = int(results["report_horizon"])
        horizon = results["horizons"][str(self.horizon_steps)]["full"]
        self.metrics = {
            "auc": float(horizon["classification"]["auc"]),
            "pr_auc": float(horizon["classification"]["pr_auc"]),
            "r2": float(horizon["regression"]["r2"]),
            "rmse": float(horizon["regression"]["rmse"]),
        }
        self.test_ids = C.simulation_splits()["test"]
        self._ready = True

    @property
    def ready(self) -> bool:
        return self._ready

    def predict_fields(self, simulation_id: int, timestep: int) -> tuple[np.ndarray, np.ndarray]:
        if simulation_id not in self.test_ids:
            raise ValueError("simulation_id must be a held-out test simulation")
        with self.torch.no_grad():
            x = self.dataset.build_input_tensor(simulation_id, timestep).unsqueeze(0).to(self.device)
            out = self.model(x).cpu().numpy()[0]
        return self.normalizer.pressure_inverse(out[0]).astype(np.float32), np.clip(out[1], 0, 1).astype(np.float32)

    def field_series(self, simulation_id: int) -> dict:
        """Every timestep of one simulation, for the 10-year animation.

        The U-Net predicts one timestep per forward pass -- the time scalar and
        cycle index are what distinguish step 7 from step 8 -- so a full cycle
        is 60 independent passes. Measured on one vCPU: 396 ms alone, 284 ms
        each when batched, about 17 s for the set.

        Two decisions follow from the size. The 60 x 2 x 128 x 128 result is
        7.9 MB as float32 and far larger again as JSON numbers, so each layer is
        quantised to uint8 against its own global range and base64'd, which is
        about 2 MB and decodes directly into ImageData in the browser.
        Quantisation is per-layer rather than per-frame on purpose: per-frame
        ranges would renormalise every step and the plume would appear to pulse
        while the real field was steady.

        One batched forward pass rather than 60 requests: the per-request
        overhead and repeated model warmup dominate otherwise.
        """
        if simulation_id not in self.test_ids:
            raise ValueError("simulation_id must be a held-out test simulation")

        steps = list(range(1, C.N_TIMESTEPS + 1))
        with self.torch.no_grad():
            batch = self.torch.stack([
                self.dataset.build_input_tensor(simulation_id, t) for t in steps
            ]).to(self.device)
            out = self.model(batch).cpu().numpy()

        pressure = self.normalizer.pressure_inverse(out[:, 0]).astype(np.float32)
        saturation = np.clip(out[:, 1], 0.0, 1.0).astype(np.float32)
        permeability = np.asarray(
            self.dataset.constants[simulation_id, C.CONST_PERMEABILITY], np.float32)

        def pack(stack: np.ndarray, lo: float, hi: float) -> str:
            span = (hi - lo) or 1.0
            q = np.clip((stack - lo) / span, 0.0, 1.0)
            return base64.b64encode((q * 255.0).round().astype(np.uint8).tobytes()).decode("ascii")

        p_lo, p_hi = float(pressure.min()), float(pressure.max())
        # Permeability spans nearly three decades, so it is packed in log space;
        # linear packing would put almost every cell in the bottom few codes.
        log_perm = np.log10(np.maximum(permeability, 1e-12))
        k_lo, k_hi = float(log_perm.min()), float(log_perm.max())

        return {
            "simulation_id": simulation_id,
            "timesteps": len(steps),
            "months_per_step": C.MONTHS_PER_STEP,
            "grid": {"width": C.GRID, "height": C.GRID, "extent_m": [0.0, C.DOMAIN_M, 0.0, C.DOMAIN_M]},
            "encoding": "uint8 per cell, row-major, frames concatenated; value = lo + code/255*(hi-lo)",
            "layers": {
                "pressure": {"data": pack(pressure, p_lo, p_hi), "range": [p_lo, p_hi],
                             "units": "bar", "source": "U-Net surrogate", "frames": len(steps)},
                "saturation": {"data": pack(saturation, 0.0, 1.0), "range": [0.0, 1.0],
                               "units": "fraction", "source": "U-Net surrogate", "frames": len(steps)},
                "permeability": {"data": pack(log_perm, k_lo, k_hi), "range": [k_lo, k_hi],
                                 "units": "log10 mD", "source": "dataset constant", "frames": 1},
            },
            "limitations": [
                "Surrogate fields, not a reservoir simulation.",
                "Held-out simulation: the model did not see this geology during training.",
            ],
        }

    def field_layers(self, simulation_id: int, timestep: int, layers: tuple[str, ...]) -> dict:
        """Return browser-ready grids with units and fixed provenance metadata.

        These values are model/data output, unlike the former procedural web
        illustration.  JSON is intentionally used for this first 128x128
        implementation: it keeps the contract inspectable while Cloud Run is
        being proven.  Tile/PNG delivery can replace it later without changing
        the semantic layer names or metadata.
        """
        pressure, saturation = self.predict_fields(simulation_id, timestep)
        constants = self.dataset.constants
        available = {
            "pressure": (pressure, "bar", "U-Net surrogate", [float(pressure.min()), float(pressure.max())]),
            "saturation": (saturation, "fraction", "U-Net surrogate", [0.0, 1.0]),
            "porosity": (np.asarray(constants[simulation_id, C.CONST_POROSITY], np.float32), "fraction", "dataset constant", None),
            "permeability": (np.asarray(constants[simulation_id, C.CONST_PERMEABILITY], np.float32), "mD", "dataset constant", None),
        }
        result = {}
        for name in layers:
            values, units, source, value_range = available[name]
            result[name] = {
                "values": values.tolist(),
                "units": units,
                "source": source,
                "range": value_range or [float(values.min()), float(values.max())],
            }
        return {
            "simulation_id": simulation_id,
            "timestep": timestep,
            "grid": {"width": C.GRID, "height": C.GRID, "extent_m": [0.0, C.DOMAIN_M, 0.0, C.DOMAIN_M]},
            "layers": result,
            "limitations": [
                "Pressure and saturation are U-Net surrogate predictions, not simulator truth fields.",
                "Porosity and permeability are synthetic geological-realisation inputs, not site measurements.",
            ],
        }

    def assess(self, simulation_id: int, timestep: int, faults: list[Fault]) -> dict:
        pressure, saturation = self.predict_fields(simulation_id, timestep)
        constants = self.dataset.constants
        porosity = np.asarray(constants[simulation_id, C.CONST_POROSITY], np.float32)
        permeability = np.asarray(constants[simulation_id, C.CONST_PERMEABILITY], np.float32)
        global_row = global_features(pressure, saturation, porosity, None, None)
        geology_row = geology_features(porosity, permeability)
        rows, results = [], []
        for fault in faults:
            distance = distance_to_fault_field(fault)
            features = fault_features(pressure, saturation, porosity, permeability, fault, distance, fault_cell_mask(distance))
            flux = float(features.pop("_q_now_m3_s"))
            row = {**global_row, **geology_row, **features, **operational_features(timestep)}
            vector = [row.get(name, 0.0) for name in self.feature_names]
            rows.append(vector)
            # The actual numbers handed to both models, per fault. Returned so
            # the interface can show what was fed in rather than only naming it:
            # a list of 41 feature names says nothing about whether the values
            # are sensible, and this is the level at which a reader can check.
            results.append({"fault": asdict(fault), "current_flux_m3_s": flux,
                            "features": {name: float(v) for name, v in zip(self.feature_names, vector)}})
        matrix = np.asarray(rows, np.float32)
        probabilities = self.classifier.predict_proba(matrix)[:, 1]

        # Exact TreeSHAP from the booster that produced the probability, so the
        # attribution explains THIS prediction rather than approximating it.
        # XGBoost's own pred_contribs is used rather than the shap package,
        # which cannot parse xgboost 3.2's base_score (serialised as the JSON
        # array '[2.37e-2]' instead of a scalar). Same algorithm, no version
        # conflict. The trailing column is the bias term, dropped so the array
        # lines up with the feature names.
        contributions = None
        try:
            import xgboost as xgb
            raw = self.classifier.get_booster().predict(xgb.DMatrix(matrix), pred_contribs=True)
            contributions, base_logit = raw[:, :-1], float(raw[0, -1])
        except Exception:
            base_logit = None

        # Second head: the regressor predicts log10(Q + 1e-12) at the same
        # horizon. Reported as a forecast, never as a measured leak rate --
        # Q is a closed-form function of quantities that are themselves
        # features, so at the SAME timestep it would be arithmetic. The only
        # genuine learning content is how the fields evolve over the horizon.
        forecasts = (self.regressor.predict(matrix) if self.regressor is not None
                     else [None] * len(rows))

        for index, (result, probability, log_q) in enumerate(zip(results, probabilities, forecasts, strict=True)):
            result["elevated_leakage_probability"] = float(probability)
            if contributions is not None:
                # Only the terms that moved this prediction. All 41 would bury
                # the handful that matter under a list of near-zeros, and the
                # full vector is already available under "features".
                row = contributions[index]
                ranked = sorted(zip(self.feature_names, row), key=lambda kv: -abs(kv[1]))
                result["contributions"] = [
                    {"feature": name, "value": float(v)} for name, v in ranked[:8] if abs(v) > 1e-6
                ]
                result["contribution_base_logit"] = base_logit
            if log_q is not None:
                result["forecast_log10_q"] = float(log_q)
                # Below the 1e-12 floor used when building the label, the
                # value is indistinguishable from no flux at all.
                result["forecast_q_m3_s"] = float(10.0 ** log_q) if log_q > -11.5 else 0.0
        return {
            "simulation_id": simulation_id, "timestep": timestep, "field_source": "U-Net surrogate",
            "forecast_horizon_steps": self.horizon_steps,
            "forecast_horizon_months": self.horizon_steps * C.MONTHS_PER_STEP,
            "field_summary": {"peak_pressure_bar": global_row["p_max_bar"], "pressure_delta_bar": global_row["delta_p_bar"],
                              "plume_area_km2": global_row["plume_area_m2"] / 1e6, "caprock_margin": global_row["caprock_margin"]},
            "risk_summary": {
                "fault_count": len(results),
                "median_probability": float(np.median(probabilities)),
                "p90_probability": float(np.quantile(probabilities, 0.9)),
                "worst_case_probability": float(np.max(probabilities)),
                # Worst case rather than mean: a leakage screen is about the
                # pathway that fails, not the average pathway.
                "worst_forecast_log10_q": (float(np.max(forecasts)) if self.regressor is not None else None),
            },
            "models": {
                "fields": {"name": "U-Net surrogate", "predicts": ["pressure", "saturation"],
                           "inputs": ["porosity", "permeability", "time", "cycle index", "distance to well"]},
                "classifier": {"name": "XGBoost classifier", "predicts": "P(elevated leakage)",
                               "n_features": len(self.feature_names),
                               "pr_auc": self.metrics.get("pr_auc"), "auc": self.metrics.get("auc")},
                "regressor": ({"name": "XGBoost regressor", "predicts": "log10 flux at the horizon",
                               "n_features": len(self.feature_names),
                               "r2": self.metrics.get("r2"), "rmse_log10": self.metrics.get("rmse")}
                              if self.regressor is not None else None),
            },
            "feature_names": self.feature_names,
            # Where each group of features comes from, so the interface does not
            # have to hardcode provenance that only the server actually knows.
            "feature_sources": {
                "fault": "the sampled fault hypothesis, plus the predicted fields read at its cells",
                "plume": "computed from the U-Net predicted saturation field",
                "pressure": "computed from the U-Net predicted pressure field",
                "geology": "dataset porosity and permeability maps for this realisation",
                "operational": "the selected timestep and its position in the injection cycle",
            },
            "faults": results,
            "limitations": ["Physics-guided screening only; not a calibrated leak-rate prediction.",
                            "Fault and caprock properties are hypotheses, not measured site data.",
                            "Results use U-Net surrogate fields, not simulator truth fields."],
        }

    def sampled_faults(self, count: int, seed: int | None) -> list[Fault]:
        return sample_faults(count, seed=seed)
