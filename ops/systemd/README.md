# ZUAEF systemd package — Orange Pi Production Node v1 (Linux aarch64)

User-level units for the Orange Pi 5 Pro node. Source of truth for the runtime;
`ops/install_orangepi_node.sh` installs exactly this set into
`~/.config/systemd/user/`.

## Units

| unit | type | runs |
|---|---|---|
| `zuaef-console.service` | simple | Agent Console — `.venv/bin/zuaef-agent web` on 127.0.0.1:8765 |
| `zuaef-gateway.service` | simple | Telegram gateway — `gateway start --surface telegram --profile quant-decision` |
| `zuaef-quant-dashboard.service` | simple | Quant Workbench — `.venv/bin/python tools/quant_serve.py` on 127.0.0.1:8787 |
| `zuaef-quant-monitor.service` + `.timer` | simple + timer | M1 live monitor, sessions Mon–Fri 09:30 / 13:00, `--exit-on-close` |
| `zuaef-quant-bridge.service` + `.timer` | oneshot + timer | event bridge every 45 s |

Paths use `%h/zuaef-agent` (repo expected at `$HOME/zuaef-agent`). The installer
rewrites `%h/zuaef-agent` to the real repo path when it lives elsewhere.

## Manual install (without the installer)

```bash
mkdir -p ~/.config/systemd/user
install -m 0644 ops/systemd/zuaef-*.service ops/systemd/zuaef-*.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now \
  zuaef-console.service zuaef-quant-dashboard.service zuaef-gateway.service
systemctl --user enable --now zuaef-quant-bridge.timer zuaef-quant-monitor.timer
sudo loginctl enable-linger "$USER"   # services survive logout
```

## Proxy (optional)

If api.telegram.org is not directly reachable, add a drop-in instead of
editing the units:

```bash
mkdir -p ~/.config/systemd/user/zuaef-gateway.service.d
printf '[Service]\nEnvironment=HTTPS_PROXY=http://127.0.0.1:7897\nEnvironment=HTTP_PROXY=http://127.0.0.1:7897\n' \
  > ~/.config/systemd/user/zuaef-gateway.service.d/proxy.conf
# same for zuaef-quant-bridge.service.d if the bridge needs it
systemctl --user daemon-reload
```

`ZUAEF_PROXY` passed to the installer writes these drop-ins automatically.

## What is deliberately NOT here

- `zuaef-supervisor-sync.{service,timer}` — x86-host artifacts with a hardcoded
  codex-x64 binary path; not part of the ARM node package.
- `quant_daily.sh` — superseded by M1 monitor + bridge; scheduling it again
  would create two competing decision paths.