# Deployment

The public demo runs as a single Cloud Run service. FastAPI serves the API and the static frontend from [index.html](file:///Users/sonil/Desktop/HyLeakAI/app/web/index.html), providing a single origin, a single URL, and zero CORS configuration overhead.

| Attribute | Value |
|---|---|
| Live URL | https://hyleakai-152424867743.asia-south1.run.app |
| GCP project | `hileak` (project number `152424867743`) |
| Region | `asia-south1` |
| Service | `hyleakai` |
| Sizing | 1 vCPU, 1 GiB, `min-instances=0`, startup CPU boost |

Setting `min-instances=0` allows the service to scale to zero when idle. The first request after an idle period incurs a cold start (~10 to 20 s to import PyTorch and load the checkpoint). Every subsequent request completes in under a second. Startup CPU boost shortens that initial cold start.

## Endpoints

| Path | Purpose |
|---|---|
| `GET /` | Static frontend application |
| `GET /health` | Returns `{"status": "ready"}` once artifacts load, or `"degraded"` if missing |
| `GET /v1/simulations` | Returns held-out test simulation IDs |
| `GET /v1/metadata` | Displays model specifications, grid parameters, and limitations |
| `GET /v1/fields/{simulation_id}` | Returns U-Net predicted pressure, saturation, and static geology grids |
| `POST /v1/assessments` | Runs U-Net surrogate and XGBoost risk screen (sampled or custom faults) |
| `POST /v1/site-screen` | Computes first-pass volumetric capacity, pressure, and flag analysis |

The `/v1/assessments` endpoint rejects any `simulation_id` outside the held-out test split with a 422 error. This design prevents scoring training simulations that would report unearned accuracy on unseen geology.

## CI/CD

The workflow [deploy-cloud-run.yml](file:///Users/sonil/Desktop/HyLeakAI/.github/workflows/deploy-cloud-run.yml) deploys on every push to `main` that touches `api/`, `src/`, `app/web/`, [Dockerfile](file:///Users/sonil/Desktop/HyLeakAI/Dockerfile), `requirements-api.txt`, or either ignore file. You can also trigger it manually via **workflow_dispatch**.

> **Note:** GitHub provides the manual "Run workflow" button only for workflows on the default branch. Merging this file to `main` enables manual triggers.

### Authentication: zero long-lived secrets

Authentication relies on **Workload Identity Federation**. GitHub mints a short-lived OIDC token, Google exchanges it for a credential valid for one hour, and the trust policy accepts only tokens whose `repository` claim matches `Sonil15/HyLeakAI`.

This design provides two advantages over service-account JSON keys. First, no long-lived credential exists to leak. Second, contributors can ship updates without repository admin rights because all workflow values remain non-secret.

Forks cannot reuse these values. A fork's OIDC token carries its own repository name, which GCP rejects.

GCP-side resources:

- Service account `github-deployer@hileak.iam.gserviceaccount.com`
- Roles: `run.admin`, `cloudbuild.builds.editor`, `artifactregistry.writer`, `logging.viewer`, plus `iam.serviceAccountUser` on the compute service account
- Bucket-scoped storage permissions: `storage.admin` on the Cloud Build source bucket and `storage.objectViewer` on the artifact bucket
- Workload Identity Federation pool `github`, provider `github-provider`, restricted by the attribute condition `assertion.repository=='Sonil15/HyLeakAI'`

## Model artifacts

The [Dockerfile](file:///Users/sonil/Desktop/HyLeakAI/Dockerfile) copies six files that git ignores. They reside in `gs://hileak-artifacts-152424867743/v1/` and the workflow fetches them before building:

| File | Size |
|---|---|
| `data/constants.npy` | 125 MB |
| `checkpoints/unet_small_best.pt` | 89 MB |
| `outputs/xgb_classifier.ubj` | 2.0 MB |
| `data/stats.json`, `outputs/shap_features.json`, `outputs/xgb_results.json` | small |

The build excludes `data/states.npy` (5.9 GB) intentionally. The U-Net predicts state fields from geology, so inference requires only `constants.npy`.

**Re-uploading weights after retraining:**

```bash
gcloud storage cp data/constants.npy data/stats.json \
  checkpoints/unet_small_best.pt \
  outputs/xgb_classifier.ubj outputs/shap_features.json outputs/xgb_results.json \
  gs://hileak-artifacts-152424867743/v1/ --project hileak
```

The `v1/` prefix enables deploying future weight revisions to `v2/` and rolling back by editing one line in the workflow.

## Cost

Cloud Run provides a perpetual free tier: 2 million requests, 360,000 GiB-seconds, and 180,000 vCPU-seconds per month. At `min-instances=0` the service charges only while processing requests, keeping demonstration traffic within free limits.

Ongoing storage costs remain under $0.10 per month for ~216 MB in the artifact bucket and container images in Artifact Registry. Maintaining `min-instances=0` keeps costs near zero. Setting `min-instances=1` would bill continuous vCPU usage and exceed free limits.

## Troubleshooting

**Container startup failure:** When Cloud Run reports a generic container startup error, inspect the execution logs directly:

```bash
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="hyleakai"' \
  --project hileak --limit 50 --format="value(timestamp,textPayload)" --freshness=1h
```

**Missing module error (`ModuleNotFoundError: No module named 'src.data.dataset'`):** The `.gcloudignore` pattern `data/*` previously matched `src/data/*` because gcloud unanchored wildcard patterns. Anchoring artifact patterns with a leading slash in [.gcloudignore](file:///Users/sonil/Desktop/HyLeakAI/.gcloudignore) resolved this issue. Verify build contexts using:

```bash
gcloud meta list-files-for-upload | grep src/data
```

**Degraded health status (`/health` returns `"degraded"`):** The container started but failed to load inference artifacts. Confirm the six artifact files exist in the GCP bucket and verify that [Dockerfile](file:///Users/sonil/Desktop/HyLeakAI/Dockerfile) `COPY` paths match the configured environment variables (`HYLEAK_DATA_DIR`, `HYLEAK_CHECKPOINT`, `HYLEAK_OUTPUT_DIR`).

## Manual deploy

Execute this command from a local checkout containing the downloaded artifacts to deploy manually:

```bash
gcloud run deploy hyleakai --source . --project hileak --region asia-south1 \
  --memory 1Gi --cpu 1 --cpu-boost --allow-unauthenticated \
  --min-instances 0 --port 8080 --timeout 300
```
