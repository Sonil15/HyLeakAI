"""Resumable parallel downloader for the Mao et al. UHS dataset.

Zenodo serves this file at roughly 2-3 MB/s per connection but honours HTTP
range requests (verified: GET with `Range:` returns 206 PARTIAL_CONTENT with a
content-range header), so several concurrent connections cut the wall time
substantially.

Progress is persisted per chunk, so an interrupted run resumes rather than
restarting a 12 GB transfer.

Usage:
    python -m src.data.download
    python -m src.data.download --connections 12
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

import requests

URL = "https://zenodo.org/records/14029514/files/data.mdb?download=1"
EXPECTED_BYTES = 12_380_934_144
EXPECTED_MD5 = "6bc841f02ad3f40c9a8ef8ad187edf43"  # from the Zenodo record

CHUNK_MB = 64
STREAM_BLOCK = 1 << 20  # 1 MiB socket reads


def _chunk_bounds(total: int, chunk_size: int) -> list[tuple[int, int]]:
    """Inclusive [start, end] byte ranges covering the whole file."""
    return [
        (start, min(start + chunk_size, total) - 1)
        for start in range(0, total, chunk_size)
    ]


class ParallelDownloader:
    def __init__(self, url: str, dest: Path, total: int, connections: int, chunk_mb: int):
        self.url = url
        self.dest = dest
        self.total = total
        self.connections = connections
        self.chunks = _chunk_bounds(total, chunk_mb * 1024 * 1024)
        self.state_path = dest.with_suffix(dest.suffix + ".progress.json")
        self.done: set[int] = set()
        self.lock = threading.Lock()
        self.downloaded = 0
        self.errors: list[str] = []

    # -- state ------------------------------------------------------------

    def load_state(self) -> None:
        if not self.state_path.exists():
            return
        try:
            state = json.loads(self.state_path.read_text())
        except json.JSONDecodeError:
            return
        # Invalidate the resume state if the chunk layout changed.
        if state.get("total") != self.total or state.get("n_chunks") != len(self.chunks):
            return
        self.done = set(state.get("done", []))
        self.downloaded = sum(
            self.chunks[i][1] - self.chunks[i][0] + 1 for i in self.done
        )

    def save_state(self) -> None:
        self.state_path.write_text(
            json.dumps(
                {
                    "total": self.total,
                    "n_chunks": len(self.chunks),
                    "done": sorted(self.done),
                }
            )
        )

    def adopt_contiguous_prefix(self) -> None:
        """Treat an existing contiguous prefix (e.g. from an earlier plain
        `curl -o`) as already-downloaded chunks, so we don't refetch it."""
        if self.done or not self.dest.exists():
            return
        have = self.dest.stat().st_size
        if have < self.chunks[0][1] + 1:
            return
        for i, (start, end) in enumerate(self.chunks):
            if end < have:
                self.done.add(i)
            else:
                break
        if self.done:
            self.downloaded = sum(
                self.chunks[i][1] - self.chunks[i][0] + 1 for i in self.done
            )
            print(
                f"Adopting {len(self.done)} complete chunks "
                f"({self.downloaded / 2**30:.2f} GiB) from the existing file."
            )

    # -- transfer ---------------------------------------------------------

    def _allocate(self) -> None:
        """Preallocate so threads can seek and write to disjoint offsets."""
        existing = self.dest.stat().st_size if self.dest.exists() else 0
        mode = "r+b" if existing else "wb"
        with open(self.dest, mode) as fh:
            fh.truncate(self.total)

    def _worker(self, queue: list[int], session: requests.Session) -> None:
        while True:
            with self.lock:
                if not queue:
                    return
                idx = queue.pop()
            start, end = self.chunks[idx]
            written = 0
            try:
                resp = session.get(
                    self.url,
                    headers={"Range": f"bytes={start}-{end}"},
                    stream=True,
                    timeout=(15, 120),
                )
                if resp.status_code != 206:
                    raise RuntimeError(
                        f"expected 206 for chunk {idx}, got {resp.status_code}"
                    )
                written = 0
                with open(self.dest, "r+b") as fh:
                    fh.seek(start)
                    for block in resp.iter_content(STREAM_BLOCK):
                        if not block:
                            continue
                        fh.write(block)
                        written += len(block)
                        with self.lock:
                            self.downloaded += len(block)
                expected = end - start + 1
                if written != expected:
                    raise RuntimeError(
                        f"chunk {idx} short: {written} of {expected} bytes"
                    )
            except Exception as exc:
                # Roll back this attempt's byte count and requeue the chunk.
                with self.lock:
                    self.downloaded -= written
                    self.errors.append(f"chunk {idx}: {exc}")
                    queue.append(idx)
                time.sleep(2)
                continue

            with self.lock:
                self.done.add(idx)
                if len(self.done) % 8 == 0:
                    self.save_state()

    def run(self) -> None:
        self.dest.parent.mkdir(parents=True, exist_ok=True)
        self.load_state()
        self.adopt_contiguous_prefix()
        self._allocate()

        todo = [i for i in range(len(self.chunks)) if i not in self.done]
        if not todo:
            print("All chunks already present.")
            return
        todo.reverse()  # pop() from the end preserves ascending order

        print(
            f"{len(todo)} of {len(self.chunks)} chunks remaining "
            f"({self.total / 2**30:.2f} GiB total) over {self.connections} connections."
        )

        start_bytes, t0 = self.downloaded, time.monotonic()
        threads = []
        for _ in range(self.connections):
            session = requests.Session()
            th = threading.Thread(target=self._worker, args=(todo, session), daemon=True)
            th.start()
            threads.append(th)

        while any(t.is_alive() for t in threads):
            time.sleep(5)
            elapsed = time.monotonic() - t0
            rate = (self.downloaded - start_bytes) / max(elapsed, 1e-9)
            remaining = self.total - self.downloaded
            eta = remaining / rate if rate > 0 else float("inf")
            print(
                f"  {self.downloaded / 2**30:6.2f} / {self.total / 2**30:.2f} GiB  "
                f"({100 * self.downloaded / self.total:5.1f}%)  "
                f"{rate / 2**20:5.1f} MiB/s  ETA {eta / 60:5.1f} min",
                flush=True,
            )

        for t in threads:
            t.join()
        self.save_state()


def verify(dest: Path, total: int, md5: str | None) -> bool:
    size = dest.stat().st_size
    if size != total:
        print(f"FAIL size: {size} != {total}")
        return False
    print(f"OK size: {size} bytes")
    if md5:
        import hashlib

        h = hashlib.md5()
        with open(dest, "rb") as fh:
            for block in iter(lambda: fh.read(8 << 20), b""):
                h.update(block)
        digest = h.hexdigest()
        if digest != md5:
            print(f"FAIL md5: {digest} != {md5}")
            return False
        print(f"OK md5: {digest}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dest", type=Path, default=Path("data/data.mdb"))
    ap.add_argument("--connections", type=int, default=8)
    ap.add_argument("--chunk-mb", type=int, default=CHUNK_MB)
    ap.add_argument("--verify-only", action="store_true")
    ap.add_argument("--skip-md5", action="store_true")
    args = ap.parse_args()

    if not args.verify_only:
        dl = ParallelDownloader(
            URL, args.dest, EXPECTED_BYTES, args.connections, args.chunk_mb
        )
        dl.run()
        if dl.errors:
            print(f"\n{len(dl.errors)} transient error(s) occurred and were retried:")
            for e in dl.errors[-5:]:
                print("  ", e)

    print("\nVerifying...")
    ok = verify(args.dest, EXPECTED_BYTES, None if args.skip_md5 else EXPECTED_MD5)
    if ok:
        progress = args.dest.with_suffix(args.dest.suffix + ".progress.json")
        progress.unlink(missing_ok=True)
        print("\nDownload complete and verified.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
