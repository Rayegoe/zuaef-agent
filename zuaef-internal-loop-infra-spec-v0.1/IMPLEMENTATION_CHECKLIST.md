# Implementation Checklist

This checklist does not expand `SPEC.md`.

## Authority/docs
- [ ] read live `AGENTS.md`
- [ ] add only internal-loop authority amendment
- [ ] add `docs/internal-loop/README.md`
- [ ] add fixed worker prompt

## Transport
- [ ] implement `tools/supervisor_loop.py`
- [ ] `bootstrap`
- [ ] `publish-report`
- [ ] `sync-control`
- [ ] `run-next`
- [ ] dedicated report/control worktrees
- [ ] exact-base fresh worker worktree
- [ ] one process lock
- [ ] one `last-started-control`
- [ ] `CONTROL_GAP`
- [ ] primary worktree untouched

## Worker adapter
- [ ] inspect installed Codex CLI
- [ ] use current supported non-interactive invocation
- [ ] pass fixed worker prompt + exact NEXT
- [ ] capture exit mechanically
- [ ] publish report after exit
- [ ] missing report → mechanical failure report only

## Polling
- [ ] user-level systemd service
- [ ] 60-second timer
- [ ] one poll per service invocation
- [ ] no inbound listener

## Tests
- [ ] dirty primary isolation
- [ ] report publication
- [ ] patch evidence
- [ ] unchanged control no-op
- [ ] new control one launch
- [ ] duplicate poll no duplicate
- [ ] missing base stop
- [ ] control gap stop
- [ ] missing worker report
- [ ] no automatic main mutation

## Live
- [ ] bootstrap two branches
- [ ] install timer
- [ ] add Project instruction amendment
- [ ] pass phone→Project→PR→phone merge→office worker→report canary

## Finish
- [ ] record evidence
- [ ] STOP
