# Operations

## Normal remote operation

```text
worker finishes
→ automatic report push
→ phone: "继续"
→ Supervisor decision
→ if control PR exists: review/merge on phone
→ office timer detects merge
→ fresh worker executes
→ automatic report push
```

No office terminal interaction is required in the normal path.

## Bootstrap

Conceptual:

```bash
uv run python tools/supervisor_loop.py bootstrap
```

It should ensure:

- `supervisor-report`;
- `supervisor-control`;
- dedicated local worktrees;
- local state directory.

It must not modify `main` or start a worker.

## Polling

Install a user-level timer:

```bash
mkdir -p ~/.config/systemd/user
cp ops/systemd/zuaef-supervisor-sync.* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now zuaef-supervisor-sync.timer
```

Each service invocation performs one poll and exits.

## Local roots

```text
/home/barry/zuaef-agent
~/.local/share/zuaef-supervisor/report
~/.local/share/zuaef-supervisor/control
~/.local/share/zuaef-supervisor/workers/<control-sha>/
~/.local/state/zuaef-supervisor/
```

## Recovery

Report push fails:
- preserve local outbox;
- human may retry transport.

Control fetch fails:
- next mechanical poll may fetch again;
- never execute from stale data.

Worker crashes:
- do not silently rerun the same instruction;
- Supervisor/human decides.

Bad control PR:
- do not merge;
- request `REVISE`.

Merged instruction must be stopped before pickup:

```bash
systemctl --user stop zuaef-supervisor-sync.timer
```

## Disable

```bash
systemctl --user disable --now zuaef-supervisor-sync.timer
```

Production ZUAEF and Console must remain functional when this infrastructure is disabled.

## Public repo scope

Current bus is public-safe engineering evidence only.

Never auto-publish secrets, `.env`, customer data, private corpora, private business docs or arbitrary home-directory content.
