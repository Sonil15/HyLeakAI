"""FastAPI entrypoint for a public HyLeakAI demonstration service."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from api.service import ArtifactError, InferenceService
from src import config as C
from src.leakage.labels import Fault

service = InferenceService()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        service.load()
    except ArtifactError:
        # Keep /health available while an incomplete demo image is diagnosed.
        pass
    yield


app = FastAPI(title="HyLeakAI API", version="0.1.0", lifespan=lifespan)
allowed_origins = os.getenv("HYLEAK_ALLOWED_ORIGINS", "https://sonil15.github.io").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class FaultInput(BaseModel):
    x_m: float = Field(ge=0, le=C.DOMAIN_M)
    y_m: float = Field(ge=0, le=C.DOMAIN_M)
    length_m: float = Field(gt=0, le=C.DOMAIN_M)
    width_m: float = Field(gt=0, le=1000)
    permeability_m2: float = Field(gt=0, le=1e-8)
    orientation_rad: float = Field(ge=0, le=3.141592653589793)


class AssessmentRequest(BaseModel):
    simulation_id: int
    timestep: int = Field(ge=1, le=C.N_TIMESTEPS)
    mode: Literal["sampled_ensemble", "custom_faults"] = "sampled_ensemble"
    fault_count: int = Field(default=20, ge=1, le=50)
    seed: int | None = None
    faults: list[FaultInput] | None = None

    @model_validator(mode="after")
    def validate_fault_selection(self):
        if self.mode == "custom_faults" and not self.faults:
            raise ValueError("faults is required when mode is custom_faults")
        return self


class SiteScreenRequest(BaseModel):
    """Transparent volumetric screen; deliberately separate from the surrogate."""

    area_km2: float = Field(default=25, gt=0, le=10_000)
    reservoir_thickness_m: float = Field(default=80, gt=0, le=2_000)
    porosity_fraction: float = Field(default=0.18, gt=0.01, le=0.5)
    storage_efficiency_fraction: float = Field(default=0.04, gt=0.001, le=0.2)
    co2_density_kg_m3: float = Field(default=650, gt=100, le=1_200)
    depth_m: float = Field(default=1_800, gt=0, le=10_000)
    brine_density_kg_m3: float = Field(default=1_050, gt=800, le=1_300)
    allowable_overpressure_bar: float = Field(default=50, gt=0, le=500)
    injection_rate_mtpa: float = Field(default=1.0, gt=0, le=100)
    injection_years: float = Field(default=20, gt=0, le=100)
    caprock_thickness_m: float = Field(default=120, gt=0, le=2_000)


@app.post("/v1/site-screen")
def site_screen(request: SiteScreenRequest):
    """Return reproducible first-pass capacity and pressure quantities.

    This uses only the supplied scalars.  It is a volumetric feasibility
    calculation, not a substitute for compositional flow simulation, geomechanics,
    site-specific capillary pressure or a permit-ready capacity estimate.
    """
    area_m2 = request.area_km2 * 1_000_000
    bulk_volume_m3 = area_m2 * request.reservoir_thickness_m
    pore_volume_m3 = bulk_volume_m3 * request.porosity_fraction
    effective_pore_volume_m3 = pore_volume_m3 * request.storage_efficiency_fraction
    capacity_mt = effective_pore_volume_m3 * request.co2_density_kg_m3 / 1_000_000_000
    planned_mass_mt = request.injection_rate_mtpa * request.injection_years
    hydrostatic_pressure_bar = request.brine_density_kg_m3 * 9.80665 * request.depth_m / 100_000
    utilization = planned_mass_mt / capacity_mt if capacity_mt else float("inf")
    flags = []
    if utilization > 1:
        flags.append("Planned injected mass exceeds this first-pass effective capacity.")
    if request.depth_m < 800:
        flags.append("Depth is below a commonly used initial screen for dense-phase CO2; confirm pressure-temperature conditions.")
    if request.caprock_thickness_m < 30:
        flags.append("Thin caprock input: assess seal continuity, entry pressure and geomechanical integrity.")
    if not flags:
        flags.append("No scalar-screen flag triggered; validate with site data, dynamic simulation and geomechanics.")
    return {
        "screen_type": "volumetric first-pass only",
        "inputs_used": request.model_dump(),
        "results": {
            "bulk_volume_m3": bulk_volume_m3,
            "pore_volume_m3": pore_volume_m3,
            "effective_pore_volume_m3": effective_pore_volume_m3,
            "capacity_mt_co2": capacity_mt,
            "planned_mass_mt_co2": planned_mass_mt,
            "capacity_utilization_fraction": utilization,
            "hydrostatic_pressure_bar": hydrostatic_pressure_bar,
            "pressure_ceiling_bar": hydrostatic_pressure_bar + request.allowable_overpressure_bar,
        },
        "flags": flags,
        "limitations": [
            "No relative permeability, salinity, temperature, structural closure, residual trapping or pressure dissipation is modelled.",
            "Do not use this output for permitting, reserves, injection design or a storage resource estimate.",
        ],
    }


def require_ready() -> None:
    if not service.ready:
        raise HTTPException(status_code=503, detail="Inference artifacts are not loaded; frontend preview mode remains available.")


@app.get("/health")
def health():
    return {"status": "ready" if service.ready else "degraded", "service": "HyLeakAI API", "mode": "surrogate screening"}


@app.get("/v1/simulations")
def simulations():
    require_ready()
    return {"simulation_ids": service.test_ids, "field_source": "held-out geological realisations"}


@app.get("/v1/metadata")
def metadata():
    """Stable display metadata for clients and exports."""
    require_ready()
    return {
        "api_version": app.version,
        "model": {"field_source": "U-Net surrogate", "risk_model": "XGBoost classifier"},
        "grid": {"width": C.GRID, "height": C.GRID, "domain_m": C.DOMAIN_M},
        "time": {"timesteps": C.N_TIMESTEPS, "months_per_step": C.MONTHS_PER_STEP},
        "limitations": [
            "Physics-guided screening only; not a calibrated leak-rate prediction.",
            "Fault and caprock properties are hypotheses, not measured site data.",
        ],
    }


@app.get("/v1/fields/{simulation_id}")
def fields(
    simulation_id: int,
    timestep: int = Query(ge=1, le=C.N_TIMESTEPS),
    layers: str = Query("pressure,saturation"),
):
    """Actual U-Net field grids and static geology for a held-out realisation."""
    require_ready()
    requested = tuple(part.strip().lower() for part in layers.split(",") if part.strip())
    allowed = {"pressure", "saturation", "porosity", "permeability"}
    unknown = set(requested) - allowed
    if not requested or unknown:
        raise HTTPException(status_code=422, detail=f"layers must use: {', '.join(sorted(allowed))}")
    try:
        return service.field_layers(simulation_id, timestep, requested)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/assessments")
def assessment(request: AssessmentRequest):
    require_ready()
    try:
        faults = (
            [Fault(fault_id=i, **fault.model_dump()) for i, fault in enumerate(request.faults or [])]
            if request.mode == "custom_faults"
            else service.sampled_faults(request.fault_count, request.seed)
        )
        return service.assess(request.simulation_id, request.timestep, faults)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# Serve the frontend from this same app, so one Fly deployment covers both and
# the browser never makes a cross-origin request.
#
# This mount MUST stay at the bottom of the file: mounting at "/" catches every
# path that has not already been registered, so moving it above the routes
# would shadow /health and /v1/*.
#
# The directory is optional on purpose — running the API alone (tests, a local
# uvicorn, an image built without app/web/) should not fail here.
WEB_DIR = Path(__file__).resolve().parent.parent / "app" / "web"
if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
