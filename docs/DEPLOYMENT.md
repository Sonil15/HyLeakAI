# Deployment

The public demo is one Cloud Run service. FastAPI serves the API *and* the
static frontend from `app/web/`, so there is a single origin, a single URL, and
no CORS to configure.

| | |
|---|---|
| Live URL | https://hyleakai-152424867743.asia-south1.run.app |
| GCP project | `hileak` (project number `152424867743`) |
| Region | `asia-south1` |
| Service | `hyleakai` |
| Sizing | 1 vCPU, 1 GiB, `min-instances=0`, startup CPU boost |

`min-instances=0` means the service scales to zero when idle. The first request
after an idle period pays a cold start (~10-20 s: importing torch and loading
the checkpoint). Every subsequent request is under a second. Startup CPU boost
is on specifically to shorten that cold start.

## Endpoints

| Path | Purpose |
|---|---|
| `GET /` | Frontend |
| `GET /health` | `{"status": "ready"}` once artifacts are loaded, `"degraded"` if not |
| `GET /v1/simulations` | The held-out test simulation IDs (the only valid inputs) |
| `POST /v1/assessments` | Runs the U-Net surrogate + XGBoost risk screen |

`/v1/assessments` rejects any `simulation_id` outside the held-out test split
with a 422. That is deliberate — scoring a training simulation would report an
accuracy the model does not have on unseen geology.

## CI/CD

`.github/workflows/deploy-cloud-run.yml` deploys on every push to `main` that
touches `api/`, `src/`, `app/web/`, the `Dockerfile`, `requirements-api.txt`, or
either ignore file. It can also be run manually via **workflow_dispatch**.

> **Note:** GitHub only offers the manual "Run workflow" button for workflows
> that exist on the *default* branch. Until this file is merged to `main`, the
> workflow cannot be triggered manually — merging is what turns it on.

### Authentication: no secrets, no keys

Auth is **Workload Identity Federation**. GitHub mints a short-lived OIDC token,
Google exchanges it for a credential valid about an hour, and the trust policy
accepts only tokens whose `repository` claim is exactly `Sonil15/HyLeakAI`.

This was chosen over a service-account JSON key for two reasons. First, no
long-lived credential exists to leak. Second — and decisively here — creating a
repository secret requires **admin** on the repo, which contributors do not
have; every value in the workflow is non-secret, so a contributor can ship the
pipeline without waiting on the owner.

A fork cannot reuse these values: its OIDC token carries the fork's own
repository name and the exchange is rejected.

GCP-side resources, already created:

- Service account `github-deployer@hileak.iam.gserviceaccount.com`
- Roles: `run.admin`, `cloudbuild.builds.editor`, `artifactregistry.writer`,
  `logging.viewer`, plus `iam.serviceAccountUser` on the compute service account
- Storage is **bucket-scoped, not project-wide**: `storage.admin` on the Cloud
  Build source bucket and `storage.objectViewer` on the artifact bucket
- WIF pool `github`, provider `github-provider`, restricted by the attribute
  condition `assertion.repository=='Sonil15/HyLeakAI'`

## Model artifacts

The Dockerfile `COPY`s six files that are **gitignored** and so are absent from
a fresh checkout. They live in `gs://hileak-artifacts-152424867743/v1/` and the
workflow pulls them before building:

| File | Size |
|---|---|
| `data/constants.npy` | 125 MB |
| `checkpoints/unet_small_best.pt` | 89 MB |
| `outputs/xgb_classifier.ubj` | 2.0 MB |
| `data/stats.json`, `outputs/shap_features.json`, `outputs/xgb_results.json` | small |

`data/states.npy` (5.9 GB) is deliberately **not** deployed. The U-Net predicts
the state fields from geology, so only `constants.npy` is needed at inference.

**After retraining, re-upload or CI will keep deploying the old weights:**

```bash
gcloud storage cp data/constants.npy data/stats.json \
  checkpoints/unet_small_best.pt \
  outputs/xgb_classifier.ubj outputs/shap_features.json outputs/xgb_results.json \
  gs://hileak-artifacts-152424867743/v1/ --project hileak
```

The `v1/` prefix exists so a future weight revision can go to `v2/` and be rolled
back by changing one line in the workflow.

## Cost

Cloud Run's free tier is perpetual, not a trial: 2 million requests, 360,000
GiB-seconds, and 180,000 vCPU-seconds per month. At `min-instances=0` the
service bills only while serving a request, so a demo handling a few thousand
requests stays inside it comfortably.

The two ongoing charges are trivial: ~216 MB in the artifact bucket and the
container images in Artifact Registry, together well under $0.10/month. Keeping
`min-instances=0` is what keeps this near zero — setting it to 1 would bill a
vCPU continuously and blow through the free tier in days.

## Troubleshooting

**"The user-provided container failed to start and listen on the port."** This
message says nothing about the cause. The cause is in the logs:

```bash
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="hyleakai"' \
  --project hileak --limit 50 --format="value(timestamp,textPayload)" --freshness=1h
```

**`ModuleNotFoundError: No module named 'src.data.dataset'`** — this happened,
and it is worth knowing about. The `data/*` line in `.gcloudignore`, present to
keep the 5.9 GB `states.npy` out, *also matched* `src/data/*`. gcloud's ignore
matcher does not anchor a `dir/*` pattern to the context root the way git does,
so `src/data/` uploaded as an empty directory. Every artifact pattern is now
anchored with a leading slash, and the workflow's **Verify build context** step
fails with the actual filename rather than the opaque port message. Check any
change to either ignore file with:

```bash
gcloud meta list-files-for-upload | grep src/data
```

**`/health` returns `"degraded"`** — the container is up but artifacts failed to
load. Confirm the six files are in the bucket and that the `COPY` paths in the
Dockerfile match `HYLEAK_DATA_DIR` / `HYLEAK_CHECKPOINT` / `HYLEAK_OUTPUT_DIR`.

## Manual deploy

CI is the normal path, but this works from a checkout that has the artifacts:

```bash
gcloud run deploy hyleakai --source . --project hileak --region asia-south1 \
  --memory 1Gi --cpu 1 --cpu-boost --allow-unauthenticated \
  --min-instances 0 --port 8080 --timeout 300
```
