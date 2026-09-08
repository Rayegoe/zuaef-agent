# 11 — Upstream Technical References

These are implementation references, not copied authority over the local repository. Always verify the API against the pinned installed minor before coding.

## PydanticAI Harness

Main repository:

https://github.com/pydantic/pydantic-ai-harness

Harness overview / capability matrix:

https://github.com/pydantic/pydantic-ai-harness/blob/main/README.md

Important current facts:
- `Coder` is a normal combined capability, not a second framework.
- `FileSystem`, `Shell`, `RepoContext`, Planning and context controls are composable blocks.
- `CodeMode` uses Monty sandboxed Python for programmatic tool calling.
- `ModalSandbox` exists for isolated cloud execution.
- Runtime Capability Creation exists for agent-authored capabilities.
- Harness is 0.x; minor releases may change APIs.

Coder reference:

https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/coder.md

Key lesson for ZUAEF:
- use the blown-out building blocks because ZUAEF already composes several Coder components.

## PydanticAI Capabilities

Capabilities overview:

https://ai.pydantic.dev/capabilities/

PrefixTools:

https://ai.pydantic.dev/capabilities/prefix-tools/

Key fact:
- `PrefixTools` wraps another capability and prefixes its tool names.
- This is the correct upstream mechanism for a second repo-scoped FileSystem/Shell surface.

Tool approval / deferred tools:

https://ai.pydantic.dev/deferred-tools/

Toolsets / ApprovalRequiredToolset:

https://ai.pydantic.dev/toolsets/

## Runtime Capability Creation

Current upstream source/docs:

https://github.com/pydantic/pydantic-ai-harness/tree/main/pydantic_ai_harness/capability_creation

Key facts:
- Agent can author, validate and persist a PydanticAI capability.
- Activation occurs on the next run.
- The orchestrator must thread active authored capabilities into each run.
- Arbitrary authored Python shares the trust boundary of shell/code execution.

v0.1 decision:
- do not depend on it until ZUAEF's frozen resume/composition semantics can include it without drift.

## Feishu / Lark Channel SDK

Standalone SDK:

https://github.com/larksuite/channel-sdk-python

PyPI:

https://pypi.org/project/lark-channel-sdk/

Current repository pin reviewed: `lark-channel-sdk==1.4.0`.

Important Channel SDK facts:
- normalized inbound messages expose resources;
- media/resource download helpers exist;
- `download_resource(...)` returns bytes;
- `download_resource_to_file(...)` saves a resource to disk;
- use Channel SDK public APIs rather than implementing raw OpenAPI transport.

Legacy-but-detailed Channel reference that documents the same high-level API surface:

https://github.com/larksuite/oapi-sdk-python/blob/v2_main/doc/channel/reference.md

Resource API model:
- message id + file key identify downloadable message resources.

## Local ZUAEF authorities

Always read live versions before editing:

```text
AGENTS.md
src/zuaef_agent/core.py
src/zuaef_agent/config.py
src/zuaef_agent/profiles.py
src/zuaef_agent/plugin_api.py
src/zuaef_agent/composition.py
src/zuaef_agent/gateway/models.py
src/zuaef_agent/gateway/feishu.py
src/zuaef_agent/gateway/bridge.py
src/zuaef_agent/gateway/routing.py
src/zuaef_agent/gateway/runner.py
```

GitHub repository:

https://github.com/Rayegoe/zuaef-agent
