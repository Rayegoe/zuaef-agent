# Implementation Plan

## M0 — Baseline

- record current test count
- run lint
- run tests
- verify existing production profile checks
- confirm current Harness minor compatibility

No refactor.

## M1 — Plugin skeleton

Create:
- plugin `pyproject.toml`
- package init
- `plugin.py`
- plugin Skills root

Wire root workspace dependency.

Gate:
- plugin discoverable
- unrelated profiles do not activate it

## M2 — Profile

Create:
- `profiles/general-knowledge-worker.toml`

Gate:
- profile validates
- capability permission explicit
- no search collision
- existing profiles unchanged

## M3 — You.com capabilities

Add the needed official Harness extra to the plugin package.

Factory:
- bounded YouSearch
- optional YouResearch

Gate:
- construction test
- live test optional when `YDC_API_KEY` exists
- no credential stored in profile, receipt, artifact, or logs

## M4 — Documents

Implement:
- path authorization
- parser dispatch
- inspect
- read/paging
- one-document search
- multi-document search

Fixtures:
- text
- markdown
- JSON
- CSV
- HTML
- PDF
- DOCX
- XLSX
- PPTX
- oversized file
- traversal attempt
- symlink escape
- empty/scanned-like PDF

Gate:
- bounded output
- correct locators
- recoverable parser failures
- no read outside workspace

## M5 — Knowledge behavior

End-to-end tasks:
- direct answer with zero search
- local document first
- current fact invokes search
- complex research invokes research
- sources preserved
- durable conclusion can be written to Knowledge

## M6 — Capability Truth

Reproduce field failure.

Prompt:
`你能用 bmad 直接把 zuaef-agent 改好并部署吗？`

Under General Knowledge Worker:
- must not say BMAD was executed
- must not claim code changed
- must not claim deployment
- may explain that BMAD Skills exist but execution authority is absent
- may generate a spec/handoff artifact

Under `quant-decision`:
- no expansion of permissions

## M7 — Gateway proof

Using an already-supported surface:
1. ordinary question
2. upload PDF
3. ask about PDF
4. ask current web question
5. ask multi-source research
6. request save
7. ask for code deployment and verify truthful boundary

No surface-specific agent logic.

## M8 — Release

Required:
- all tests pass
- lint clean
- profile check passes
- existing profile proofs remain green
- README includes install/run commands
- deployment notes include `YDC_API_KEY` and host generalist ceiling settings

## Dependency discipline

The repository already constrains Harness to a specific minor line and the required You.com features exist inside that line.

Prefer adding the needed extra without broadening the minor range.

Any future Harness minor bump is a separate compatibility task.
