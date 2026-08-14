"""FastAPI entrypoint for a public HyLeakAI demonstration service."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
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
