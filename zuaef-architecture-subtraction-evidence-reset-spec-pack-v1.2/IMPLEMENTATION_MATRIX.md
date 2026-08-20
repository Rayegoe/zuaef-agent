# IMPLEMENTATION MATRIX

| Area | Current | Target | Action |
|---|---|---|---|
| Agent loop | PydanticAI | PydanticAI | KEEP |
| Plugin entry points | `zuaef.plugins` | same | FREEZE |
| PluginBundle | tools/skills/capabilities | same | FREEZE |
| CompositionSnapshot | exact plugin composition | same | KEEP |
| StepPersistence | upstream Harness | same | KEEP |
| Approval | native PydanticAI | same | KEEP |
| `case_id` | CoreDeps/receipt/runtime | opaque bindings | REPLACE |
| Case context | generic host projection | Case capability | MOVE |
| Cross-case pending check | runtime | Case tool validator | MOVE |
| `verification.py` | integrity + semantic evidence | integrity only | SHRINK/RENAME |
| `verified_artifacts` | semantic-sounding | artifact facts or remove | RENAME/DELETE |
| `verified_knowledge` | semantic-sounding | remove | DELETE |
| evidence refs | hard-coded prefixes | citations in artifact | DELETE |
| knowledge type ontology | global hard-coded types | document-first | DELETE/SIMPLIFY |
| Generalist flags | growing registry | closed compatibility surface | FREEZE |
| Editorial sensors/actions | treated as evidence | derived diagnostics only | DEMOTE |
| Human feedback | compressed to fields | preserved natural artifact | PROMOTE |
| Source URLs | curated metadata | visible in result + review | PROMOTE |
| Quality acceptance | machine fields/sensors | LLM + human review | REPLACE |

## Result ownership matrix

| Domain | Result contract owner | Kernel involvement |
|---|---|---|
| Writing/article | Writing Capability/plugin | none beyond execution |
| Research/report | Research Capability/plugin | none beyond execution |
| Budget analysis | Budget Capability/plugin | none beyond execution |
| Client reply/negotiation | Client-service/negotiation Capability/plugin | none beyond execution |
| WordPress post mutation | WordPress plugin/tool contract | approval + execution only |

**Invariant:** adding a new row must not require a new Kernel result field.
