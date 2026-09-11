# 07 — Format Engine Plan

## General rule

Use independent implementations based on public libraries and system tools. The local OAI tree is not a production runtime dependency.

Prefer deterministic, declarative generation over model-generated executable source.

## DOCX engine

### Primary libraries

- `python-docx` for common document creation/editing.
- Standard XML tooling only for narrowly required unsupported features.
- LibreOffice headless or an equivalent configured converter for render QA.
- A PDF-to-image renderer for page previews after conversion.

### v0.1 create support

Implement a `DocumentSpec` with common blocks:

```text
DocumentSpec
- title
- subtitle?
- blocks[]
- page_size?
- margins?
- header_text?
- footer_text?

Block variants
- heading(level, text)
- paragraph(text, emphasis spans optional)
- bullet_list(items)
- numbered_list(items)
- quote(text)
- table(headers, rows, widths optional)
- image(path, caption optional, width optional)
- page_break
```

Keep styling opinionated and limited. Create one clean default business theme; do not implement a general Word styling language.

### v0.1 revision support

Implement deterministic operations:

- replace exact text with bounded match policy;
- append blocks;
- insert blocks after a located heading;
- update title/subtitle;
- update a table cell by table index and row/column coordinates;
- replace a simple table.

If a requested edit cannot be represented safely, return an unsupported-operation error and let the model decide whether a controlled rebuild is acceptable.

### Later scope

- tracked changes;
- comments;
- content controls;
- watermarking;
- complex fields/cross-references;
- advanced section layouts;
- redaction/anonymization;
- accessibility remediation.

Do not implement these merely because reference material contains them.

## PDF engine

### Primary libraries/tools

Choose small public libraries already compatible with repository constraints, for example:

- `pypdf` for page-level manipulation;
- PyMuPDF or another supported renderer/editor where licensing and deployment fit;
- ReportLab/HTML-to-PDF path for simple generated reports if appropriate;
- LibreOffice conversion for Office-to-PDF.

Codex must choose one coherent stack after checking existing dependencies; avoid redundant libraries that solve the same v0.1 task.

### v0.1 support

- create PDF from simple structured/Markdown-like content;
- convert DOCX/PPTX/XLSX to PDF;
- merge ordered inputs;
- extract/select page ranges;
- rotate pages;
- inspect page count and basic properties;
- render selected pages.

### Later scope

- OCR;
- forms;
- true content redaction;
- encryption;
- annotations;
- coordinate editing UI;
- renderer parity testing.

## Slides engine

### Preferred backend

Use PptxGenJS with a small ZUAEF-owned layout layer if Node is acceptable on the supported host. This is a good fit for x86_64 and ARM64 Linux and avoids a dependency on a service-specific presentation backend.

If repository deployment constraints make Node undesirable, `python-pptx` is an acceptable fallback, but choose one primary creation backend for v0.1 rather than maintaining two competing implementations.

### Do not ship the OAI template pack by default

The local reference Slides package may contain a large template directory. It is not required for the MVP and must not be copied into the plugin.

Create one or two small ZUAEF-owned themes instead:

- `business-light`
- optional `business-dark`

### Slide model

```text
DeckSpec
- title
- subtitle?
- theme
- slides[]

Slide variants
- title
- title_body
- key_message
- two_column
- image_text
- table
- chart
- quote
- closing
```

Use conservative layout defaults and readable typography.

### QA

- reopen package where practical;
- convert with LibreOffice;
- render slides to PNG;
- optional multimodal preview.

## Spreadsheet engine

### Backend decision

Do not depend on a service-specific workbook library that is unavailable in ordinary ZUAEF deployments.

Use a public Python stack, with `openpyxl` as the default because the repository already uses it for reading `.xlsx`. Add XlsxWriter only if a demonstrated feature gap requires it for creation.

LibreOffice headless may be used for recalculation and render QA when installed.

### Workbook model

Support one build call with structured sheet specs rather than exposing cell-by-cell tools.

```text
WorkbookSpec
- sheets[]

SheetSpec
- name
- blocks[]

Block variants
- matrix(start_cell, values)
- formulas(start_cell or mapping)
- table(range/name/style)
- format(range, number_format, font, fill, border, alignment)
- widths(mapping)
- heights(mapping)
- validation(range, allowed values/rule)
- conditional_format(range, rule)
- chart(source ranges, chart type, anchor)
```

Revision uses the same bounded operations against an existing workbook.

### Formula policy

When derived values are expected to remain editable, prefer formulas rather than converting the business model to static numbers.

Do not add formulas merely for decorative or unnecessary calculations.

### Recalculation

`openpyxl` does not evaluate formulas. If computed results must be refreshed before delivery, use a bounded LibreOffice recalculation/conversion pass when available, then reopen to inspect cached values.

If no recalculation engine is present, preserve formulas and clearly report that cached results were not independently recalculated.

## ARM64 deployment

The implementation must avoid assuming x86-only binaries.

The OrangePi deployment lane should prefer:

- pure Python wheels/source packages;
- Node packages that are architecture-neutral JavaScript;
- distro-provided LibreOffice and PDF rendering tools available for ARM64.

Any dependency that is not viable on ARM64 must be optional or replaced before v0.1 is promoted to the OrangePi profile.
