"""Create the minimal, reviewable artifact bundle for the public API.

The bundle intentionally excludes raw simulator states and LMDB data. It is
ignored by Git and must be uploaded to approved object storage or a model
registry before a Render deployment is configured to retrieve it.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = (
    (ROOT / "data" / "constants.npy", "data/constants.npy"),
    (ROOT / "data" / "stats.json", "data/stats.json"),
    (ROOT / "checkpoints" / "unet_small_best.pt", "checkpoints/unet_small_best.pt"),
    (ROOT / "outputs" / "xgb_classifier.ubj", "outputs/xgb_classifier.ubj"),
    (ROOT / "outputs" / "shap_features.json", "outputs/shap_features.json"),
    (ROOT / "outputs" / "xgb_results.json", "outputs/xgb_results.json"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "api_artifacts")
    args = parser.parse_args()
    missing = [str(source) for source, _ in ARTIFACTS if not source.exists()]
    if missing:
        raise SystemExit("Missing required artifacts:\n" + "\n".join(missing))

    manifest = []
    for source, relative in ARTIFACTS:
        target = args.output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        manifest.append({"path": relative, "bytes": target.stat().st_size, "sha256": sha256(target)})
    (args.output / "MANIFEST.sha256.json").write_text(
        __import__("json").dumps({"files": manifest}, indent=2) + "\n"
    )
    print(f"Created {args.output} with {len(manifest)} inference artifacts.")


if __name__ == "__main__":
    main()
