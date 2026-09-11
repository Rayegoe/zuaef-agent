# Patch Map

## New

- `profiles/general-knowledge-worker.toml`
- `plugins/zuaef-knowledge-worker/pyproject.toml`
- `plugins/zuaef-knowledge-worker/zuaef_knowledge_worker/__init__.py`
- `plugins/zuaef-knowledge-worker/zuaef_knowledge_worker/plugin.py`
- `plugins/zuaef-knowledge-worker/zuaef_knowledge_worker/document_tools.py`
- `plugins/zuaef-knowledge-worker/zuaef_knowledge_worker/skills/knowledge-worker/SKILL.md`
- focused profile/plugin/document tests
- one end-to-end proof

## Root project change

Root `pyproject.toml`:
- add `zuaef-knowledge-worker` project dependency
- add `[tool.uv.sources]` entry

Workspace glob already includes `plugins/*`; do not invent another workspace mechanism.

## Do not change

- global generalist flag tuple
- plugin API shape
- approval subsystem
- receipt architecture
- existing vertical profiles except independently justified compatibility fixes

## Optional host enhancement

If needed after proof:
- project structured web source metadata into presentation/receipt output

Do not make this a prerequisite for the first vertical slice if source URLs are already preserved reliably.
