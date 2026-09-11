# 11 — Dependencies and Deployment

## Python baseline

Use repository Python baseline and normal `uv` workspace install flow.

Do not add runtime package installation from inside an agent tool.

## Candidate Python dependencies

Codex must minimize additions after checking what is already installed transitively.

Likely needs:

- `python-docx`
- `pypdf`
- `openpyxl`
- one selected PDF render/create library only if required
- Pillow for image normalization only if needed

Do not add `pandas` merely for spreadsheet file creation.

## Slides JavaScript dependencies

If PptxGenJS is selected:

- declare a reproducible Node dependency location owned by `zuaef-artifacts` or repository tooling;
- do not rely on globally installed npm packages;
- keep generated JS internal and static; do not execute model-generated JavaScript;
- provide one setup/check command in the implementation report.

Prefer a small package set.

## System dependencies

Expected supported production environment may include:

- LibreOffice headless;
- a PDF-to-image rendering tool/library;
- Node if PptxGenJS is selected.

Codex must not silently install system packages. Report missing packages and provide operator install commands appropriate for Debian/Ubuntu/Armbian only after detecting the target host.

## OrangePi / ARM64 lane

Treat the OrangePi deployment as a real target, not an afterthought.

Acceptance probe should print only factual availability:

- architecture;
- Python version;
- LibreOffice version/presence;
- Node version/presence;
- selected Python engine imports;
- selected renderer availability.

Do not require a GUI desktop session.

## Profile plan

Pilot first with a separate profile:

```text
general-knowledge-worker-artifacts
```

It should preserve the current General Knowledge Worker behavior and add only the new artifacts plugin.

After end-to-end acceptance, the product owner may decide whether to:

- replace the current General Knowledge Worker profile with this composition;
- keep both profiles;
- make it the default Feishu profile.

Do not make unrelated routing-profile changes in this task.

## Gateway deployment

For Feishu seamless delivery:

- enable generic auto-artifact delivery in the Feishu gateway deployment;
- preserve current file-size limit;
- restart the gateway after environment changes, consistent with existing operations behavior.

## Operational smoke commands

The final implementation report must provide exact commands for the local tree, including:

- workspace sync;
- plugin list/inspect;
- profile check;
- targeted tests;
- dependency probe;
- one CLI natural-language artifact run;
- one Feishu gateway restart/status command if that deployment is being promoted.

Do not place secrets in commands, profiles, test fixtures, or reports.
