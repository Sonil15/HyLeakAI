"""Download and verify the versioned inference bundle during a Render build."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import urllib.request
import zipfile
from pathlib import Path


DEFAULT_URL = (
    "https://api.github.com/repos/Sonil15/HyLeakAI/releases/assets/510448743"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", type=Path, default=Path("runtime_artifacts"))
    args = parser.parse_args()
    archive = args.output.with_suffix(".zip")
    shutil.rmtree(args.output, ignore_errors=True)
    args.output.mkdir(parents=True, exist_ok=True)
    print(f"Downloading inference artifacts from {args.url}")
    token = os.getenv("HYLEAK_GITHUB_TOKEN")
    if not token:
        raise SystemExit("HYLEAK_GITHUB_TOKEN is required to download the private release asset.")
    headers = {
        "Accept": "application/octet-stream",
        "Authorization": f"Bearer {token}",
        "User-Agent": "HyLeakAI-Render-Build",
    }
    request = urllib.request.Request(args.url, headers=headers)
    with urllib.request.urlopen(request) as response, archive.open("wb") as target:
        shutil.copyfileobj(response, target)
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(args.output)
    manifest = json.loads((args.output / "MANIFEST.sha256.json").read_text())
    failures = [
        entry["path"]
        for entry in manifest["files"]
        if not (args.output / entry["path"]).exists()
        or sha256(args.output / entry["path"]) != entry["sha256"]
    ]
    archive.unlink()
    if failures:
        raise SystemExit("Artifact verification failed: " + ", ".join(failures))
    print(f"Verified {len(manifest['files'])} inference artifacts.")


if __name__ == "__main__":
    main()
