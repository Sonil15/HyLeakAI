# syntax=docker/dockerfile:1.7
#
# Single-image deployment: the FastAPI backend also serves the static frontend
# from app/web/, so there is one service, one domain, and no CORS.
#
# Targets Google Cloud Run, but the image is plain OCI and runs anywhere that
# takes a container (Fly, Render, local Docker).

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies before code: torch is a slow, ~800 MB install, and keeping it in
# its own layer means ordinary code edits do not re-run it.
COPY requirements-api.txt ./
RUN pip install -r requirements-api.txt

# Application code. src/ is required because api/service.py imports the model
# definition and the leakage physics from it.
COPY api/ api/
COPY src/ src/
COPY app/web/ app/web/

# Model artifacts (~216 MB), copied from the build context rather than
# downloaded from the private GitHub release.
#
# Why copy instead of download: Cloud Build has no first-class BuildKit secret,
# so a token would have to be passed as a build ARG and would then be
# recoverable from the image history. Copying needs no credential at all, which
# also means this image can be rebuilt by anyone with the repo checked out.
#
# .gcloudignore and .dockerignore both allow exactly these six paths through and
# exclude everything else under data/, checkpoints/ and outputs/ - in particular
# data/states.npy, which is 5.9 GB and is not needed, because the U-Net predicts
# the state fields from geology.
COPY data/constants.npy data/stats.json runtime_artifacts/data/
COPY checkpoints/unet_small_best.pt runtime_artifacts/checkpoints/
COPY outputs/xgb_classifier.ubj outputs/xgb_regressor.ubj outputs/shap_features.json outputs/xgb_results.json outputs/site_suitability_ranking.csv runtime_artifacts/outputs/

ENV HYLEAK_DATA_DIR=/app/runtime_artifacts/data \
    HYLEAK_CHECKPOINT=/app/runtime_artifacts/checkpoints/unet_small_best.pt \
    HYLEAK_OUTPUT_DIR=/app/runtime_artifacts/outputs

# Cloud Run injects PORT and expects the server to listen on it. The default
# keeps the image runnable outside Cloud Run.
ENV PORT=8080
EXPOSE 8080

# Shell form so ${PORT} expands; exec so uvicorn becomes PID 1 and receives
# SIGTERM directly, which lets Cloud Run shut instances down cleanly.
#
# One worker deliberately: the model is loaded once at startup and a second
# worker would double the ~415 MB resident footprint for no throughput gain on
# a single-vCPU instance.
CMD exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --workers 1
