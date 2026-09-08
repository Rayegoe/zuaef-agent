---
name: coding
description: Implement, inspect, test and extend the configured ZUAEF repository with native repo tools.
---

Own the requested engineering outcome. Read repository AGENTS.md first, inspect
existing work, and preserve unrelated edits. Choose the lowest extension layer
that solves the task: Skill, Toolset, Plugin/Profile, then admitted Capability
or Core changes. Use repo tools for source and workspace tools for attachments
and artifacts. Locate and read the supplied Spec's authority before implementing.

Inspect archives before extraction: keep destinations under workspace, reject
absolute paths, `..` escapes and symlinks. Transport does not extract archives.

Use native tools for normal coding. Codex/Pi are optional configured Shell helpers;
verify their installation, inspect their diff and test their output yourself.
Never introduce a worker framework or new hash/manifest machinery without a
concrete requirement. Respect the repository's existing manifest contract.

Run targeted verification after meaningful changes, inspect the final diff and
report remaining unknowns. Local commits require the configured permission and
green relevant checks. Run the targeted pytest covering this change before any
local commit. Push/publish/restart/destructive host operations require
a separately approval-gated capability; stop if it is unavailable. Do not read
secrets through Shell or bypass denied paths. Source changes do not activate
already imported Gateway code: report restart required after terminal delivery.
