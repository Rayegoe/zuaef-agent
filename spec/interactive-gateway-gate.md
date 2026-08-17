# Interactive Business Gateway — Gate Record (SPEC v0.3 §85)

```yaml
date: 2026-08-16T21:56:00Z
commit: 9014e25dd633a4b8fdba04817ba29050cd301dd7  # HEAD; gateway work is uncommitted on top
model: deepseek-v4-flash
surface: telegram
profile: wordpress-operator
plugin: zuaef-wordpress
plugin_version: 0.1.0

initial_run: 9cedcc018ce845f9b592f3990f33d382      # paused run: wordpress_publish_post(post_id=52)
pause_receipt: 9cedcc018ce845f9b592f3990f33d382.json
conversation_id: 91870c40234c4e9fa5084fa7687d707b
composition_id: 81b34fc8abd949719674784ef0c91b7dd017e6d7329384b7556061ae5bf4013b

approval: approved                                  # opaque token consumed by the operator in Telegram
continuation_run: 6dbbb41d1c114128a735503ace0c84c7

wordpress_post_id: 52
wordpress_before_status: draft
wordpress_after_status: publish                     # verified via WordPress REST API

verified_effect: wordpress_publish_post completed   # in continuation RunReceipt.verified_tool_effects
terminal_status: partial                            # see degraded note below

tests: 302 passed                                   # uv run pytest -q
ruff: All checks passed                             # uv run ruff check .
manifest: green                                     # uv run python tools/regen_manifest.py
```

## Gates

```yaml
GW-1:  PASS   # real Telegram message → gateway (first message produced a real completed run e1a45609acf54cca86e07fadb578e722)
GW-2:  PASS   # task composed through build_profile_agent with the real zuaef.plugins wordpress entry point
GW-3:  PASS   # task executed through execute_run()
GW-4:  PASS   # wordpress_publish_post produced a real PausedRun + PauseReceipt (9cedcc01…)
GW-5:  PASS   # Telegram showed the approval card; operator tapped Approve
GW-6:  PASS   # forged/foreign/duplicate token rejection proven by tests; real token consumed exactly once
GW-7:  PASS   # approve resumed via shared resume_paused_run with restored StepPersistence history
GW-8:  PASS   # continuation composition_id == PauseReceipt composition_id (81b34fc8…)
GW-9:  PASS   # real WordPress draft 52 changed to publish on https://dynoedge.com
GW-10: PASS   # verified_tool_effects contains wordpress_publish_post completed
GW-11: PASS   # all pre-existing tests green (no xfail/skip/relaxation)
GW-12: PASS   # no Gateway Agent / ApprovalEngine / GatewayReceipt / WorkflowRuntime / EventBus
```

## Real-run degraded note (recorded, not hidden)

The continuation receipt is `partial`, not `completed`: the model cited
`tool-effect:<tool_call_id>` with a tool_call_id that is not in the host's
effect ledger (tool_call_ids are host-opaque; the model guessed one). The
host verified the effect itself from the ledger — `wordpress_publish_post
completed` IS in `verified_tool_effects` — and degraded the model's
unverifiable claim. This is the designed behavior (model claims are
proposals; the host owns verification), not an architecture failure.

## Proven vertical slice (real systems)

```text
Telegram (phone)
  → "Publish WordPress draft 52."
  → GatewayService → wordpress-operator profile → build_profile_agent
  → execute_run() → model proposes wordpress_publish_post(52)
  → PydanticAI native approval → PausedRun 9cedcc01… + PauseReceipt
  → Telegram approval card → operator taps Approve
  → opaque token consumed → resume_paused_run (frozen composition 81b34fc8…)
  → WordPress REST write → post 52 draft → publish
  → host verification → RunReceipt 6dbbb41d… (continued_from 9cedcc01…)
```

Incidental evidence: the first real message ("hi") produced a real completed
run `e1a45609acf54cca86e07fadb578e722` through the same path (no approval
required for a read-only interaction).
