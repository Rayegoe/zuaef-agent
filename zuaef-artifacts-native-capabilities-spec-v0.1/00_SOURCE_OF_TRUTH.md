# 00 — Source of Truth

## Goal

Add a small, native artifact-production layer to ZUAEF without changing the kernel architecture.

The source priority for this work is:

1. The current local working tree.
2. Repository `AGENTS.md` and current runtime-refoundation rules where relevant.
3. Current installed PydanticAI and pydantic-ai-harness public APIs in the repository environment.
4. This spec pack.
5. The local `oai/` material only as a non-shippable reference, subject to its own license terms.

When this pack disagrees with the current working tree about an API name or version-specific detail, preserve the architectural decisions here but adapt the syntax to the actually installed public API.

## Current repository facts this design relies on

Codex must verify these in the working tree before edits:

- ZUAEF has one core Agent.
- `PluginBundle` can return toolsets, skill directories, and explicitly permitted PydanticAI capabilities.
- Profile composition already forwards plugin capabilities into `build_agent(..., extra_capabilities=...)`.
- The General Knowledge Worker already reads and searches `.pdf`, `.docx`, `.xlsx`, and `.pptx` files under the workspace using deterministic extraction.
- The General Knowledge Worker profile already enables tool search and disables shell.
- Generic FileSystem writes to `artifacts/*` are protected, so artifact creation belongs in dedicated domain tools/capabilities.
- Feishu already receives file attachments into `workspace/inbox/...`.
- Feishu's surface adapter already has a document-send primitive.
- Gateway `artifacts` handling can already send receipt-listed artifact files when explicitly requested.

If any of these facts are no longer true in the local tree, record the delta in the implementation report and make the smallest compatible adjustment. Do not redesign the kernel.

## Architectural classification

`zuaef-artifacts` is an `ADMITTED_PROFILE` business plugin.

Each format is a Capability because it needs a reusable bundle of:

- business-oriented capability description;
- instructions for when and how to produce the artifact;
- a bounded deterministic action surface;
- format-local rendering and validation behavior;
- optional multimodal preview behavior where the active model supports image input.

No new cross-domain kernel invariant is required.

## Non-negotiable boundaries

- No second agent.
- No artifact router service.
- No format-command UX.
- No new workflow engine.
- No arbitrary code execution exposed to the model.
- No arbitrary shell exposed to the model.
- No direct writes to `workspace/knowledge/` from this plugin.
- No automatic creation of durable Knowledge nodes for every artifact.
- No native Feishu Docs/Sheets editing in v0.1.
- No requirement to support every advanced Word, PowerPoint, PDF, or Excel feature in v0.1.
- No copied OAI implementation assets in the shippable plugin by default.

## Change budget

Expected functional changes:

- new `plugins/zuaef-artifacts/` package;
- new tests;
- one new pilot profile or a controlled update to a profile after pilot acceptance;
- root package dependency/source registration for the new in-repo plugin;
- surgical update to the repository's existing build inventory file;
- a small generic GatewayService refactor/addition for automatic delivery if required by the Feishu MVP.

Expected zero functional changes:

- `src/zuaef_agent/core.py`
- `src/zuaef_agent/runtime.py`
- `src/zuaef_agent/composition.py`

If implementation appears to require changes to those three files, stop that line of work and first prove why the existing extension seams are insufficient.
