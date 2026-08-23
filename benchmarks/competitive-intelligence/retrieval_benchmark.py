"""Retrieval benchmark — DISCOVERY / READ / KEY FACT measured separately.

Gate T005 (spec pack v0.2.0-final, RETRIEVAL_BENCHMARK_SPEC.md): before any
renderer work, the configured acquisition path must discover and read the
seeded official Riese & Müller surfaces and recover the literal key-fact
probes. A backend that returns URLs but fails key-fact recovery does not
pass.

Layers (never merged into one score):

  DISCOVERY  search finds the target official URL or an official equivalent
  READ       read_source-equivalent extraction yields useful body text
  KEY FACT   the extracted text contains the literal probe terms

Usage:

  uv run python benchmarks/competitive-intelligence/retrieval_benchmark.py \
    --cases benchmarks/competitive-intelligence/rm_cases.yaml \
    --backend brave \
    --results-dir benchmarks/competitive-intelligence/results

  # offline/deterministic harness proof:
  ... --backend fixture

Emit JSON + Markdown under the results dir.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins" / "zuaef-competitive-intelligence"))

from zuaef_competitive_intelligence import network
from zuaef_competitive_intelligence.search_backend import (
    BraveSearchBackend,
    FixtureSearchBackend,
    SearchBackend,
    SearchBackendError,
)

_HERE = Path(__file__).resolve().parent
_DEFAULT_CASES = _HERE / "rm_cases.yaml"
OFFICIAL_CLASSES = {"official_product_index", "official_product", "official_press"}

# Minimum pass contract (RETRIEVAL_BENCHMARK_SPEC §7):
#   discovery >= 80% of the official seed set
#   read      >= 90% of directly supplied public official URLs
#   key fact  >= 80% of cases
PASS_DISCOVERY = 0.80
PASS_READ = 0.90
PASS_KEY_FACT = 0.80


def _normalize_host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().rstrip(".")


def _official_equivalent(hit_url: str, case_target: str) -> bool:
    """A same-domain result sharing the first path segment is an official
    equivalent for discovery purposes (exact match always wins)."""
    hit, target = _normalize_host(hit_url), _normalize_host(case_target)
    if not hit or not target:
        return False
    if hit != target:
        return False
    hit_path = urlparse(hit_url).path
    target_path = urlparse(case_target).path
    return hit_path.split("/")[:3] == target_path.split("/")[:3]


def _discovery_hit(case: dict, hits: list) -> tuple[bool, int | None]:
    for index, hit in enumerate(hits):
        if hit.url == case["target_url"] or _official_equivalent(
            hit.url, case["target_url"]
        ):
            return True, index + 1
    return False, None


def _best_url(case: dict, hits: list) -> str | None:
    for hit in hits:
        if hit.url == case["target_url"]:
            return hit.url
    for hit in hits:
        if _official_equivalent(hit.url, case["target_url"]):
            return hit.url
    return None


def _probe_result(text: str, case: dict) -> dict:
    text_lower = text.lower()
    must_any = [p for p in case.get("must_contain_any") or [] if p]
    must_all = [p for p in case.get("must_contain_all") or [] if p]
    any_pass = not must_any or any(p.lower() in text_lower for p in must_any)
    all_pass = all(p.lower() in text_lower for p in must_all)
    return {
        "probe_terms": {"any": must_any, "all": must_all},
        "pass": bool(any_pass and all_pass),
        "found_any": [p for p in must_any if p.lower() in text_lower],
        "missing_any": [p for p in must_any if p.lower() not in text_lower],
        "missing_all": [p for p in must_all if p.lower() not in text_lower],
    }


def _fetch_and_extract(url: str, *, max_fetch_bytes: int, timeout: float) -> dict:
    """Bounded fetch + extraction through the plugin's production path."""
    start = time.monotonic()
    client = network.make_client(timeout_seconds=timeout)
    try:
        with client:
            document = network.fetch_document(
                url, client, max_bytes=max_fetch_bytes
            )
            title, text = network.extract_document(document)
    except network.NetworkError as exc:
        return {
            "fetch_status": "failure",
            "failure_reason": f"{exc.code}: {exc.message}",
            "elapsed_ms": int((time.monotonic() - start) * 1000),
        }
    return {
        "fetch_status": "success",
        "content_type": document.content_type,
        "body_chars": len(text),
        "title": title,
        "text": text[:200_000],
        "elapsed_ms": int((time.monotonic() - start) * 1000),
    }


def _fixture_data(case: dict) -> tuple[dict | None, dict]:
    """Fixture-mode fetch result: local HTML/PDF placeholders for the seed set.

    Returns ``(hit_metadata, fetch_and_probe_result)``. The fixture HTML
    contains the case target URL, the decision use and the probe terms, so
    READ/KEY FACT layers are exercised offline without faking search.
    """
    probes = (case.get("must_contain_any") or []) + (
        case.get("must_contain_all") or []
    )
    text = (
        f"{case['id']} {case['expected_source_class']} "
        f"{case['decision_use']} Probe terms: {' '.join(probes)}"
    )
    return (
        {"content_type": "text/html", "title": f"{case['id']} — fixture"},
        {
            "fetch_status": "success",
            "content_type": "text/html",
            "body_chars": len(text),
            "text": text,
            "elapsed_ms": 1,
        },
    )


def run_benchmark(
    *,
    cases: list[dict],
    backend: SearchBackend,
    backend_name: str,
    backend_has_dates: bool,
    backend_has_snippets: bool,
    remove: bool = False,
    max_fetch_bytes: int,
    timeout: float,
) -> dict:
    rows: list[dict] = []
    for case in cases:
        row: dict = {
            "id": case["id"],
            "target_url": case["target_url"],
            "expected_source_class": case["expected_source_class"],
            "decision_use": case["decision_use"],
        }
        hits: list = []
        for query in case["search_queries"]:
            try:
                query_hits = backend.search(query, limit=10)
            except SearchBackendError as exc:
                row["search_error"] = f"{exc.code}: {exc.message}"
                query_hits = []
            hits.extend(query_hits)
            found, rank = _discovery_hit(case, hits)
            if found:
                row["search_returned_target_or_equivalent"] = "yes"
                row["search_result_rank"] = rank
                break
        else:
            row["search_returned_target_or_equivalent"] = "no"
            row["search_result_rank"] = "unknown"
        snippets = [h.snippet for h in hits if h.snippet]
        dates = [h.published_or_indexed_date for h in hits if h.published_or_indexed_date]
        row["snippet_present"] = (
            "yes" if snippets else ("no" if hits else "unknown")
        )
        row["date_present"] = "yes" if dates else ("no" if hits else "unknown")

        # READ + KEY FACT: the seed's target URL is the contract (spec §7:
        # "directly supplied public official target URLs"). Fixture mode
        # stays offline with its local placeholder. Discovery is measured
        # separately above and never gates the read measurement.
        if backend_name == "fixture":
            best = _best_url(case, hits) or case["target_url"]
            _, fetch = _fixture_data(case)
        else:
            best = case["target_url"]
            fetch = _fetch_and_extract(
                best, max_fetch_bytes=max_fetch_bytes, timeout=timeout
            )
        if "fetch_status" not in row:
            row.update(fetch)
            if row.get("fetch_status") == "success":
                probes = _probe_result(row.get("text", ""), case)
                row["key_fact_probe"] = "pass" if probes["pass"] else "fail"
                row["probe_details"] = probes
            else:
                row["key_fact_probe"] = "not_measured"
        else:
            row["fetch_status"] = "not_attempted"
            row["key_fact_probe"] = "not_measured"

        rows.append(row)

    def _share(cond) -> float:
        total = len(rows)
        count = sum(1 for r in rows if cond(r))
        return count / total if total else 0.0

    def _official(cond) -> float:
        subset = [r for r in rows if r["expected_source_class"] in OFFICIAL_CLASSES]
        total = len(subset)
        count = sum(1 for r in subset if cond(r))
        return count / total if total else 0.0

    discovery_official = _official(
        lambda r: r["search_returned_target_or_equivalent"] == "yes"
    )
    read_share = _share(lambda r: r.get("fetch_status") == "success")
    key_share = _share(lambda r: r.get("key_fact_probe") == "pass")
    discovery_share = _share(
        lambda r: r["search_returned_target_or_equivalent"] == "yes"
    )

    verdict = {
        "discovery_official_share": round(discovery_official, 3),
        "discovery_all_share": round(discovery_share, 3),
        "read_share": round(read_share, 3),
        "key_fact_share": round(key_share, 3),
        "discovery_pass": discovery_official >= PASS_DISCOVERY,
        "read_pass": read_share >= PASS_READ,
        "key_fact_pass": key_share >= PASS_KEY_FACT,
    }
    verdict["overall_pass"] = (
        verdict["discovery_pass"]
        and verdict["read_pass"]
        and verdict["key_fact_pass"]
    )
    return {
        "benchmark": "retrieval-v1",
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "backend": backend_name,
        "backend_has_snippets": backend_has_snippets,
        "backend_has_dates": backend_has_dates,
        "thresholds": {
            "discovery_official_min": PASS_DISCOVERY,
            "read_min": PASS_READ,
            "key_fact_min": PASS_KEY_FACT,
        },
        "verdict": verdict,
        "cases": rows,
    }


def _markdown(result: dict) -> str:
    lines = [
        f"# Retrieval Benchmark — {result['backend']}",
        "",
        f"- run_at: {result['run_at']}",
        f"- backend: {result['backend']}",
        f"- verdict: {'PASS' if result['verdict']['overall_pass'] else 'FAIL'}",
        "",
        "## Aggregate",
        "",
        "| Layer | Share | Threshold | Pass |",
        "| --- | --- | --- | --- |",
    ]
    v = result["verdict"]
    lines.append(
        f"| DISCOVERY (official seed) | {v['discovery_official_share']:.0%} "
        f"| >= {result['thresholds']['discovery_official_min']:.0%} "
        f"| {'yes' if v['discovery_pass'] else 'no'} |"
    )
    lines.append(
        f"| READ | {v['read_share']:.0%} | >= {result['thresholds']['read_min']:.0%} "
        f"| {'yes' if v['read_pass'] else 'no'} |"
    )
    lines.append(
        f"| KEY FACT | {v['key_fact_share']:.0%} | >= {result['thresholds']['key_fact_min']:.0%} "
        f"| {'yes' if v['key_fact_pass'] else 'no'} |"
    )
    lines += ["", "## Per case", ""]
    lines.append(
        "| id | discovery | rank | snippet | date | fetch | type | chars | key fact |"
    )
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in result["cases"]:
        lines.append(
            f"| {row['id']} | {row['search_returned_target_or_equivalent']} "
            f"| {row['search_result_rank']} | {row.get('snippet_present', 'unknown')} "
            f"| {row.get('date_present', 'unknown')} | {row.get('fetch_status')} "
            f"| {row.get('content_type', '-')} | {row.get('body_chars', '-')} "
            f"| {row.get('key_fact_probe', 'not_measured')} |"
        )
    failures = [
        row
        for row in result["cases"]
        if row.get("fetch_status") == "failure"
        or row.get("key_fact_probe") == "fail"
    ]
    if failures:
        lines += ["", "## Failures", ""]
        for row in failures:
            lines.append(
                f"- {row['id']}: fetch={row.get('fetch_status')} "
                f"reason={row.get('failure_reason', '-')} "
                f"key={row.get('key_fact_probe')}"
            )
    return "\n".join(lines) + "\n"


def _load_fixture_hits() -> dict:
    path = _HERE / "rm_fixture_hits.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def main(argv: list[str] | None = None) -> int:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", default=str(_DEFAULT_CASES))
    parser.add_argument("--backend", choices=["brave", "fixture"], default="brave")
    parser.add_argument("--results-dir", default=str(_HERE / "results"))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-fetch-bytes", type=int, default=10_000_000)
    args = parser.parse_args(argv)

    cases = yaml.safe_load(Path(args.cases).read_text(encoding="utf-8"))["cases"]

    if args.backend == "fixture":
        fixture = (_load_fixture_hits() or {}).get("queries", {})
        if not fixture:
            print(
                "error: no benchmark fixtures at "
                f"{_HERE / 'rm_fixture_hits.yaml'}",
                file=sys.stderr,
            )
            return 64
        backend: SearchBackend = FixtureSearchBackend(fixture)
        backend_has_snippets = True
        backend_has_dates = True
    else:
        secret = BraveSearchBackend.secret_from_env()
        if not secret:
            print(
                "error: ZUAEF_BRAVE_SEARCH_API_KEY (or BRAVE_API_KEY) not set",
                file=sys.stderr,
            )
            return 64
        backend = BraveSearchBackend(api_key=secret)
        backend_has_snippets = True
        backend_has_dates = True

    result = run_benchmark(
        cases=cases,
        backend=backend,
        backend_name=args.backend,
        backend_has_dates=backend_has_dates,
        backend_has_snippets=backend_has_snippets,
        max_fetch_bytes=args.max_fetch_bytes,
        timeout=args.timeout,
    )
    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    json_path = results_dir / f"retrieval-benchmark-{stamp}.json"
    md_path = results_dir / f"retrieval-benchmark-{stamp}.md"
    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_path.write_text(_markdown(result), encoding="utf-8")
    # Stable "latest" pointers for downstream tooling.
    (results_dir / "latest.json").write_text(json_path.read_text(), encoding="utf-8")
    (results_dir / "latest.md").write_text(md_path.read_text(), encoding="utf-8")

    print(_markdown(result))
    verdict = result["verdict"]
    if verdict["overall_pass"]:
        print("RETRIEVAL BENCHMARK: PASS")
        return 0
    print("RETRIEVAL BENCHMARK: FAIL — diagnose the failed layer before renderer work", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())