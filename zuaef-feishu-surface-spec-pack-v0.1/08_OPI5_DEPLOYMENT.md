# 08 — OPi5 Deployment

## Principle

The OPi5 already hosts zuaef-agent runtime.

Therefore:
> extend the existing runtime/gateway before creating another daemon.

## 1. Preflight

Run on OPi5:

```bash
whoami
hostname
pwd
git status --short --branch
git rev-parse HEAD
python3 --version
uv --version
systemctl --user --type=service --all | grep -i zuaef || true
systemctl --user --type=timer --all | grep -i zuaef || true
```

Record the real paths/unit names.

Do not assume `/home/orangepi/zuaef-agent` even if that is likely.

## 2. Dependency

Pin in owning package:

```text
lark-channel-sdk==1.4.0
```

Then use the repo's normal uv lock/update procedure.

Do not globally `pip install` into a different Python than the runtime service.

## 3. Environment file

Example location:

```text
~/.config/zuaef/feishu.env
```

Contents:

```bash
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=...
FEISHU_GROUP_ALLOWLIST=oc_xxx,oc_yyy
FEISHU_USER_ALLOWLIST=ou_xxx
```

Permissions:

```bash
mkdir -p ~/.config/zuaef
chmod 700 ~/.config/zuaef
chmod 600 ~/.config/zuaef/feishu.env
```

## 4. Service integration priority

### Preferred
Existing runtime/gateway unit already owns surfaces.

Add:
```ini
EnvironmentFile=%h/.config/zuaef/feishu.env
```

and register Feishu surface in the same process.

### Second choice
Existing generic surface/gateway host is a separate unit.

Register Feishu there.

### Last resort
If no generic persistent surface host exists, add a dedicated Feishu gateway process
that imports/calls the same zuaef-agent runtime composition.

It may own transport, but must not own a second agent core.

Conceptual service only:

```ini
[Unit]
Description=ZUAEF Feishu Surface
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=<ACTUAL_REPO>
EnvironmentFile=%h/.config/zuaef/feishu.env
ExecStart=<ACTUAL_UV_PATH> run <ACTUAL_FEISHU_GATEWAY_ENTRYPOINT>
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

Use actual local paths discovered at P0.

## 5. Single active worker

Do not run:
- one manually in shell;
- and one under systemd;
- or two systemd instances

for the same Feishu App.

Before canary:

```bash
ps aux | grep -i feishu
systemctl --user status <unit>
```

## 6. Logs

```bash
journalctl --user -u <unit> -n 100 --no-pager
journalctl --user -u <unit> -f
```

Expected healthy sequence:
```text
surface=feishu connecting
surface=feishu ready
...
surface=feishu reconnecting
surface=feishu reconnected
```

Exact formatting should follow existing structured logging.

## 7. Canary order

1. transport connection;
2. allowed group @mention;
3. generic `general`/research response;
4. profile switch;
5. file send;
6. approval card;
7. Quant allowed group;
8. Quant DM rejection;
9. service restart;
10. regression suite.

Do not start acceptance with Quant; prove the Surface is generic first.
