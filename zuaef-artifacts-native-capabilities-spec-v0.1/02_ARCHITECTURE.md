# 02 — Architecture

## Target package

Create one independent in-repo plugin distribution:

```text
plugins/zuaef-artifacts/
├── pyproject.toml
└── zuaef_artifacts/
    ├── __init__.py
    ├── plugin.py
    ├── contracts.py
    ├── paths.py
    ├── process.py
    ├── capabilities/
    │   ├── __init__.py
    │   ├── docx.py
    │   ├── pdf.py
    │   ├── slides.py
    │   └── spreadsheet.py
    ├── engines/
    │   ├── __init__.py
    │   ├── docx_engine.py
    │   ├── pdf_engine.py
    │   ├── slides_engine.py
    │   └── spreadsheet_engine.py
    └── guidance/
        ├── docx.md
        ├── pdf.md
        ├── slides.md
        └── spreadsheet.md
```

The exact internal split may be simplified if fewer files are clearer, but preserve the four capability boundaries and one plugin distribution.

## Plugin factory

The plugin entry point must follow the existing repository pattern and return a `PluginBundle`.

Conceptual shape:

```python
PluginBundle(
    capabilities=[
        DocxArtifactCapability(...),
        PdfArtifactCapability(...),
        SlidesArtifactCapability(...),
        SpreadsheetArtifactCapability(...),
    ]
)
```

Do not add a parallel registry. Do not add a second runtime.

The profile enabling this plugin must set capability permission explicitly, consistent with current ZUAEF composition policy.

## Capability construction strategy

Use the simplest public PydanticAI capability API supported by the repository's installed version.

Preferred order:

1. If the pinned version has the public declarative `Capability` helper with descriptions, instructions, tools/toolsets, and capability-level deferred loading, use it.
2. Otherwise subclass the installed public `AbstractCapability` and provide the toolset/instructions through its supported methods.

Do not upgrade PydanticAI merely to obtain a nicer syntax unless the current API cannot express the required behavior.

## Why capability, not only toolset

Each artifact domain needs to bundle:

- semantic discovery description;
- domain production guidance;
- its deterministic tools;
- local QA semantics;
- potentially rich preview output.

That crosses the threshold from a bare domain action surface into a reusable behavior unit.

## One-agent composition

The desired combined profile is conceptually:

```text
Knowledge Worker
+ DOCX artifact capability
+ PDF artifact capability
+ Slides artifact capability
+ Spreadsheet artifact capability
```

This must still be one Agent instance. There is no artifact sub-agent in v0.1.

## Capability graph, not command router

The same user request may load several capabilities:

```text
inbox quotation.xlsx
        |
        v
Knowledge Worker reads/analyzes
        |
        +-----------------+
        |                 |
        v                 v
Spreadsheet           DOCX
pricing model         proposal
                          |
                          v
                         PDF
```

The main model owns the semantic sequence. Deterministic format engines own mechanical generation, conversion, rendering, and validation.

## Existing artifact authority

Keep using `workspace/artifacts/` as the durable output root. Generic model-facing FileSystem must not become an alternate write path into this tree.

Do not add a second artifact database.

## Proposed paths

```text
workspace/artifacts/docx/
workspace/artifacts/pdf/
workspace/artifacts/slides/
workspace/artifacts/spreadsheets/

.zuaef-state/artifact-work/<run-or-call-scope>/
.zuaef-state/artifact-renders/<run-or-call-scope>/
```

Temporary renders are internal QA material. They are not returned to users unless explicitly requested.

## Existing Knowledge Worker relationship

Do not duplicate reading/search extraction already present in `zuaef-knowledge-worker`.

Artifact capability tools may inspect an input file only as needed to revise or validate that artifact. General “find content across documents” remains Knowledge Worker's responsibility.

## Gateway relationship

Gateway remains transport and projection only.

Permitted Gateway behavior:

- receive input attachments;
- automatically send receipt-listed completed artifact files;
- enforce file-size limits;
- report delivery failures separately from execution result.

Prohibited Gateway behavior:

- decide that a customer proposal should be PDF;
- select an artifact capability;
- rewrite business content;
- decide whether a spreadsheet needs a chart.
