# UPSTREAM BASELINE — Capability-Complete Release Policy v2.1

Inspection anchor: 2026-08-19

The platform target is a broad generalist capability surface backed by released upstream public APIs.

---

# 1. Release rule

Select a tested released PydanticAI + Pydantic AI Harness pair.

Do not make production depend on upstream `main`.

Use `uv.lock` as the exact execution baseline.

---

# 2. Capability matrix to probe

The coding agent must probe the selected release for:

| Primitive | Platform baseline |
|---|---:|
| Agent / Toolsets / Capability APIs | REQUIRED |
| deferred tools / approval | REQUIRED |
| message history | REQUIRED |
| official provider path | REQUIRED |
| FileSystem | REQUIRED |
| Shell | REQUIRED |
| RepoContext | REQUIRED |
| Planning | REQUIRED |
| Skills | REQUIRED |
| ToolOutputLimits | REQUIRED |
| StepPersistence | REQUIRED |
| public StepStore/equivalent | REQUIRED |
| WebSearch | REQUIRED |
| WebFetch | REQUIRED |
| ToolSearch / on-demand loading | REQUIRED |
| context controls / compaction | REQUIRED |
| Memory | REQUIRED |
| ConversationSearch | REQUIRED |
| SubAgents | REQUIRED |
| Coder combined stack | OPTIONAL |
| Researcher combined stack | OPTIONAL |
| CodeMode | OPTIONAL / deployment-specific |
| Browser | OPTIONAL / deployment-specific |

For each REQUIRED item mark:

```text
READY
or
RELEASE GAP
```

A release gap is acceptable only as a documented upstream-version limitation, not as a reason to silently create a ZUAEF replacement.

---

# 3. Availability vs activation

The release probe answers:

```text
Can the platform provide this capability?
```

Runtime policy answers:

```text
Should this deployment expose it?
Should the model load it now?
Should the model invoke it now?
```

Never conflate these questions.

---

# 4. Progressive disclosure

Prefer upstream mechanisms that support:

```text
compact catalog
deferred capability/tool definitions
ToolSearch
selective activation
```

This is a core architectural requirement for a growing multi-domain FDE platform.

---

# 5. Memory boundary

Harness Memory is generic persistent model memory.

ConversationSearch retrieves prior conversation material.

Neither replaces:

```text
Case
Evidence-backed Knowledge
RunReceipt
```

---

# 6. SubAgent boundary

SubAgent capability should be available when released/stable.

It must not redefine the topology into a multi-agent platform.

Default:

```text
one FDE Agent owns the user outcome
```

SubAgent is an execution primitive selected only when useful.

---

# 7. Main-only features

If an important baseline capability is only on upstream main:

1. confirm there is no released equivalent;
2. record `RELEASE GAP`;
3. prefer waiting for release or using a lower-level released public primitive;
4. do not vendor for convenience;
5. vendor only if the capability is product-blocking and the user explicitly approves.

---

# 8. Provider rule

Use official providers/profiles for generic model compatibility.

Keep local code only for actual deployment-specific transport/configuration.

---

# 9. Persistence rule

Use public Harness persistence APIs.

Private backend filenames are not stable contracts.

---

# 10. Stop rule

Once the released baseline is ready, progressive disclosure works, continuity works, and the real FDE case passes:

```text
STOP general harness work.
```

Future changes should primarily extend business-domain capabilities and skills.
