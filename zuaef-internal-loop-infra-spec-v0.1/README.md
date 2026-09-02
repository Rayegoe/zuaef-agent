# ZUAEF Internal Supervisor Loop Infrastructure — Spec Pack v0.1

**Status:** READY TO FREEZE  
**Canonical engineering authority:** `SPEC.md`

This pack implements the minimum infrastructure for:

```text
Console / worker evidence
→ GitHub
→ ChatGPT Project Supervisor
→ control PR
→ human mobile merge
→ local fresh worker
→ report
→ GitHub
```

The operator can leave the office. The only intentional v0.1 human activation is opening the existing ChatGPT Project on phone/web and sending `继续` (or equivalent) after a new report arrives.

The control PR is then reviewed/merged from the phone; the local watcher automatically picks up the merged instruction.

## Files

- `SPEC.md` — canonical worker authority for infrastructure implementation.
- `ARCHITECTURE.md` — role/authority rationale.
- `PROTOCOL.md` — branch, report and instruction contracts.
- `ACCEPTANCE.md` — deterministic + live end-to-end gates.
- `OPERATIONS.md` — bootstrap, mobile use and recovery.
- `PROJECT_INSTRUCTION_AMENDMENT.md` — behavior to add to the Supervisor Project.
- `CODEX_WORKER_PROMPT.md` — fixed bounded local worker prompt.
- `IMPLEMENTATION_CHECKLIST.md` — implementation ordering only.
- `SOURCE_BASIS.md` — source facts and assumptions.

Supporting files do not expand `SPEC.md`.
