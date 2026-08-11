#!/usr/bin/env bash
# Pull committed output from the Kaggle notebook into checkpoints/.
# Requires a Quick Save (committed version) on the Kaggle side first.
set -euo pipefail
T="${KAGGLE_BEARER:?set KAGGLE_BEARER to your KGAT_ token}"
REF_USER=onethybeing
REF_SLUG=kaggle-train-unetea90265767
API=https://www.kaggle.com/api/v1
mkdir -p checkpoints
curl -s -H "Authorization: Bearer $T" \
  "$API/kernels/output?userName=$REF_USER&kernelSlug=$REF_SLUG" -o /tmp/kout.json
python - <<'PY'
import json, os, subprocess
d = json.load(open('/tmp/kout.json'))
files = d.get('files', [])
print(f"{len(files)} output file(s)")
for f in files:
    name, url = f.get('fileName'), f.get('url')
    if not name.endswith(('.pt', '.json')):
        continue
    dest = os.path.join('checkpoints', os.path.basename(name))
    print(f"  -> {dest} ({f.get('size',0)/2**20:.1f} MiB)")
    subprocess.run(['curl','-sL','-H',f"Authorization: Bearer {os.environ['KAGGLE_BEARER']}",
                    url,'-o',dest], check=True)
PY
ls -la checkpoints/
