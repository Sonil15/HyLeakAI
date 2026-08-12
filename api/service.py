"""Surrogate-only inference service shared by the FastAPI routes."""

from __future__ import annotations

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
        self.feature_names = json.loads((self.output_dir / "shap_features.json").read_text())
        results = json.loads((self.output_dir / "xgb_results.json").read_text())
        self.horizon_steps = int(results["report_horizon"])
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
            rows.append([row.get(name, 0.0) for name in self.feature_names])
            results.append({"fault": asdict(fault), "current_flux_m3_s": flux})
        probabilities = self.classifier.predict_proba(np.asarray(rows, np.float32))[:, 1]
        for result, probability in zip(results, probabilities, strict=True):
            result["elevated_leakage_probability"] = float(probability)
        return {
            "simulation_id": simulation_id, "timestep": timestep, "field_source": "U-Net surrogate",
            "forecast_horizon_steps": self.horizon_steps,
            "forecast_horizon_months": self.horizon_steps * C.MONTHS_PER_STEP,
            "field_summary": {"peak_pressure_bar": global_row["p_max_bar"], "pressure_delta_bar": global_row["delta_p_bar"],
                              "plume_area_km2": global_row["plume_area_m2"] / 1e6, "caprock_margin": global_row["caprock_margin"]},
            "risk_summary": {"fault_count": len(results), "median_probability": float(np.median(probabilities)),
                             "p90_probability": float(np.quantile(probabilities, 0.9)), "worst_case_probability": float(np.max(probabilities))},
            "faults": results,
            "limitations": ["Physics-guided screening only; not a calibrated leak-rate prediction.",
                            "Fault and caprock properties are hypotheses, not measured site data.",
                            "Results use U-Net surrogate fields, not simulator truth fields."],
        }

    def sampled_faults(self, count: int, seed: int | None) -> list[Fault]:
        return sample_faults(count, seed=seed)
