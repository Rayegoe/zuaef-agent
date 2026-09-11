# Follow-on: Supervisor Build Operator

Not part of General Knowledge Worker v0.1.

## Problem

Desired private workflow:

> I state a requirement → ZUAEF edits code → runs tests → deploys → reports evidence.

The field conversation showed why this must be a real deployment, not a verbal promise.

BMAD build Skills exist, but a Skill alone does not create:
- repository file authority
- shell authority
- deployment authority

## Recommended shape

Separate profile:
`supervisor-build`

Private/supervisor-only surface.

Potential composition:
- repository-scoped filesystem
- RepoContext
- Shell or isolated execution environment
- Planning
- BMAD Skills
- tests/lint
- explicit deployment toolset
- approval for production-changing deployment
- no quant trading-core privilege by default

## Why separate

General Knowledge Worker reads untrusted web/documents.

Build Operator executes code and changes systems.

Mixing those authority classes in one general Gateway bot creates unnecessary prompt-injection blast radius.

## Later design choice

A. reuse official Harness `Coder` in a dedicated deployment  
B. compose only the needed Coder blocks to avoid duplicate tools  
C. use a dedicated sandboxed execution plugin

Before implementation, run a tool-collision and approval-boundary proof against current ZUAEF core.

## Minimal acceptance

Prompt:
`把这个 bug 修好，跑测试，通过后部署到测试环境。`

Success must prove:
- repository changed
- tests ran
- test result
- deployment tool ran
- target environment
- final state

Anything less is incomplete and must never be described as deployed.
