# 09 — Implementation Tasks

Execute phases in order. Do not start the next phase merely because it is listed here; finish and verify the current phase first.

## P0 — Baseline and compatibility probe

Deliverable: `IMPLEMENTATION_REPORT.md` section “P0 Baseline”.

Tasks:

- [ ] Read repository `AGENTS.md`.
- [ ] Inspect current `plugin_api.py`, `composition.py`, `core.py`, current Knowledge Worker plugin, and General Knowledge Worker profile.
- [ ] Inspect current Feishu adapter and GatewayService artifact delivery path.
- [ ] Locate the four local OAI skill roots under repository `oai/`.
- [ ] Read their local license files and record the implementation boundary without reproducing the text.
- [ ] Confirm `oai/` Git state. Do not alter it.
- [ ] Confirm current pinned PydanticAI capability API and whether capability-level deferred loading is available.
- [ ] Confirm current tool-return multimodal support in the pinned PydanticAI version.
- [ ] Confirm Python version.
- [ ] Probe LibreOffice availability/version.
- [ ] Probe Node/npm availability/version if using PptxGenJS.
- [ ] Probe installed PDF rendering utility/library candidates.
- [ ] Run the existing relevant test baseline before edits.

P0 pass criteria:

- no production code changed;
- exact implementation choices for capability API, slides backend, PDF stack, and QA route are recorded;
- no unknown blocking dependency remains hidden.

## P1 — Plugin skeleton and packaging

- [ ] Create `plugins/zuaef-artifacts/` distribution.
- [ ] Add in-repo plugin entry point `artifacts`.
- [ ] Add package to root workspace dependency/source declarations following repository convention.
- [ ] Implement `build_plugin(env, config)` with strict non-secret config validation.
- [ ] Add four capability objects, initially with minimal no-op or inspect-only toolsets sufficient for composition tests.
- [ ] Add pilot profile `profiles/general-knowledge-worker-artifacts.toml` by cloning current General Knowledge Worker semantics and adding the new plugin with capability permission.
- [ ] Keep tool search enabled and shell disabled.
- [ ] Update the existing build inventory file surgically as required by repository rules.

P1 pass criteria:

- plugin list/inspect sees the installed plugin after normal workspace sync;
- profile check passes with no model call;
- four capabilities compose through existing seams;
- `core.py`, `runtime.py`, `composition.py` have no functional diff.

## P2 — Common runtime helpers

- [ ] Implement workspace-safe path helpers.
- [ ] Implement bounded output naming.
- [ ] Implement work/render temp directories.
- [ ] Implement bounded fixed-executable process wrapper.
- [ ] Implement dependency probe used by tests/diagnostics.
- [ ] Implement plugin-local `ArtifactResult` or reuse an existing suitable local result convention.
- [ ] Add unit tests for traversal rejection, protected paths, output placement, timeout behavior, and absent executable handling.

P2 pass criteria:

- no model-facing arbitrary shell/code execution;
- all final output is restricted to intended artifact roots;
- process invocation uses argv arrays and fixed executable selection.

## P3 — DOCX and PDF capabilities

DOCX:

- [ ] Implement declarative document spec.
- [ ] Implement create.
- [ ] Implement bounded revise operations.
- [ ] Implement structure inspection.
- [ ] Implement office conversion/render QA.
- [ ] Implement optional selected-page multimodal preview if P0 proved support.

PDF:

- [ ] Implement create-from-content route.
- [ ] Implement office-to-PDF conversion.
- [ ] Implement merge/select/rotate core edits.
- [ ] Implement inspect.
- [ ] Implement render QA.
- [ ] Implement optional preview.

P3 acceptance scenario:

1. Generate a three-page Chinese business proposal DOCX containing heading hierarchy, bullets, a table, and an image.
2. Convert to PDF.
3. Reopen both formats.
4. Render both successfully.
5. Revise a price and payment term in DOCX.
6. Regenerate/revalidate client PDF.

## P4 — Slides and Spreadsheet capabilities

Slides:

- [ ] Implement selected backend and owned business theme.
- [ ] Implement core slide variants.
- [ ] Implement table and simple chart.
- [ ] Implement bounded revision by slide index/id and element role.
- [ ] Implement render QA.
- [ ] Optional preview if supported.

Spreadsheet:

- [ ] Implement workbook/sheet declarative spec.
- [ ] Implement bulk values/formulas/styles.
- [ ] Implement tables, validation, conditional formatting, simple charts.
- [ ] Implement bounded revision operations.
- [ ] Implement inspect.
- [ ] Implement recalculation route when LibreOffice exists.
- [ ] Implement render QA for selected sheet/range or converted output.
- [ ] Optional preview if supported.

P4 acceptance scenario:

- Generate a pricing workbook with editable input assumptions, formulas for three price scenarios, a summary area, and one chart.
- Generate a six-slide management deck from the same structured facts.
- Reopen and render both.
- Revise one assumption and verify dependent spreadsheet formulas remain present.

## P5 — Natural-language routing

- [ ] Make each capability's description business-semantic rather than extension-only.
- [ ] Enable capability-level deferred loading if supported and stable in the current stack.
- [ ] Add concise capability guidance for explicit format override and implicit intent selection.
- [ ] Add routing tests with Chinese/English paraphrases.
- [ ] Add no-artifact control tests.
- [ ] Add multi-capability scenario tests.
- [ ] Confirm the agent never requires a format command.

Do not implement a Python keyword switch for format routing.

## P6 — Feishu automatic delivery

- [ ] Extract/reuse one generic receipt-artifact send helper in GatewayService.
- [ ] Add/reuse automatic artifact delivery configuration.
- [ ] Keep current manual artifacts command working as recovery.
- [ ] Add tests using fake surface adapter: completed run with eligible artifact -> one automatic document send.
- [ ] Test oversize/nonexistent/outside-workspace artifacts remain blocked by existing rules.
- [ ] Test upload/send failure does not rewrite execution completion.

No format policy in Gateway.

## P7 — End-to-end profile validation

Run the actual pilot profile with representative natural-language requests:

- [ ] explicit DOCX request;
- [ ] implicit client-final request -> PDF path;
- [ ] implicit management briefing -> Slides;
- [ ] implicit pricing/scenario -> Spreadsheet;
- [ ] proposal + calculations -> multi-capability output;
- [ ] uploaded XLSX -> read via Knowledge Worker -> proposal output;
- [ ] follow-up revision of last artifact;
- [ ] normal factual question -> no artifact.

Where live Feishu credentials are available, run one real Feishu closed-loop smoke test. If they are not available in the development environment, fake-surface integration tests are required and live Feishu remains an operator smoke step.

## P8 — Regression and promotion

- [ ] Run targeted artifact tests.
- [ ] Run existing Knowledge Worker tests.
- [ ] Run gateway tests.
- [ ] Run full repository test suite.
- [ ] Run lint.
- [ ] Confirm build inventory is current.
- [ ] Confirm clean checkout can install without `oai/`.
- [ ] Confirm no runtime path depends on `oai/` or `/home/oai/`.
- [ ] Confirm `core.py`, `runtime.py`, `composition.py` were not functionally modified.
- [ ] Write final `IMPLEMENTATION_REPORT.md` with files changed, supported features, known limits, deployment dependencies, and exact smoke commands.
