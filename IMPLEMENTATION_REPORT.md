# ZUAEF Artifacts Native Capabilities v0.1 — Implementation Report

Status: **v0.1 complete** (P0–P8 executed and verified; final gate results in §9).
Authority: `zuaef-artifacts-native-capabilities-spec-v0.1/` pack + repository
`AGENTS.md`. All facts below were verified against the local working tree.

## 1. What shipped

- One production plugin `plugins/zuaef-artifacts/` exposing four native
  PydanticAI **capabilities** (DOCX, PDF, Slides, Spreadsheet), each with a
  declarative business-semantic description, its own guidance, its own toolset
  and capability-level deferred loading.
- One pilot profile `profiles/general-knowledge-worker-artifacts.toml` =
  current General Knowledge Worker semantics + the artifacts plugin
  (`allow_capabilities = true`, tool search on, shell off).
- Generic Feishu terminal artifact delivery in the Gateway
  (`ZUAEF_GATEWAY_AUTO_ARTIFACTS`, default **false**), implemented as one
  shared receipt-artifact send helper reused by the manual `/artifacts`
  recovery command.
- No kernel change: `core.py`, `runtime.py`, `composition.py` have **zero**
  functional diff (see §11).

## 2. P0 Baseline

### 2.1 Environment

- Python: 3.13.14 (repo venv), `requires-python >= 3.11`.
- pydantic-ai: 2.40.0 (pinned). pydantic-ai-harness: 0.29.0.
- Host arch: x86_64 (dev). ARM64/OrangePi is a real target (see §10).

### 2.2 Kernel seams verified (no changes needed)

- `src/zuaef_agent/plugin_api.py`: `PluginBundle(toolsets, skill_dirs, capabilities)`;
  capabilities are denied unless the profile sets `allow_capabilities = true`
  (enforced in `composition.py::_check_capability_policy`).
- `src/zuaef_agent/composition.py`: plugin capabilities flow into
  `build_agent(..., extra_capabilities=...)` (`build_agent_from_snapshot`).
  `core.py::build_agent` accepts `extra_capabilities` — the seam exists.
- Artifacts written under `workspace/artifacts/**` are automatically detected
  at settlement by the host's pre/post byte snapshot (`integrity.snapshot_artifacts`
  + `runtime._changed_artifact_facts`) and recorded as receipt `artifact_facts` —
  the plugin needs no extra registration to become delivery-eligible.
- Generic FileSystem protection: `artifacts/*` is write-protected for generic
  model file tools (core.py `FILESYSTEM_PROTECTED_PATTERNS`), so artifact writes
  belong in dedicated domain tools — exactly what this plugin adds.

### 2.3 Capability API decision

PydanticAI 2.40.0 has the public declarative `pydantic_ai.capabilities.Capability`
helper with `instructions / toolsets / tools / id / description / defer_loading`.

**Capability-level deferred loading IS supported and is used**: when any
capability has `defer_loading=True`, the Agent installs the
`DeferredCapabilityLoader` (byte-stable deferred-capability catalog in
instructions + a `load_capability` tool that coexists with ToolSearch). The
"cannot reveal tools mid-session" limitation applies only to Realtime sessions,
not normal runs. Verified by direct probe and by live runs (§8).

### 2.4 Tool-return multimodal support

The pinned stack supports multimodal tool returns
(`ToolReturn(return_value=..., content=[BinaryContent(...)])`). The active model
lane is `deepseek/deepseek-v4-flash-0731` (OpenAI-compat chat), not verified
image-capable. **Decision: v0.1 ships no model-visible image preview tools**;
QA = structure QA + render QA only, and this report does not claim visual
parity.

### 2.5 OAI reference material (license boundary)

- The local reference directory is `oai-skills/` (the master prompt says `oai/`;
  actual tree name recorded here). Git state: **untracked, not git-ignored** —
  left untouched, never committed by this work.
- Four skill roots: `oai-skills/skills/{docx,pdfs,slides,spreadsheets}`, each
  with an adjacent `LICENSE.txt` (OpenAI proprietary terms; text not reproduced
  here).
- Practical consequence: reference-only; **no OAI source, prompts, helper code,
  templates or assets were copied**; production runtime has no dependency on
  the directory (see §11) and no `/home/oai/`-style path assumptions.

### 2.6 System / dependency probes (dev host)

| Dependency | Status |
|---|---|
| LibreOffice | 26.2.5.2 via snap; PATH name is `libreoffice` (`soffice` not on PATH) |
| Node / npm | v22.23.1 / 10.9.8 (not provisioned on OrangePi today) |
| poppler-utils | 26.01.0 (`pdftoppm`, `pdftocairo`) |
| pypdf | 6.16.1 |
| openpyxl | 3.1.5 |
| python-docx | 1.2.0 |
| python-pptx | 1.0.2 |
| Pillow | 12.3.0 |
| pymupdf | present transitively — **not used** (AGPL; avoided) |

### 2.7 Implementation choices (P0 pass criteria)

1. **Capability API**: declarative `Capability`, one per format, all with
   `defer_loading=True`, business-semantic `id` + `description`.
2. **Slides backend**: `python-pptx` (single primary backend): acceptance
   requires bounded **revision by slide index** without rebuilding, which
   PptxGenJS cannot do (create-only); pure Python behaves identically on
   x86_64 and ARM64; and it is already the .pptx reading engine (zero new
   dependency class).
3. **PDF stack**: `pypdf` for page ops (merge/select/rotate/inspect);
   create-from-content route = structured spec → DOCX → bounded LibreOffice
   conversion; render QA via `pdftoppm`. Missing system tools degrade render QA
   to structure QA with explicit warnings, never fabricated success.
4. **Spreadsheet engine**: `openpyxl` only; LibreOffice headless for
   recalculation/render QA when installed; otherwise formulas are preserved and
   the limitation is reported.
5. **QA route**: create/revise tools run the full mechanical lifecycle inside
   one tool call (validate → build → reopen/inspect → render/convert where
   supported → format-local checks → `ArtifactResult`). No model-visible
   preview tools.
6. **Feishu auto-delivery route**: gateway-local setting
   `ZUAEF_GATEWAY_AUTO_ARTIFACTS` (default false) → `GatewayConfig.auto_artifacts`
   → `GatewayService(auto_artifacts=...)`; the manual `/artifacts` send loop and
   automatic settlement delivery both use one generic
   `_send_receipt_artifacts(session, receipt)` helper. No format policy in
   Gateway.

### 2.8 Test baseline before edits

`tests/test_knowledge_worker_plugin.py`, `test_knowledge_worker_documents.py`,
`test_gateway_service.py`, `test_gateway_feishu.py`, `test_manifest_integrity.py`,
`test_gateway_architecture.py` → **157 passed**.

## 3. Files changed

Modified (tracked):

| File | Change |
|---|---|
| `pyproject.toml` | add `zuaef-artifacts` dependency + uv workspace source; ruff exclude note |
| `uv.lock` | workspace member `zuaef-artifacts` (1 new package) |
| `.env.example` | documents `ZUAEF_GATEWAY_AUTO_ARTIFACTS`, `ZUAEF_ARTIFACTS_WORK_DIR` |
| `src/zuaef_agent/gateway/runner.py` | `GatewayConfig.auto_artifacts` from env (default false) |
| `src/zuaef_agent/gateway/service.py` | `_send_receipt_artifacts` (shared), `_auto_deliver_artifacts` (settlement hook), manual command reuses helper |
| `BUILD_MANIFEST.json` | surgical entries for every new/changed delivery file |

Added:

- `plugins/zuaef-artifacts/` — `pyproject.toml`, `plugin.py`, `contracts.py`,
  `paths.py`, `process.py`, `qa.py`, `guidance.py`,
  `guidance/{docx,pdf,slides,spreadsheet}.md`,
  `capabilities/{__init__,docx,pdf,slides,spreadsheet}.py`,
  `engines/{__init__,errors,docx_engine,pdf_engine,slides_engine,spreadsheet_engine}.py`.
- `profiles/general-knowledge-worker-artifacts.toml`.
- `tests/test_artifacts_plugin.py`, `tests/test_artifacts_paths.py`,
  `tests/test_artifacts_docx_pdf.py`, `tests/test_artifacts_slides_spreadsheet.py`,
  `tests/test_artifacts_routing.py`, `tests/test_gateway_auto_artifacts.py`.
- `IMPLEMENTATION_REPORT.md` (this file).

## 4. Dependencies added

Python (declared by `plugins/zuaef-artifacts/pyproject.toml`, all already inside
the repository dependency closure — `uv.lock` gained only the workspace package):
`python-docx>=1.1`, `pypdf>=5`, `openpyxl>=3.1`, `python-pptx>=1.0`.

System (optional, never installed silently): LibreOffice headless (conversion,
recalculation, office render QA) and poppler-utils (`pdftoppm`, PDF render QA).
Both degrade explicitly when absent.

## 5. Capability surface (v0.1)

| Capability id | Tools | Supported operations |
|---|---|---|
| `docx-artifacts` | `create_docx`, `revise_docx`, `inspect_docx` | declarative document spec (headings, paragraphs, bullets, tables, images, page breaks), bounded revisions (text replace, cell update, block append), structure inspection, structure+render QA, DOCX→PDF route |
| `pdf-artifacts` | `create_pdf`, `convert_to_pdf`, `merge_pdf`, `edit_pdf`, `inspect_pdf` | create from structured content, freeze DOCX/PPTX/XLSX into PDF, merge / page select / rotate, inspect, render QA |
| `slides-artifacts` | `create_slides`, `revise_slides`, `inspect_slides` | owned business theme + layout variants, tables, simple charts, bounded revision by slide index/id, render QA |
| `spreadsheet-artifacts` | `create_spreadsheet`, `revise_spreadsheet`, `inspect_spreadsheet` | declarative sheets/blocks, bulk values + formulas + styles, tables, validation, conditional formatting, charts, bounded revision, inspect, LibreOffice recalculation when available |

Config keys (validated strictly at composition; unknown keys fail):
`max_input_bytes` (25 MB), `max_output_bytes` (25 MB), `process_timeout_seconds`
(120; bounds 5–600), `render_max_pages` (8; bounds 1–50), `work_dir`
(operator-owned absolute path; `ZUAEF_ARTIFACTS_WORK_DIR` fallback).

Path/process safety (P2): all inputs resolve under the workspace (traversal,
absolute paths and symlink escapes rejected; secret patterns rejected); outputs
always land under `workspace/artifacts/<format>/` with bounded unique names and
never overwrite; system tools run only through a private bounded wrapper
(fixed executable allowlist, argv lists, `shell=False`, timeout, capped output);
the plugin exposes **no** arbitrary shell or code execution.

## 6. Deferred loading and natural-language routing

- Mode actually used: **capability-level deferred loading**
  (`Capability(defer_loading=True)` × 4) — no format commands, no Python
  keyword switch.
- One deferred catalog entry per capability, business-semantic in Chinese and
  English (e.g. 提案/报告/客户方案, 发客户/正式版/PDF, 周会材料/汇报/pitch,
  报价表/预算/利润测算), so ordinary outcome intent selects the right
  capability; explicit user format requests override.
- Tools stay hidden until the capability is loaded (`load_capability`), which
  keeps the base tool surface unchanged for non-artifact tasks.

## 7. Feishu automatic delivery

- One generic helper `GatewayService._send_receipt_artifacts(session, receipt)`
  performs: workspace containment check → file exists → size ≤ surface limit →
  `surface.send_document(...)`; otherwise a text notice. Used by both the manual
  `/artifacts` recovery command and the automatic terminal path.
- `ZUAEF_GATEWAY_AUTO_ARTIFACTS=true` (default false) enables automatic delivery
  of the settled run's eligible artifacts right after the terminal text; only
  `completed` runs are eligible.
- Delivery failures are logged and reported as a short transport warning; they
  never rewrite the settled execution truth.
- Tests: 7 fake-surface tests (auto-send on completed run, default-off,
  failed-run skip, oversize block, outside/missing block, failure does not
  rewrite truth, manual command still works) + 110 existing gateway tests.

## 8. P7 real-lane results (deepseek lane, pilot profile)

Workspace `/home/barry/zuaef-artifacts-pilot-ws`, receipts under
`~/.zuaef-state/receipts/`.

| # | Scenario | Run | State | Evidence |
|---|---|---|---|---|
| 1 | explicit editable Word proposal | `ad17a17a` | completed | DOCX produced, 3 tool calls |
| 2 | client-final version → PDF | `c16342cb` + `ec6a4399` | completed | final DOCX then PDF conversion |
| 3 | weekly management deck ≤ 6 pages | `a878909d` | model iterated itself (7→6 pages) then hit the request limit; artifacts complete | 3 .pptx variants incl. `-6页` / `-final` |
| 4 | three price tiers → margin workbook | `f401be74` | completed | 33 formulas + chart; LibreOffice recalculation embeds cached values |
| 5 | report + calculation table (multi-capability) | `8f2ceebd` | failed (supplier channel), 2 capabilities loaded | deterministic tests prove both capabilities load in one run; production was blocked by the supplier channel fault, not by composition |
| 6 | inbox XLSX → client PDF | `c6c19709` | completed | 12 tool calls, PDF produced |
| 7 | follow-up revision (40→60 units) | `785fba0e` | completed | `rev2.docx` + updated PDF variant |
| 8 | no-artifact control (`总结一下这个文件说了什么`) | `f46c5512` | completed | `artifact_facts: []`, 3 tool calls (`inspect_document`, `file_info`, `read_document`), no capability loaded |

Three real defects were found by these runs and fixed inside the plugin:

1. **snap LibreOffice cannot read hidden dirs or host `/tmp`** → operator
   work-dir override (`work_dir` config / `ZUAEF_ARTIFACTS_WORK_DIR`); the
   default remains the state root so portability is unaffected.
2. **empty table cells were rejected by validation** → allowed (business tables
   legitimately contain blanks).
3. **staging leftovers leaked into receipt `artifact_facts`** (would pollute
   automatic delivery) → staging lifecycle fixed; staging files are always
   consumed.

## 9. P8 regression, lint, manifest, clean checkout, kernel

Verification commands and results (final run on the tree reported here):

| Gate | Command | Result |
|---|---|---|
| Targeted artifact tests | `pytest -q tests/test_artifacts_plugin.py tests/test_artifacts_paths.py tests/test_artifacts_docx_pdf.py tests/test_artifacts_slides_spreadsheet.py tests/test_artifacts_routing.py tests/test_gateway_auto_artifacts.py` | **45 passed** |
| Knowledge Worker + gateway subset | `pytest -q tests/test_knowledge_worker_plugin.py tests/test_knowledge_worker_documents.py tests/test_gateway_service.py tests/test_gateway_feishu.py tests/test_gateway_architecture.py` | **154 passed** |
| Full suite | `pytest -q --ignore=tests/test_quant_hydration.py --ignore=tests/test_quant_v31.py` | **1125 passed, 5 skipped, 1 failed** — the single failure is pre-existing, see notes |
| Lint | `ruff check .` | **31 errors = the 30 pre-existing HEAD findings (quant/tools) + 1 import-order finding in the concurrent `zuaef-wechat-x` plugin** → zero new findings from this work |
| Manifest integrity | `pytest -q tests/test_manifest_integrity.py` | **3 passed** (bytes/hash, coverage, containment) |
| Clean checkout without `oai-skills/` | `tar` copy (no `.git`, no `oai-skills`) → `uv sync --frozen` | installs all workspace members incl. `zuaef-artifacts 0.1.0`; plugin discovery lists `artifacts 0.1.0`; artifact plugin/paths/routing + manifest gates **33 passed** |
| Kernel diff | `git status --porcelain src/zuaef_agent/core.py src/zuaef_agent/runtime.py src/zuaef_agent/composition.py` | **empty** (no functional change) |

Notes on the residual full-suite failure and on concurrent work in the shared tree:

1. `tests/test_quant_research.py::TestMarketIntelAdapter::test_bounded_items_with_source_and_time`
   fails identically on a pristine `HEAD` export → **pre-existing**, unrelated.
   (`tests/test_quant_hydration.py` and `tests/test_quant_v31.py` are excluded
   because they need the opt-in `quant` dependency group — pandas/akshare are
   not installed in this lane.)
2. Concurrent work landed in the shared tree while this task ran: a new
   `plugins/zuaef-wechat-x/` plugin + `profiles/wechat-x.toml`, and four
   `SKILL.md` files under `plugins/zuaef-competitive-intelligence/` and
   `plugins/zuaef-knowledge-worker/`. Their manifest entries were added
   (path/bytes/sha256, surgical append — no regeneration) so the covers-all
   contract holds for the tree as reported; **their author owns future
   re-syncs**. The one remaining new lint finding (`I001` import order in
   `plugins/zuaef-wechat-x/zuaef_wechat_x/plugin.py`) belongs to that
   workstream and was deliberately not edited here.

Lint work in this change set: the new/changed artifact files were fixed from
77 findings to 0 (import order, unused imports, `X | Y` annotations,
positional-only `model_post_init(..., /)` signatures, the missing `Path` import
in the spreadsheet engine, `check=False` on the bounded subprocess call, no-op
`try/except` removal, `TypeError` for wrong-typed spec input, logging instead of
`except: pass` in the auto-delivery notice path). The `oai-skills/` reference
tree was added to the ruff exclude list so the local lint gate measures the
delivery tree.

## 10. ARM64 readiness (OrangePi, probed 2026-09-11)

| Fact | Result |
|---|---|
| architecture | `aarch64` |
| project venv Python | 3.12.2 (≥ 3.11 required ✓) |
| `python-docx` / `python-pptx` / `openpyxl` / `pypdf` in the project venv | present |
| `zuaef_artifacts` installed there | **not yet** (this work is not pushed to the OrangePi remote yet) |
| LibreOffice | **absent** → DOCX→PDF conversion and xlsx recalculation must report "missing dependency"; do not claim a PDF or a recalculated workbook there |
| `pdftoppm` | present (`/usr/bin/pdftoppm`) → PDF render QA works |
| node / npm | present (not needed; slides use python-pptx) |

Operator install for full QA on that host (Debian/Armbian, as root):
`apt-get install -y libreoffice-writer libreoffice-impress libreoffice-calc poppler-utils`
(system packages stay optional; the plugin never installs packages itself).

## 11. Confirmations required by the master prompt

- **Production runtime does not depend on `oai/`** (here `oai-skills/`): no
  runtime or test path references it (grep over the delivered tree returns only
  the ruff-exclude comment in `pyproject.toml`); the clean-checkout install and
  test run above were executed with the directory absent.
- **`core.py`, `runtime.py`, `composition.py` received no functional change**:
  `git status --porcelain` for the three paths is empty and `git diff` shows
  nothing for them.
- Feishu closed loop: live credentials were not available in this development
  environment, so live Feishu remains an **operator smoke step**; fake-surface
  integration tests cover the adapter-independent behavior.

## 12. Known limitations (v0.1)

- PDF: no true redaction, forms, OCR or encryption; page operations are limited
  to merge / select / rotate / inspect. Never promise the unsupported ones.
- `create_pdf` builds a DOCX first and converts it through LibreOffice →
  conversion QA requires LibreOffice; without it `create_pdf` reports a missing
  dependency instead of producing an unverified PDF.
- Spreadsheet: no cached formula values unless LibreOffice recalculation is
  available; openpyxl alone never evaluates formulas.
- Slides: python-pptx backend with the ZUAEF-owned theme only; no third-party
  templates (and none copied from the OAI reference material).
- QA is structural/render based; the active model lane is text-only, so no
  visual-parity claim is made and no image preview tools ship.
- Artifact production runs need a larger request budget than the default 12;
  **use ≥ 24** (`--request-limit 24` or `ZUAEF_REQUEST_LIMIT=24`), as observed in
  P7 runs 3/4/5.
- Supplier channel flakiness (non-standard `finish_reason`, truncated response
  JSON, argument retries) was observed in P7; it is unrelated to the plugin and
  converges to `failed`, never to fabricated output.

## 13. Operator smoke commands

Run from the repository root (no secrets in any command):

```bash
# 1. install / sync (adds the plugin as a workspace member)
uv sync --frozen

# 2. plugin discovery + metadata
uv run zuaef-agent plugin list
uv run zuaef-agent plugin inspect artifacts

# 3. profile resolution without any model request (the Knowledge Worker
#    composes YouSearch, so a non-empty YDC_API_KEY is required even though no
#    search happens; any deployment placeholder works on a never-searching host)
YDC_API_KEY=<you.com key or deployment placeholder> \
uv run zuaef-agent profile check general-knowledge-worker-artifacts \
  --config-root "$PWD"

# 4. targeted tests
uv run pytest -q tests/test_artifacts_plugin.py tests/test_artifacts_paths.py \
  tests/test_artifacts_docx_pdf.py tests/test_artifacts_slides_spreadsheet.py \
  tests/test_artifacts_routing.py tests/test_gateway_auto_artifacts.py

# 5. factual dependency probe (architecture, engines, system tools)
uv run python -c "from zuaef_artifacts.process import probe_dependencies as p; \
import json; print(json.dumps(p(), ensure_ascii=False, indent=1))"

# 6. one CLI natural-language artifact run (pilot profile; needs the model key)
YDC_API_KEY=<you.com key or deployment placeholder> \
ZUAEF_CONFIG_ROOT="$PWD" ZUAEF_REQUEST_LIMIT=24 \
  uv run zuaef-agent run \
  "根据 inbox/供应商报价单.xlsx，做一份能直接发给客户的正式合作方案（PDF）。" \
  --profile general-knowledge-worker-artifacts \
  --workspace /home/barry/zuaef-artifacts-pilot-ws
```

Feishu deployment (enable automatic artifact delivery, then restart — the
gateway reads `.env` only at process start):

```bash
printf '\nZUAEF_GATEWAY_AUTO_ARTIFACTS=true\n' >> .env
systemctl --user restart zuaef-gateway
systemctl --user status zuaef-gateway --no-pager
```

On hosts where LibreOffice ships as a snap, also set a plain (non-hidden,
non-`/tmp`) work base, e.g.
`ZUAEF_ARTIFACTS_WORK_DIR=/home/<user>/zuaef-artifacts-work`.

## 14. Deltas vs. the spec pack / master prompt

- The reference directory is named `oai-skills/`, not `oai/` (same license
  boundary; recorded in §2.5).
- Slides backend is python-pptx rather than PptxGenJS — rationale in §2.7
  (P4 requires bounded revision of an existing deck; ARM64 has no provisioned
  Node lane, and `ops/install_orangepi_node.sh` installs neither LibreOffice nor
  poppler).
- Nothing else: all "current repository facts" listed in `00_SOURCE_OF_TRUTH.md`
  were confirmed true in the working tree.
