# Source Basis

## Project policy

Derived from the installed ZUAEF Internal Supervisor sources:

- `00_SYSTEM.md`
- `01_PROJECT_INSTRUCTIONS.md`
- `02_SUPERVISOR.md`
- `03_HANDOFF.md`
- `04_AGENTS_INVARIANTS.md`
- `05_RUNTIME_COACH_CORE.md`
- `06_RUNTIME_REFOUNDATION_INVARIANTS.md`
- `07_ANALYSIS_CONTRACT.md`

Carried-forward doctrine:

- Project = Supervisor Plane.
- GitHub = current facts/handoff.
- Worker = bounded execution.
- Console/Run Analysis = observation.
- queued task != execution authority.
- one causal mechanism per normal iteration.
- no speculative schema/gate/state/memory/framework.
- history != default state.
- semantic decisions remain model-owned.

## Live repository basis

At spec preparation:

```text
Rayegoe/zuaef-agent
main = 1b0e46bbf5e67de00a194c3e5b68638b230434f7
```

Observed:

- current `AGENTS.md` still has legacy "identify next unfinished TASKS item" runtime-refoundation routing;
- current Project policy narrows that for Supervisor-launched workers;
- current Run Analysis already satisfies Observation Plane separation;
- `main` is unprotected at the inspected baseline;
- repository is public;
- local work has already encountered concurrent unrelated uncommitted edits.

## OpenAI product facts verified 2026-08-24

Projects can be continued across devices, including phone and web:

https://help.openai.com/en/articles/10169521-projects-in-chatgpt

The standard documented GitHub app can read live repository data; the public help article describes the standard app as read-only for repository writes:

https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt

In the specific Supervisor environment used to prepare this pack, the connected GitHub tool exposed branch/file/PR/merge write actions and the target repository connection reported push/admin permissions.

That target-environment write capability must be proven again in the live mobile canary. It is not treated as a universal promise of the standard GitHub app.

v0.1 does not assume a GitHub push can autonomously wake this exact Project conversation.
