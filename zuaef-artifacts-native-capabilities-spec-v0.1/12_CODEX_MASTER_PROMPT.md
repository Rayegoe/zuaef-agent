# 12 — Codex Master Prompt

Copy the instruction below into Codex while the current working directory is the `zuaef-agent` repository root.

---

Implement **ZUAEF Artifacts Native Capabilities v0.1** using the spec pack provided with this instruction.

Your execution authority is this pack plus the repository's current `AGENTS.md`. Work against the actual local tree; do not assume the remote default branch contains local changes.

## Required outcome

Add one production plugin, `zuaef-artifacts`, that provides four native PydanticAI capability units for DOCX, PDF, Slides, and Spreadsheet production/revision. They must be discoverable from ordinary natural-language outcome intent. Users must not need `/docx`, `/pdf`, `/ppt`, `/excel`, or any format command.

The existing single ZUAEF Agent remains the outcome owner. The existing Knowledge Worker remains responsible for general document reading/search/research. The new plugin produces and revises final artifacts under `workspace/artifacts/`.

## Local OAI reference directory

A local `oai/` directory already exists at repository root. In P0 locate the four skill roots and read each local `LICENSE.txt`. Treat the directory as reference-only by default. Do not copy OAI source, prompts, helper code, templates, or assets into the shippable plugin unless the user's applicable agreement explicitly permits it. Do not modify or commit the `oai/` tree as part of this work. Production execution must not depend on it.

## Kernel constraint

`src/zuaef_agent/core.py`, `src/zuaef_agent/runtime.py`, and `src/zuaef_agent/composition.py` must receive no functional changes in v0.1. The current plugin capability seam is expected to be sufficient. If it is not, document the exact reproduced blocker before considering any kernel change; do not redesign around a guess.

## Security constraint

Do not expose arbitrary shell or arbitrary code execution through the artifact plugin. Shell stays disabled in the pilot profile. Fixed system executables such as LibreOffice or Node may be invoked only through private bounded wrappers using validated workspace paths, fixed executable selection, argv lists, timeouts, and `shell=False`.

## Capability API

During P0 inspect the pinned PydanticAI API in the current environment. Use the simplest released public capability API available there. Prefer capability-level deferred loading when supported cleanly. Do not upgrade PydanticAI simply to make the implementation syntax nicer.

## Implement in phases

Follow `09_IMPLEMENTATION_TASKS.md` exactly from P0 through P8. Finish each phase's checks before moving on.

Do not ask the product owner to choose low-level implementation details that can be resolved from the local tree. Choose the smallest reliable option and record it in `IMPLEMENTATION_REPORT.md`.

## Required product behaviors

Natural-language examples that must work after implementation:

1. `根据这个报价表，做一份可以直接发给客户的正式方案。`
2. `把本周销售和未成交原因整理成老板周会材料，最多 6 页。`
3. `三个供应商按 399、499、599 三档售价算毛利，给我一个以后能自己改参数的表。`
4. `给我老板汇报和详细计算表。`
5. `第二页价格改成 168，付款方式改成 30/70，再给我客户版。`
6. `总结一下这个文件说了什么。` — control case: should not create an office artifact unless needed.

Explicit user format requests override automatic selection.

## Feishu outcome

The current Feishu adapter already receives files and has a generic send-document primitive. Reuse the existing receipt-aware artifact path. Refactor the current manual artifact-send loop into one generic helper and support automatic terminal artifact delivery behind a small generic gateway setting. For the Feishu pilot, enable it. Keep the manual artifact command as recovery.

Do not put document-format business routing into Gateway or Feishu adapter.

## Format implementation

Implement independent engines with public libraries/system tools:

- DOCX: common creation/revision with `python-docx`, render via bounded office conversion.
- PDF: creation/conversion and common page operations using a minimal coherent public stack.
- Slides: prefer PptxGenJS with ZUAEF-owned layout/theme if Node is viable on the target hosts; otherwise choose one supported primary backend and document why.
- Spreadsheet: use `openpyxl` as the default engine; use LibreOffice for recalculation when available. Preserve formulas when they express editable business logic.

Do not ship copied OAI slide templates.

## QA

Create/revise tools own their mechanical QA cycle: build -> reopen/inspect -> render where supported -> format-local checks -> result. Do not force the model to call multiple low-level mechanical tools for every artifact.

If the pinned stack and active model support image content returned from tools, optional preview tools may expose bounded rendered images for visual review. Do not modify core solely to obtain this feature. When unavailable, report structure/render QA only and do not claim visual parity.

## Testing

Implement the full acceptance matrix in `10_ACCEPTANCE.md`, including routing paraphrases, no-artifact controls, path/security tests, Feishu auto-delivery tests, and clean deployment without the local `oai/` directory.

Run existing relevant baseline tests before edits, targeted tests during phases, then full tests and lint before completion.

Follow repository rules for the existing build inventory file; update it surgically rather than creating a new integrity subsystem.

## Completion report

At the end, create `IMPLEMENTATION_REPORT.md` containing:

- baseline facts discovered in P0;
- exact files changed;
- exact dependencies added;
- capability surface and supported v0.1 operations;
- deferred-loading mode actually used;
- QA mode actually available;
- Feishu auto-delivery behavior;
- known limitations;
- ARM64 readiness result;
- tests and lint results;
- exact operator smoke commands;
- confirmation that production runtime does not depend on `oai/`;
- confirmation that the three kernel files above received no functional changes.

Stop at a clean, tested v0.1. Do not opportunistically implement advanced Word review features, OCR, PDF forms, native Feishu Docs, large template systems, or unrelated refactors.

---
