#!/usr/bin/env python3
"""ZUAEF-ASHARE-001 · 本地实时看板服务 (只读, 无交易语义)。

GET /          → docs/quant/dashboard.html (页面 JS 每 60s 轮询 /api/scan 实时刷新)
GET /api/scan  → 实时扫描 JSON (qt.gtimg.cn 批量报价 + 触发判定; ~3s, 确定性)

用法:
    python3 tools/quant_serve.py [--port 8787]
打开: http://127.0.0.1:8787/

Loopback-only; 只读巡检页, 不产生任何交易动作。冻结期有意的最小实现
(docs/quant/README.md §6): 本服务只是把既有确定性扫描工具实时暴露给看板,
不建 watcher/daemon 框架 —— 页面轮询 + 确定性扫描即足够。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = REPO_ROOT / "docs" / "quant" / "dashboard.html"
SCAN_CMD = ["uv", "run", "--group", "quant", "python", "tools/quant_live_scan.py"]


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
        if self.path in ("/", "/index.html"):
            try:
                body = DASHBOARD.read_bytes()
            except FileNotFoundError:
                self._send(
                    500,
                    b"docs/quant/dashboard.html not found; run render first",
                    "text/plain; charset=utf-8",
                )
                return
            self._send(200, body, "text/html; charset=utf-8")
            return
        if self.path == "/api/scan":
            try:
                r = subprocess.run(
                    SCAN_CMD,
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=60,
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
        f"ZUAEF-ASHARE-001 live dashboard → http://{args.host}:{args.port}  (Ctrl-C 停止)",
        file=sys.stderr,
    )
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
