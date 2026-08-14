# syntax=docker/dockerfile:1.7
#
# Single-image deployment for Fly.io: the FastAPI backend also serves the
# static frontend from app/web/, so there is one app, one domain, and no CORS.
#
# Replaces the previous split of Render (backend) + GitHub Pages (frontend).

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies before code: torch is a slow, ~800 MB install, and this keeps it
# in a cached layer that ordinary code edits do not invalidate.
COPY requirements-api.txt ./
RUN pip install -r requirements-api.txt

# Application code. src/ is needed because api/service.py imports the model
# definition and leakage physics from it.
COPY api/ api/
COPY src/ src/
COPY scripts/ scripts/
COPY app/web/ app/web/

# Model artifacts (~216 MB) are baked into the image rather than downloaded on
# boot. Cold starts already pay for a torch import; adding a 216 MB download on
# top would make the first request after a scale-to-zero wake unusably slow.
#
# The token is a BuildKit secret, so it is never written to an image layer —
# unlike an ARG or ENV, which would be recoverable from `docker history`.
RUN --mount=type=secret,id=hyleak_token \
    HYLEAK_GITHUB_TOKEN="$(cat /run/secrets/hyleak_token)" \
    python scripts/download_api_artifacts.py

# Match the paths render.yaml used, so api/service.py finds the same layout.
ENV HYLEAK_DATA_DIR=/app/runtime_artifacts/data \
    HYLEAK_CHECKPOINT=/app/runtime_artifacts/checkpoints/unet_small_best.pt \
    HYLEAK_OUTPUT_DIR=/app/runtime_artifacts/outputs

# Fly routes to this port; it must match internal_port in fly.toml.
EXPOSE 8080

# One worker deliberately: the model is loaded into memory once at startup, and
# a second worker would double the resident footprint for no throughput gain on
# a shared-cpu-1x machine.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
