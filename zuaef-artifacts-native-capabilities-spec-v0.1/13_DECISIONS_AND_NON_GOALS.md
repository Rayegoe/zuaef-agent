# 13 — Decisions and Non-Goals

## Frozen decisions

### D1 — One plugin, four capabilities

Reason: installation/version/composition is one product concern; each file format remains separately discoverable and independently testable.

### D2 — Natural language, no required format commands

Reason: ZUAEF is an outcome controller, not a command palette.

### D3 — Explicit format wins

Reason: a user-stated deliverable constraint is stronger evidence than inferred intent.

### D4 — Semantic discovery instead of hard-coded intent routing

Reason: phrasing diversity and multi-capability tasks make a keyword switch brittle and redundant with the model/tool-search architecture.

### D5 — Capability owns mechanical QA

Reason: save/render/reopen/check are deterministic sub-steps and should not create unnecessary model turns.

### D6 — Knowledge Worker reads; Artifacts produces

Reason: avoid duplicate document search/extraction implementations.

### D7 — No arbitrary shell

Reason: artifact creation does not justify granting a broad execution capability.

### D8 — Clean implementation, local OAI assets not shipped by default

Reason: production portability and license boundary.

### D9 — Pilot profile before promotion

Reason: prove product value and runtime cost without silently expanding every deployment.

### D10 — Feishu file loop first, native Feishu document objects later

Reason: the current surface already supports attachment intake and document sending, so standard files are enough to validate the business loop.

## Explicit non-goals for v0.1

- Full Microsoft Office feature parity.
- Full parity with the local OAI skill packages.
- Word tracked changes/comments/content controls.
- PDF OCR/forms/advanced redaction.
- Large slide template library.
- General-purpose visual design application.
- Spreadsheet macro support.
- `.xls` legacy binary editing unless an existing dependency already supports it safely.
- Native Google Docs/Sheets/Slides integration.
- Native Feishu Docs/Sheets creation/editing.
- New agent registry.
- New multi-agent topology.
- New workflow state machine.
- New artifact database.
- New generic shell surface.
- New vector store.
- Reworking StillWrite.

## Future candidates after v0.1 proves demand

Only admit from observed user need:

- richer DOCX review lifecycle;
- client-specific branded templates owned by ZUAEF/user;
- native Feishu document projection;
- visual-verifier capability for deployments with multimodal models;
- OCR/redaction flows;
- domain templates such as quotation, investment memo, operating review, customer proposal;
- artifact revision history surfaced as Case relations.
