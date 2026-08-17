#!/usr/bin/env python3
"""Fetch the four public sources into data/raw/ (gitignored, never committed).

Repository policy: only bounded excerpts, record ids, licenses and hashes are
committed (benchmarks/editorial-learning/tasks/ + provenance/). Complete
datasets live here and are rebuilt on demand.

Network notes (verified 2026-08-17 from this host):
  - huggingface.co direct is unreachable; hf-mirror.com works.
  - raw.githubusercontent.com is unreachable; api.github.com contents API works.
  - TU Darmstadt DataLib breaks long transfers; resume with -C - and verify
    against the bitstream checkSum (MD5).

--reuse DIR copies an existing raw/ tree (e.g. the z-workspace build) after
verifying hashes, avoiding a second ~380MB download.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
REPO = BENCH.parents[1]
RAW = REPO / "data" / "raw"

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}

TETRA_FILES = [
    "P01-1044-A", "P01-1044-B", "P03-1006-A", "P03-1006-B",
    "P06-1005-A", "P06-1005-B", "P15-4020-A", "P15-4020-B",
    "P16-1061-A", "P16-1061-B", "W12-4514-A", "W12-4514-B",
    "W13-4603-A", "W13-4603-B", "W18-1705-A", "W18-1705-B",
    "W18-3410-A", "W18-3410-B",
]

WP_SHA256 = "fd9c8faf85b7f4ae4b48f938c9fd608e5ed2011f726789130b37c1588f2ab6e0"
RE3_MD5 = "60e128d2d02a72461199f0cacc436bbb"
RE3_BITSTREAM = "https://tudatalib.ulb.tu-darmstadt.de/server/api/core/bitstreams/d3cba11b-8c2d-406a-b380-21dc8b24344c/content"


def fetch(url: str, dest: Path, *, resume: bool = True) -> None:
    cmd = ["curl", "-sL", "--max-time", "280", "-A", UA["User-Agent"], url, "-o", str(dest)]
    if resume and dest.exists():
        cmd.insert(2, "-C")
        cmd.insert(3, "-")
    subprocess.run(cmd, check=False)


def fetch_retry(url: str, dest: Path, attempts: int = 6) -> None:
    for _ in range(attempts):
        fetch(url, dest)
        # a complete download ends with curl exit 0 AND (for zips) a valid EOCD
        if dest.exists() and (dest.suffix != ".zip" or _zip_ok(dest)):
            return
    raise SystemExit(f"download failed after {attempts} attempts: {url}")


def _zip_ok(path: Path) -> bool:
    data = path.read_bytes()
    return b"PK\x05\x06" in data[-22:]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def fetch_all() -> None:
    RAW.mkdir(parents=True, exist_ok=True)

    # 1) WritingPreferenceBench Chinese (via mirror; HF direct unreachable)
    wp = RAW / "WP_bench_chinese.json"
    if not (wp.exists() and sha256(wp) == WP_SHA256):
        fetch_retry(
            "https://hf-mirror.com/datasets/m-a-p/Writing-Preference-Bench/resolve/main/WP_bench_chinese.json",
            wp,
        )
        assert sha256(wp) == WP_SHA256, "WP_bench sha256 mismatch"
    print("wpbench ok", sha256(wp)[:12])

    # 2) IteraTeR
    it = RAW / "IteraTeR.zip"
    if not it.exists():
        fetch_retry("https://github.com/vipulraheja/iterater/raw/main/dataset/IteraTeR.zip", it)
    if not (RAW / "iterater" / "IteraTeR" / "human_doc_level").is_dir():
        subprocess.run(["unzip", "-q", "-o", str(it), "-d", str(RAW / "iterater")], check=True)
    print("iterater ok")

    # 3) TETRA (via GitHub contents API; raw.githubusercontent unreachable)
    tetra = RAW / "tetra"
    tetra.mkdir(parents=True, exist_ok=True)
    for name in TETRA_FILES:
        dest = tetra / f"{name}.xml"
        if dest.exists() and dest.stat().st_size > 0:
            continue
        req = urllib.request.Request(
            f"https://api.github.com/repos/chemicaltree/tetra/contents/original/{name}.xml",
            headers={**UA, "Accept": "application/vnd.github.raw+json"},
        )
        dest.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    print("tetra ok", len(list(tetra.glob('*.xml'))), "files")

    # 4) Re3-Sci (DataLib; resume + MD5 verify)
    re3 = RAW / "re3-sci.zip"
    if not (re3.exists() and md5(re3) == RE3_MD5 and _zip_ok(re3)):
        fetch_retry(RE3_BITSTREAM, re3)
        assert md5(re3) == RE3_MD5, "Re3-Sci md5 mismatch vs DataLib checkSum"
    if not (RAW / "re3" / "Re3-Sci_v1").is_dir():
        subprocess.run(["unzip", "-q", "-o", str(re3), "-d", str(RAW / "re3")], check=True)
    print("re3 ok", md5(re3))


def reuse(other_raw: Path) -> None:
    """Copy an existing verified raw tree instead of re-downloading."""
    other = Path(other_raw).expanduser().resolve()
    expect = {
        "WP_bench_chinese.json": lambda p: sha256(p) == WP_SHA256,
        "IteraTeR.zip": lambda p: p.is_file(),
        "re3-sci.zip": lambda p: md5(p) == RE3_MD5,
        "tetra": lambda p: p.is_dir() and len(list(p.glob("*.xml"))) >= len(TETRA_FILES),
        "iterater": lambda p: p.is_dir(),
        "re3": lambda p: p.is_dir(),
    }
    for name, check in expect.items():
        src = other / name
        if not check(src):
            raise SystemExit(f"reuse source missing or invalid: {src}")
    RAW.mkdir(parents=True, exist_ok=True)
    for name in expect:
        src = other / name
        dst = RAW / name
        if dst.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    print("reused from", other)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reuse", metavar="DIR", help="reuse an existing raw/ tree instead of downloading")
    args = ap.parse_args()
    if args.reuse:
        reuse(args.reuse)
    fetch_all()  # verifies everything present even after reuse


if __name__ == "__main__":
    sys.exit(main())
