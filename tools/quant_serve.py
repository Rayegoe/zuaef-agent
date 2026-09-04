#!/usr/bin/env python3
"""ZUAEF-ASHARE-001 · 本地看板服务 (只读, 无交易语义, loopback-only)。

GET / , /business , /index.html → docs/quant/business.html   (业务决策页, 默认)
GET /engineering               → docs/quant/dashboard.html   (工程/审计页)
GET /api/scan                  → 活跃候选宇宙实时扫描 JSON (确定性; quant_live_scan.py)
GET /api/watchlist             → legacy_watchlist 显式扫描 JSON (只扫用户自选名单)

用法:
    python3 tools/quant_serve.py [--port 8787]
打开: http://127.0.0.1:8787/            (业务页)
      http://127.0.0.1:8787/engineering (工程/审计页)

Loopback-only; 只读巡检, 不产生任何交易动作。冻结期有意的最小实现
(docs/quant/README.md §6): 页面轮询 + 确定性扫描即足够, 不建 watcher/daemon
框架。宇宙解析失败时 /api/* 返回错误 JSON (fail closed), 绝不静默返回空宇宙。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PAGES = {
    "business": REPO_ROOT / "docs" / "quant" / "business.html",
    "engineering": REPO_ROOT / "docs" / "quant" / "dashboard.html",
}
SCAN_CMD = ["uv", "run", "--group", "quant", "python", "tools/quant_live_scan.py"]
WATCHLIST_CMD = SCAN_CMD + ["--universe-file", "benchmarks/quant/gen1/legacy_watchlist.toml"]


def page_for_path(path: str) -> Path | None:
    """Route map (unit-tested): page paths -> html files; None for API/other."""
    if path in ("/", "/index.html", "/business"):
        return PAGES["business"]
    if path == "/engineering":
        return PAGES["engineering"]
    return None


def api_command_for_path(path: str) -> list[str] | None:
    if path == "/api/scan":
        return SCAN_CMD
    if path == "/api/watchlist":
        return WATCHLIST_CMD
    return None


ATTENTION_STATE = REPO_ROOT / "workspace/artifacts/quant/trading/state.json"


def attention_state() -> dict:
    """M1 monitor state for /api/attention — a file read, never a scan run:
    the fast loop owns scanning; the page only projects its artifacts."""
    try:
        return json.loads(ATTENTION_STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "UNKNOWN", "reason": "monitor has not run yet"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # keep access logs bounded
        sys.stderr.write(f"[serve] {format % args}\n")

    def _send(self, code: int, body: bytes, ctype: str, no_store: bool = False) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if no_store:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        page = page_for_path(self.path)
        if page is not None:
            try:
                body = page.read_bytes()
            except FileNotFoundError:
                self._send(
                    500,
                    f"{page.relative_to(REPO_ROOT)} not found; run the renderer first".encode(),
                    "text/plain; charset=utf-8",
                )
                return
            self._send(200, body, "text/html; charset=utf-8")
            return
        if self.path == "/api/attention":
            body = json.dumps(attention_state(), ensure_ascii=False, default=str).encode("utf-8")
            self._send(200, body, "application/json", no_store=True)
            return
        cmd = api_command_for_path(self.path)
        if cmd is not None:
            try:
                r = subprocess.run(
                    cmd,
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                self._send(
                    504,
                    json.dumps({"error": "scan timeout"}).encode(),
                    "application/json",
                )
                return
            if r.returncode != 0:
                self._send(
                    500,
                    json.dumps({"error": (r.stderr or r.stdout)[-500:]}).encode(),
                    "application/json",
                )
                return
            self._send(200, r.stdout.encode("utf-8"), "application/json", no_store=True)
            return
        self._send(404, b"not found", "text/plain")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(
        f"ZUAEF quant dashboards → business http://{args.host}:{args.port}/  "
        f"engineering http://{args.host}:{args.port}/engineering  (Ctrl-C 停止)",
        file=sys.stderr,
    )
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
