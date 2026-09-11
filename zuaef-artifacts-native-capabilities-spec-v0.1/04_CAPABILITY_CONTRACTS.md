# 04 — Capability Contracts

## Common capability metadata

Each format capability must expose a business-oriented description suitable for natural-language discovery.

Do not describe capabilities only by extensions.

### DOCX description intent

Use for editable formal long-form business documents: proposals, reports, briefs, contract-like drafts, structured meeting outputs, and documents expected to be revised after delivery.

### PDF description intent

Use for polished fixed-layout deliverables intended for sharing, archiving, printing, publishing, or producing a frozen client-facing version from another artifact.

### Slides description intent

Use for presentation-ready visual narratives: management reviews, client pitches, project updates, strategy briefings, weekly/monthly reviews, and meeting decks.

### Spreadsheet description intent

Use for structured calculations and editable tabular models: pricing, budgets, forecasts, scenario analysis, comparisons, trackers, operating models, and data-heavy deliverables.

## Common result envelope

All artifact tools should return a small, consistent serializable result shape. Use existing project conventions if one already exists; do not introduce a global schema solely for this plugin.

Suggested local model:

```text
ArtifactResult
- ok: bool
- artifact_path: workspace-relative path or null
- artifact_type: docx | pdf | slides | spreadsheet
- qa_state: not_run | passed | passed_with_warnings | failed
- warnings: short list
- summary: short machine-generated statement of what changed
```

Do not return large binary bodies as normal JSON tool results.

## Common path rules

Every input and output path accepted from the model must:

- be workspace-relative;
- resolve inside the configured workspace;
- reject traversal outside the workspace;
- reject protected secrets and keys;
- never accept arbitrary absolute output paths;
- write final outputs only below the designated artifact root for that format.

Existing artifacts may be revised only when they are inside the workspace and of the expected file type.

## Tool granularity

Avoid dozens of tiny model-visible tools.

Each capability should expose a small high-level surface. Target three to five model-visible tools per format.

Mechanical sub-steps such as save, render, page conversion, temporary cleanup, and structural checks should normally happen inside one high-level tool call.

## DOCX v0.1 tool surface

Recommended:

- `create_docx`
- `revise_docx`
- `inspect_docx`
- `preview_docx` only if multimodal tool output is supported by the pinned stack and active model

`create_docx` should accept a declarative document spec with common blocks:

- title/subtitle;
- headings;
- paragraphs;
- bullet/number lists;
- quotes/callouts;
- tables;
- images from workspace paths;
- page breaks;
- basic header/footer metadata.

`revise_docx` v0.1 must support bounded structured edits, at minimum:

- replace text;
- append/insert section;
- replace a named/located section when deterministic location is available;
- update table cells or replace a simple table;
- update title/subtitle.

Advanced review lifecycle features are later scope unless needed by an acceptance case.

## PDF v0.1 tool surface

Recommended:

- `create_pdf`
- `convert_to_pdf`
- `edit_pdf`
- `inspect_pdf`
- `preview_pdf` when multimodal preview is available

Required operations:

- generate a simple polished PDF from structured/Markdown-like content;
- convert DOCX/PPTX/XLSX to PDF through a bounded system conversion wrapper;
- merge selected PDFs;
- select/split pages;
- basic rotate/crop where supported cleanly;
- inspect page count and basic metadata;
- render selected pages to images.

True redaction, forms, OCR, encryption, and advanced annotations are later scope.

## Slides v0.1 tool surface

Recommended:

- `create_slides`
- `revise_slides`
- `inspect_slides`
- `preview_slides` when multimodal preview is available

The creation spec should support:

- deck title and optional subtitle;
- slide title;
- body bullets;
- two-column content;
- image + text layout;
- table;
- simple chart from structured data;
- quote/key-message slide;
- closing/recommendation slide;
- speaker notes when easy to support.

The model should supply content and layout intent; engine code should implement safe layout defaults.

Do not expose raw JavaScript generation to the model.

## Spreadsheet v0.1 tool surface

Recommended:

- `create_spreadsheet`
- `revise_spreadsheet`
- `inspect_spreadsheet`
- `preview_spreadsheet` when multimodal preview is available

Creation/revision must support:

- multiple sheets;
- bulk value write;
- formulas;
- number/date/percent/currency formatting;
- widths/heights/wrap;
- basic fills/borders/fonts/alignment;
- tables;
- data validation for common categorical fields;
- conditional formatting;
- basic charts;
- formula/result inspection after recalculation when a recalculation engine is available.

Spreadsheet business logic that is expected to remain editable must remain formula-driven where practical.

## QA behavior inside tools

High-level create/revise tools should execute this mechanical lifecycle without requiring extra model turns:

```text
validate request
-> build/revise file
-> reopen/inspect structure
-> render or convert for QA when supported
-> run format-local checks
-> return final artifact result
```

A separate preview tool exists only to let a multimodal model visually review selected pages/slides/ranges when the deployment supports that path.

## No false completion

If file creation succeeds but required QA fails:

- preserve the artifact for debugging when useful;
- return `ok=false` or a clearly non-passing QA state;
- include a bounded warning;
- do not let capability guidance instruct the model to claim polished completion.
