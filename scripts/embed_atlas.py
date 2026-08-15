"""Regenerate the inline SITES array in app/web/index.html from the ranking CSV.

Stage 1 embeds its 1,000 points in the page rather than fetching them. That is
deliberate: the Storage Atlas is the first thing a visitor sees, and making it
wait on a Cloud Run cold start — or fail entirely when the API is down — would
be worse than the ~54 KB the array costs.

The consequence is that the page and outputs/site_suitability_ranking.csv can
drift apart. This script is the only supported way to close that gap:

    python scripts/embed_atlas.py            # rewrite the array
    python scripts/embed_atlas.py --check    # verify it is current, exit 1 if not

Run it after any re-scoring in src/site_suitability.py.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "outputs" / "site_suitability_ranking.csv"
HTML_PATH = ROOT / "app" / "web" / "index.html"

# Column order the frontend indexes by position. Changing this means changing
# every SITES[i][n] in index.html, so the names are asserted below against the
# CSV header rather than trusted.
COLUMNS = [
    ("sim_id", 0),
    ("capacity_norm", 6),
    ("seal_risk_norm", 6),
    ("heterogeneity_norm", 6),
    ("suitability_score", 2),
    ("rank", 0),
    ("poro_mean", 5),
    ("logk_mean", 4),
    ("caprock_margin_peak", 5),
]

# 6 decimals on the normalised criteria rather than the 4 used previously: the
# frontend recomputes scores from these under user-selected weights, and the
# result is checked for parity against the Python ranking. 4 decimals put that
# parity at the edge of the tolerance for no meaningful size saving.

ARRAY_RE = re.compile(r"(var SITES = )\[.*?\](;)", re.DOTALL)
TEST_IDS_RE = re.compile(r"(var TEST_IDS = )\[.*?\](;)", re.DOTALL)


def test_ids() -> list[int]:
    """Held-out simulation IDs — the only ones Stage 2 can run live inference on.

    Embedded rather than fetched from /v1/simulations so the ranking list can
    label availability with the API down, matching the decision to embed the
    atlas itself. The split is deterministic, so this cannot drift as long as
    it is regenerated from the same source the API uses.
    """
    sys.path.insert(0, str(ROOT))
    from src import config as C  # noqa: E402  (import here: needs ROOT on the path)

    return sorted(C.simulation_splits()["test"])


def fmt(value: str, places: int) -> str:
    if places == 0:
        return str(int(float(value)))
    text = f"{float(value):.{places}f}".rstrip("0").rstrip(".")
    return text if text not in ("", "-") else "0"


def build_array() -> tuple[str, int]:
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [name for name, _ in COLUMNS if name not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"{CSV_PATH.name} is missing column(s): {', '.join(missing)}")
        rows = list(reader)

    rows.sort(key=lambda r: int(r["rank"]))
    parts = ["[" + ",".join(fmt(row[name], places) for name, places in COLUMNS) + "]" for row in rows]
    return "[" + ",".join(parts) + "]", len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify the embedded array matches the CSV; do not write")
    args = parser.parse_args()

    array, n = build_array()
    html = HTML_PATH.read_text(encoding="utf-8")
    if not ARRAY_RE.search(html):
        raise SystemExit("could not find `var SITES = [...];` in index.html")
    if not TEST_IDS_RE.search(html):
        raise SystemExit("could not find `var TEST_IDS = [...];` in index.html")

    ids = test_ids()
    updated = ARRAY_RE.sub(lambda m: m.group(1) + array + m.group(2), html, count=1)
    updated = TEST_IDS_RE.sub(
        lambda m: m.group(1) + "[" + ",".join(str(i) for i in ids) + "]" + m.group(2),
        updated, count=1)

    if args.check:
        if updated == html:
            print(f"embedded atlas is current ({n} sites)")
            return 0
        print("embedded atlas is STALE - run: python scripts/embed_atlas.py", file=sys.stderr)
        return 1

    if updated == html:
        print(f"embedded atlas already current ({n} sites, {len(array):,} chars)")
        return 0

    HTML_PATH.write_text(updated, encoding="utf-8")
    print(f"embedded {n} sites, {len(array):,} chars, "
          f"columns: {', '.join(name for name, _ in COLUMNS)}")
    print(f"embedded {len(ids)} held-out test ids")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
