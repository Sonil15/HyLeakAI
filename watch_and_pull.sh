#!/usr/bin/env bash
# Watch the Kaggle notebook run and pull its weights the moment they commit.
#
# Emits one line per meaningful event (status change, completion, download
# result) and then exits — so it produces a handful of notifications over a
# multi-hour run rather than a stream.
#
# Requires KAGGLE_BEARER (a KGAT_ token). The Kaggle CLI cannot be used here:
# it authenticates with Basic auth, which rejects KGAT_ tokens; the REST API
# accepts them as Bearer.
set -uo pipefail

T="${KAGGLE_BEARER:?set KAGGLE_BEARER}"
USER_NAME="${KAGGLE_USER:-onethybeing}"
SLUG="${KAGGLE_SLUG:-kaggle-train-unetea90265767}"
API="https://www.kaggle.com/api/v1"
DEST="${DEST:-checkpoints}"
POLL="${POLL:-300}"          # 5 minutes; a training run changes state slowly
MAX_HOURS="${MAX_HOURS:-14}" # Kaggle commits are capped at 12h

mkdir -p "$DEST"
auth=(-H "Authorization: Bearer $T")
deadline=$(( $(date +%s) + MAX_HOURS * 3600 ))
prev=""

get_status() {
  curl -s --max-time 60 "${auth[@]}" \
    "$API/kernels/status?userName=$USER_NAME&kernelSlug=$SLUG" \
  | python -c "import sys,json;print(json.load(sys.stdin).get('status','?'))" 2>/dev/null \
  || echo "netfail"
}

# Downloads every .pt/.json in the committed output. Prints one line per file
# plus a final summary line. Returns non-zero if nothing was retrieved.
pull_output() {
  local json="$DEST/.kaggle_output.json"
  curl -s --max-time 120 "${auth[@]}" \
    "$API/kernels/output?userName=$USER_NAME&kernelSlug=$SLUG" -o "$json" || return 1
  KAGGLE_BEARER="$T" DEST="$DEST" python - "$json" <<'PY'
import json, os, subprocess, sys
dest = os.environ["DEST"]
token = os.environ["KAGGLE_BEARER"]
files = json.load(open(sys.argv[1])).get("files", [])
wanted = [f for f in files if str(f.get("fileName", "")).endswith((".pt", ".json"))]
if not wanted:
    print(f"no downloadable files yet ({len(files)} listed)")
    raise SystemExit(1)
ok = 0
for f in wanted:
    name = os.path.basename(f["fileName"])
    out = os.path.join(dest, name)
    r = subprocess.run(
        ["curl", "-sL", "--max-time", "1800", "-H", f"Authorization: Bearer {token}",
         f["url"], "-o", out])
    size = os.path.getsize(out) if os.path.exists(out) else 0
    if r.returncode == 0 and size > 0:
        ok += 1
        print(f"pulled {name} ({size / 2**20:.1f} MiB)")
    else:
        print(f"FAILED {name}")
print(f"downloaded {ok}/{len(wanted)} file(s) into {dest}/")
raise SystemExit(0 if ok else 1)
PY
}

while :; do
  if [ "$(date +%s)" -gt "$deadline" ]; then
    echo "giving up after ${MAX_HOURS}h — Kaggle run never completed"
    exit 1
  fi

  st="$(get_status)"
  [ "$st" != "$prev" ] && { echo "kaggle status: $st"; prev="$st"; }

  case "$st" in
    running|queued|netfail)
      sleep "$POLL" ;;
    *)
      echo "run finished with status: $st — attempting to pull output"
      if pull_output; then
        echo "WEIGHTS RETRIEVED — ready to run the propagation measurement"
        exit 0
      fi
      # A finished run with no committed output means it was never saved as a
      # version; polling further will not change that.
      echo "run finished but committed NO output files; a browser download is required"
      exit 2 ;;
  esac
done
