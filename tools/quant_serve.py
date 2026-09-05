#!/usr/bin/env python3
"""ZUAEF-ASHARE-001 · 本地看板服务 (loopback-only)。

GET / , /business , /index.html → docs/quant/business.html   (业务决策页, 默认)
GET /engineering               → docs/quant/dashboard.html   (工程/审计页)
GET /api/scan                  → 活跃候选宇宙实时扫描 JSON (确定性; quant_live_scan.py)
GET /api/watchlist             → legacy_watchlist 显式扫描 JSON (只扫用户自选名单)
GET /api/attention             → monitor state.json 投影 (兼容保留)
GET /api/quant/now             → NOW: durable trading facts 有界投影 (now_snapshot)

POST /api/quant/ack-buy        → 记录用户已完成/纸面买入 (canonical ack-buy)
POST /api/quant/ack-sell       → 记录用户全仓平仓 (canonical ack-sell)
POST /api/quant/skip           → 记录用户 SKIP 决定 (canonical skip)

写接口是 canonical trading host 操作 (quant_trading_monitor.py CLI) 的薄
HTTP adapter，不做任何 JSON 直写；且强制 loopback-only —— --host 非本机
回环地址时 POST 一律 403 (无账号系统，Phase 1 不对 LAN 暴露写接口)。

用法:
    python3 tools/quant_serve.py [--port 8787]
打开: http://127.0.0.1:8787/            (业务页)
      http://127.0.0.1:8787/engineering (工程/审计页)

冻结期有意的最小实现 (docs/quant/README.md §6): 页面轮询 + 确定性扫描即
足够, 不建 watcher/daemon 框架。宇宙解析失败时 /api/* 返回错误 JSON
(fail closed), 绝不静默返回空宇宙。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import quant_render_business_dashboard as biz

REPO_ROOT = Path(__file__).resolve().parent.parent
PAGES = {
    "business": REPO_ROOT / "docs" / "quant" / "business.html",
    "engineering": REPO_ROOT / "docs" / "quant" / "dashboard.html",
}
SCAN_CMD = ["uv", "run", "--group", "quant", "python", "tools/quant_live_scan.py"]
WATCHLIST_CMD = SCAN_CMD + ["--universe-file", "benchmarks/quant/gen1/legacy_watchlist.toml"]
MONITOR_CMD = ["uv", "run", "--group", "quant", "python", "tools/quant_trading_monitor.py"]
TRADING_STATE_DIR = "workspace/artifacts/quant/trading"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
MAX_BODY_BYTES = 4096


def writes_enabled_for_host(host: str) -> bool:
    """Trade-recording writes stay loopback-only: no accounts in Phase 1,
    so an unauthenticated LAN POST must never reach the ack endpoints."""
    return host in LOOPBACK_HOSTS


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


def now_state() -> dict:
    """NOW projection — the same durable-facts builder the static page
    embeds; reads artifacts, never recomputes the market."""
    return biz.now_snapshot()


ACK_KINDS = ("ack-buy", "ack-sell", "skip")


def ack_command_for(kind: str, payload: dict) -> list[str]:
    """Validate one human-action payload and build the canonical monitor CLI
    argv. Pure + unit-tested; the server never writes trading JSON itself.

    buy/sell require symbol/shares/price/venue/executed_at; skip requires
    symbol/price/executed_at (note optional). Full-close and venue-match
    rules are enforced by the monitor host op, not duplicated here.
    """
    if kind not in ACK_KINDS:
        raise ValueError(f"unknown ack kind: {kind}")
    if not isinstance(payload, dict):
        raise TypeError("body must be a JSON object")
    symbol = str(payload.get("symbol") or "").strip().upper()
    if not symbol:
        raise ValueError("symbol is required")
    argv = MONITOR_CMD + ["--state-dir", TRADING_STATE_DIR, kind, "--symbol", symbol]
    executed_at = str(payload.get("executed_at") or "").strip()
    if not executed_at:
        raise ValueError("executed_at is required (the human fact's own time)")
    if kind == "skip":
        price = payload.get("price")
        if not isinstance(price, (int, float)) or price <= 0:
            raise ValueError("price must be a positive number")
        argv += ["--price", repr(float(price)), "--time", executed_at]
        note = str(payload.get("note") or "").strip()
        if note:
            argv += ["--note", note]
        return argv
    venue = str(payload.get("venue") or "").strip()
    if venue not in ("paper", "real"):
        raise ValueError("venue must be 'paper' or 'real'")
    shares = payload.get("shares")
    if not isinstance(shares, int) or isinstance(shares, bool) or shares <= 0:
        raise ValueError("shares must be a positive integer")
    price = payload.get("price")
    if not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 0:
        raise ValueError("price must be a positive number")
    argv += [
        "--price", repr(float(price)),
        "--shares", str(shares),
        "--venue", venue,
        "--time", executed_at,
    ]
    note = str(payload.get("note") or "").strip()
    if note:
        argv += ["--note", note]
    return argv


class Handler(BaseHTTPRequestHandler):
    # set by main(): POST endpoints answer 403 when bound to a non-loopback host
    writes_enabled: bool = True

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

    def _send_json(self, code: int, obj: dict, no_store: bool = True) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"),
                   "application/json", no_store=no_store)

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
            self._send_json(200, attention_state())
            return
        if self.path == "/api/quant/now":
            self._send_json(200, now_state())
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

    def do_POST(self) -> None:
        kind = self.path.rsplit("/", 1)[-1] if self.path.startswith("/api/quant/") else ""
        if kind not in ACK_KINDS:
            self._send_json(404, {"error": "not found"})
            return
        if not self.writes_enabled:
            self._send_json(403, {"error": "trade writes are loopback-only; rebind --host to 127.0.0.1"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length <= 0 or length > MAX_BODY_BYTES:
            self._send_json(400, {"error": f"Content-Length must be 1..{MAX_BODY_BYTES}"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._send_json(400, {"error": "body is not valid JSON"})
            return
        try:
            cmd = ack_command_for(kind, payload)
        except (ValueError, TypeError) as exc:
            self._send_json(400, {"error": str(exc)})
            return
        try:
            r = subprocess.run(
                cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120, check=False,
            )
        except subprocess.TimeoutExpired:
            self._send_json(504, {"error": "ack timeout"})
            return
        if r.returncode != 0:
            # canonical host rejection (missing position / full-close / venue
            # rules) surfaces verbatim as 400 — the API never overrides it
            try:
                err = json.loads(r.stderr.strip() or r.stdout.strip())
            except ValueError:
                err = {"error": (r.stderr or r.stdout)[-500:]}
            self._send_json(400, err)
            return
        self._send_json(200, json.loads(r.stdout.strip() or "{}"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    Handler.writes_enabled = writes_enabled_for_host(args.host)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    writes = "enabled" if Handler.writes_enabled else "DISABLED (non-loopback host)"
    print(
        f"ZUAEF quant dashboards → business http://{args.host}:{args.port}/  "
        f"engineering http://{args.host}:{args.port}/engineering  "
        f"(trade writes {writes}; Ctrl-C 停止)",
        file=sys.stderr,
    )
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
