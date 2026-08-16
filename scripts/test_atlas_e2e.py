"""Browser E2E test for the Stage 1 Storage Atlas.

Serves app/web, drives index.html inside a same-origin iframe, and asserts the
things a DOM snapshot alone cannot: that reweighting reshuffles the ranking,
that selection propagates to Stage 2, that filters and sorting work, and that
the 3D module actually initialised rather than quietly falling back to 2D.

    python scripts/test_atlas_e2e.py           # headless, exit 1 on any failure
    python scripts/test_atlas_e2e.py --show    # print every assertion

The harness lives in tests/ and is copied into app/web only while the test
runs: it must be same-origin to reach the iframe's document, but it must not
ship in the container image.
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
import threading
import http.server
import functools
import socketserver
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "app" / "web"
HARNESS = ROOT / "tests" / "atlas_e2e.html"
PORT = 8899

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_chrome() -> str:
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    raise SystemExit("no Chrome/Edge binary found; set one in CHROME_CANDIDATES")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):  # noqa: D102 - silence per-request logging
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show", action="store_true", help="print every assertion, not just failures")
    args = parser.parse_args()

    chrome = find_chrome()
    served = WEB / "__e2e.html"
    shutil.copy(HARNESS, served)

    handler = functools.partial(QuietHandler, directory=str(WEB))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), handler) as httpd:
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            proc = subprocess.run(
                [chrome, "--headless=new", "--disable-gpu", "--use-gl=swiftshader",
                 "--enable-unsafe-swiftshader", "--no-sandbox",
                 # Virtual time so the harness's own sleeps do not cost real seconds.
                 # Without it the suite takes ~4s of wall clock for no benefit.
                 "--virtual-time-budget=25000", "--dump-dom",
                 f"http://127.0.0.1:{PORT}/__e2e.html"],
                capture_output=True, text=True, timeout=180)
        finally:
            httpd.shutdown()
            served.unlink(missing_ok=True)

    match = re.search(r'<pre id="out">(.*?)</pre>', proc.stdout, re.DOTALL)
    if not match:
        print("could not read test output from the page", file=sys.stderr)
        print(proc.stdout[:800], file=sys.stderr)
        return 1

    lines = [ln for ln in html.unescape(match.group(1)).splitlines() if ln.strip()]
    failures = [ln for ln in lines if ln.startswith("FAIL")]

    if args.show or failures:
        for line in lines:
            print(line)
    if not lines:
        print("the harness produced no assertions", file=sys.stderr)
        return 1
    print(f"\n{len(lines) - len(failures)}/{len(lines)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
