# 06 — Artifact Runtime, Security, and QA

## Scope

This is a plugin-local deterministic execution layer, not a new ZUAEF runtime.

## Path authority

Create a small helper module that owns path resolution for artifact operations.

Suggested responsibilities:

- `resolve_input_path(relative_path)`
- `resolve_existing_artifact(relative_path, expected_suffix)`
- `allocate_output_path(kind, requested_name)`
- `allocate_work_dir(call_scope)`
- `allocate_render_dir(call_scope)`

Rules:

- no workspace escape;
- no writing into inbox;
- no writing into knowledge;
- no arbitrary hidden-directory output;
- sanitize user/model supplied filenames;
- preserve Unicode filenames where safe;
- enforce correct extension;
- avoid overwriting an existing final artifact unless revision explicitly targets that file or a versioned output is intentionally requested.

## External process wrapper

Office conversion and some rendering may require installed executables such as LibreOffice, Node, or a PDF renderer.

This does not justify exposing the Harness Shell capability.

Implement a private bounded process helper with:

- executable chosen from a fixed internal allowlist;
- argv supplied as a list, never shell text;
- `shell=False`;
- bounded timeout;
- controlled working directory;
- controlled environment additions;
- captured stdout/stderr with bounded return size;
- clear error when dependency is absent;
- no user-controlled executable path;
- all file arguments validated through artifact path helpers first.

## Dependency probing

Provide one internal probe used by tests/diagnostics, not as a model-visible general command.

Probe at minimum:

- Python format libraries importable;
- LibreOffice/compatible office converter present when configured;
- Node present if Slides backend requires it;
- presentation JavaScript dependencies installed;
- PDF renderer present when configured.

A missing optional dependency should disable only the affected optional QA path where possible. A missing dependency required to create the requested format should return a clean capability failure.

## QA tiers

Define three local QA concepts without adding a new kernel state machine:

### Structure QA — required

Examples:

- generated file exists and is non-empty;
- package can be reopened by the selected library;
- expected sheet/slide/page/document structure exists;
- spreadsheet formulas/targets are syntactically present;
- output suffix matches format.

### Render QA — required where a renderer is available in the supported deployment

Examples:

- DOCX converts successfully and pages render;
- Slides converts/renders successfully;
- Spreadsheet converts or selected ranges render;
- PDF pages render to images.

This catches many broken-file and missing-glyph/layout failures even without visual reasoning.

### Visual QA — deployment-dependent in v0.1

If the pinned PydanticAI stack and active model support tool-returned image content, preview tools may return selected rendered PNGs as multimodal content so the same agent can inspect them.

Do not modify core just to force visual QA.

If the deployment cannot consume local rendered images in model context, v0.1 reports structure/render QA only and does not claim visual parity with the OAI reference environment.

## Preview limits

A preview tool must be bounded:

- explicit page/slide/range selection or a small default sample;
- cap number of returned images;
- cap total bytes;
- downscale oversized previews;
- never return the entire large document as image content by default.

## Intermediate-file discipline

Temporary converted PDFs and rendered PNGs live under state-owned work/render directories, not the final delivery folder.

Final artifact directories should contain deliverables, not QA debris.

## Error strategy

Bad input is recoverable and format-local.

Return short structured errors for:

- unsupported file;
- missing renderer;
- conversion failure;
- invalid output name;
- path rejection;
- malformed document package;
- unsupported revision operation.

Do not crash the whole gateway process for a single bad office file.

## Resource bounds

Use configurable but conservative plugin-local limits for:

- input bytes;
- output bytes;
- render page/slide count per preview;
- process timeout;
- image size.

Do not create a new global configuration framework. Plugin config must remain non-secret and small.
