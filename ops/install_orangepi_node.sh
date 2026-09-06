#!/usr/bin/env bash
#
# install_orangepi_node.sh — Orange Pi 5 Pro (Linux aarch64) ZUAEF Production Node v1
#
# One-shot, idempotent bootstrap per the repo's REAL structure (main):
#   1. system prereqs          (apt, timezone Asia/Shanghai)
#   2. uv                       -> Astral standalone installer
#   3. .venv  (Agent env)       -> uv sync --frozen --group quant --python 3.12
#   4. .venv-quant (quant env)  -> conda-forge ARM64 prefix (reuses existing conda
#                                  unless --miniforge), akshare==1.18.94,
#                                  Qlib v0.9.7 compiled from source -> ARM64 wheel
#   5. profiles + .env          -> ~/.config/zuaef/profiles, repo .env with
#                                  ZUAEF_QUANT_PYTHON / ZUAEF_QUANT_REPO_ROOT
#   6. systemd package          -> ops/systemd/* installed to ~/.config/systemd/user
#
# State layout (real): data/quant-cache/ (candidate cache), workspace/artifacts/quant/
# (trading facts), .zuaef-state/quant-bridge/ (bridge cursor). .venv* never migrated.
#
# Hard gates: aarch64 machine (preflight), qlib==0.9.7, and rolling/expanding
# import (the ARM64 compile). file(1) architecture output is diagnostics only,
# not a gate.
#
# Usage:
#   bash ops/install_orangepi_node.sh [--skip-apt] [--skip-timezone]
#                                     [--miniforge] [--no-systemd] [--no-linger]
#                                     [--smoke] [--help]
#
# Env knobs (all optional):
#   ZUAEF_REPO_ROOT          repo location (default: parent of this script)
#   ZUAEF_PYTHON             python major.minor for BOTH envs (default 3.12)
#   ZUAEF_MINIFORGE_PREFIX   miniforge install root (default ~/miniforge3)
#   ZUAEF_QLIB_SRC           qlib source checkout path (default /tmp/qlib-v0.9.7)
#   ZUAEF_PROXY              e.g. http://127.0.0.1:7897 -> systemd drop-in
#                            HTTPS_PROXY/HTTP_PROXY for gateway + bridge units
#   TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID ZUAEF_TELEGRAM_ALLOWED_USERS
#   ZUAEF_MODEL ZUAEF_OPENAI_BASE_URL ZUAEF_OPENAI_API_KEY ZUAEF_COMPAT_MODEL
#                            -> appended to repo .env when set (never overrides)
#
set -euo pipefail

REPO_ROOT="${ZUAEF_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ZUAEF_PYTHON="${ZUAEF_PYTHON:-3.12}"
QLIB_TAG="v0.9.7"
QLIB_VER="${QLIB_TAG#v}"   # qlib.__version__ = "0.9.7" (no v prefix)
QLIB_SRC="${ZUAEF_QLIB_SRC:-/tmp/qlib-${QLIB_TAG}}"
MINIFORGE_PREFIX="${ZUAEF_MINIFORGE_PREFIX:-$HOME/miniforge3}"
MINIFORGE_SH="${ZUAEF_MINIFORGE_SH:-/tmp/Miniforge3-Linux-aarch64.sh}"
AKSHARE_VER="1.18.94"
TELEGRAM_KEYS="TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID ZUAEF_TELEGRAM_ALLOWED_USERS"
MODEL_KEYS="ZUAEF_MODEL ZUAEF_OPENAI_BASE_URL ZUAEF_OPENAI_API_KEY ZUAEF_COMPAT_MODEL"

SKIP_APT=0; SKIP_TZ=0; FORCE_MINIFORGE=0; NO_SYSTEMD=0; NO_LINGER=0; SMOKE=0

usage() {
  sed -n '2,28p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-apt) SKIP_APT=1 ;;
    --skip-timezone) SKIP_TZ=1 ;;
    --miniforge) FORCE_MINIFORGE=1 ;;
    --no-systemd) NO_SYSTEMD=1 ;;
    --no-linger) NO_LINGER=1 ;;
    --smoke) SMOKE=1 ;;
    --help|-h) usage ;;
    *) echo "unknown option: $1" >&2; usage ;;
  esac
  shift
done

say()  { printf '\n== [%s] %s ==\n' "$1" "$2"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

append_if_absent() { # key value file
  local k="$1" v="$2" f="$3"
  grep -qxF "$k=$v" "$f" 2>/dev/null || \
    { printf '%s=%s\n' "$k" "$v" >> "$f"; echo "  .env += $k"; }
}

dotenv_passthrough() { # keys... -> .env (only when exported, never override)
  local f="$ENV_FILE" k
  for k in "$@"; do
    if [[ -n "${!k:-}" ]] && ! grep -q "^${k}=" "$f" 2>/dev/null; then
      printf '%s=%s\n' "$k" "${!k}" >> "$f"
      echo "  .env += $k (from environment)"
    fi
  done
}

# ───────────────────────────── preflight ─────────────────────────────────────
say "preflight" "target checks"
[[ "$(uname -m)" == "aarch64" ]] || die "machine=$(uname -m) — this script requires 64-bit aarch64 (armv7l is NOT supported)"
echo "machine  = $(uname -m)"
echo "glibc    = $(getconf GNU_LIBC_VERSION 2>/dev/null || echo unknown)"
[[ -d "$REPO_ROOT/.git" ]] || die "$REPO_ROOT is not a zuaef-agent checkout"
BRANCH="$(git -C "$REPO_ROOT" branch --show-current)"
echo "repo     = $REPO_ROOT (branch: ${BRANCH:-detached})"
[[ "$BRANCH" == "main" ]] || warn "branch is '$BRANCH', not main"
DIRTY="$(git -C "$REPO_ROOT" status --porcelain | wc -l)"
[[ "$DIRTY" -eq 0 ]] || warn "repo has $DIRTY uncommitted file(s) — installer only touches runtime dirs"
FREE_MB=$(( $(df -Pk "$REPO_ROOT" | awk 'NR==2 {print $4}') / 1024 ))
echo "disk free on repo root = ${FREE_MB} MB"
[[ "$FREE_MB" -ge 8192 ]] || warn "less than 8 GB free — conda env + wheels may not fit"

# ───────────────────────────── 1. system packages ────────────────────────────
if [[ "$SKIP_APT" -eq 0 ]]; then
  say "1/12" "system packages (apt)"
  sudo apt-get update -qq
  sudo apt-get install -y \
    git curl wget ca-certificates rsync jq unzip \
    build-essential gcc g++ make cmake pkg-config gfortran \
    python3-dev libgomp1 libopenblas-dev liblapack-dev \
    libssl-dev libffi-dev sqlite3 htop tmux
fi

# ───────────────────────────── 2. timezone ───────────────────────────────────
if [[ "$SKIP_TZ" -eq 0 ]]; then
  say "2/12" "timezone Asia/Shanghai + NTP"
  sudo timedatectl set-timezone Asia/Shanghai || warn "set-timezone failed (container?)"
  sudo timedatectl set-ntp true || warn "set-ntp failed"
  timedatectl | sed -n '1,4p'
fi

# ───────────────────────────── 3. uv ─────────────────────────────────────────
if ! command -v uv >/dev/null 2>&1; then
  say "3/12" "install uv (Astral standalone installer)"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  grep -q 'HOME/.local/bin' "$HOME/.bashrc" 2>/dev/null || \
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
fi
export PATH="$HOME/.local/bin:$PATH"
echo "uv = $(uv --version)"

# ───────────────────────────── 4. Agent main env ─────────────────────────────
say "4/12" "uv sync Agent env (.venv, python ${ZUAEF_PYTHON}, --group quant)"
( cd "$REPO_ROOT" && uv sync --frozen --group quant --python "$ZUAEF_PYTHON" )
( cd "$REPO_ROOT" && .venv/bin/python --version )
( cd "$REPO_ROOT" && .venv/bin/zuaef-agent --help >/dev/null ) || die "zuaef-agent CLI failed"
( cd "$REPO_ROOT" && .venv/bin/zuaef-agent plugin list 2>&1 | grep -qiE 'quant|telegram' ) \
  && echo "plugin list shows quant/telegram" || warn "plugin list did not show quant/telegram"

# ───────────────────────────── 5. quant conda env ────────────────────────────
say "5/12" "quant runtime conda (.venv-quant, python ${ZUAEF_PYTHON}, conda-forge)"
# Runtime probe: reuse an existing conda (incl. ~/miniconda3 when PATH misses
# it in a non-interactive shell); only when none exists install Miniforge3.
CONDA_BIN="$(command -v conda 2>/dev/null || true)"
if [[ -z "$CONDA_BIN" && -x "$HOME/miniconda3/bin/conda" ]]; then
  CONDA_BIN="$HOME/miniconda3/bin/conda"
fi
if [[ -z "$CONDA_BIN" && -x "$HOME/miniforge3/bin/conda" ]]; then
  CONDA_BIN="$HOME/miniforge3/bin/conda"
fi
if [[ -n "$CONDA_BIN" && "$FORCE_MINIFORGE" -eq 0 ]]; then
  echo "reusing existing conda: $CONDA_BIN"
else
  if [[ ! -x "$MINIFORGE_PREFIX/bin/conda" ]]; then
    echo "installing Miniforge3 (aarch64) -> $MINIFORGE_PREFIX"
    [[ -f "$MINIFORGE_SH" ]] || \
      curl -L -o "$MINIFORGE_SH" \
        https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh
    bash "$MINIFORGE_SH" -b -p "$MINIFORGE_PREFIX"
  fi
  CONDA_BIN="$MINIFORGE_PREFIX/bin/conda"
fi
"$CONDA_BIN" --version

if [[ ! -x "$REPO_ROOT/.venv-quant/bin/python" ]]; then
  # conda-forge solve failure = explicit failure (set -e); no pip fallback.
  # NB: `build` is a pip package (not on conda-forge); step 7 pip-installs it
  # into the env before `python -m build`.
  "$CONDA_BIN" create -y -p "$REPO_ROOT/.venv-quant" \
    --override-channels -c conda-forge \
    python="$ZUAEF_PYTHON" pip \
    "numpy=1.26.*" "pandas=2.2.*" scipy scikit-learn \
    cython setuptools wheel packaging \
    lightgbm pyarrow cvxpy
fi
QP="$REPO_ROOT/.venv-quant/bin/python"
"$QP" --version

# ───────────────────────────── 6. akshare ────────────────────────────────────
say "6/12" "akshare==${AKSHARE_VER} into .venv-quant"
"$QP" -m pip install --quiet "akshare==$AKSHARE_VER"
"$QP" - "$AKSHARE_VER" <<'PY'
import sys, akshare, platform
assert akshare.__version__ == sys.argv[1], (akshare.__version__, sys.argv[1])
print("machine =", platform.machine())
print("akshare =", akshare.__version__)
PY

# ───────────────────────────── 7. Qlib ARM64 build ───────────────────────────
say "7/12" "build Qlib ${QLIB_TAG} from source -> ARM64 wheel"
if ! git -C "$QLIB_SRC" describe --tags 2>/dev/null | grep -qx "$QLIB_TAG"; then
  rm -rf "$QLIB_SRC"
  # GitHub is intermittently flaky on this network (observed GnuTLS -110);
  # retry a few times before failing explicitly.
  for attempt in 1 2 3; do
    echo "qlib clone attempt $attempt/3"
    if git clone --branch "$QLIB_TAG" --depth 1 https://github.com/microsoft/qlib.git "$QLIB_SRC"; then
      break
    fi
    sleep 5
  done
  git -C "$QLIB_SRC" describe --tags 2>/dev/null | grep -qx "$QLIB_TAG" \
    || die "qlib clone failed after retries ($QLIB_SRC)"
fi
( cd "$QLIB_SRC" \
    && "$QP" -m pip install --quiet build wheel setuptools cython \
    && "$QP" -m build --wheel --no-isolation )
WHEEL="$(ls -1 "$QLIB_SRC"/dist/pyqlib-0.9.7-*.whl 2>/dev/null | head -1 || true)"
[[ -n "$WHEEL" ]] || die "no wheel produced under $QLIB_SRC/dist"
mkdir -p "$REPO_ROOT/.arm-wheels"
cp "$WHEEL" "$REPO_ROOT/.arm-wheels/"
echo "saved wheel -> $REPO_ROOT/.arm-wheels/$(basename "$WHEEL")"
"$QP" -m pip install --quiet "$REPO_ROOT"/.arm-wheels/pyqlib-*.whl

# ───────────────────────────── 8. Qlib native gate ───────────────────────────
say "8/12" "verify Qlib is native ARM64 (hard gate)"
"$QP" - "$QLIB_VER" <<'PY'
import sys, platform, qlib
assert platform.machine() == "aarch64", "not aarch64"
assert qlib.__version__ == sys.argv[1], (qlib.__version__, sys.argv[1])
from qlib.data._libs import rolling, expanding   # import must succeed
print("qlib      =", qlib.__version__)
print("rolling   =", rolling.__file__)
print("expanding =", expanding.__file__)
PY
ROLLING_SO="$("$QP" -c 'from qlib.data._libs import rolling; print(rolling.__file__)')"
echo "file(1) diagnostics (informational):"
file "$ROLLING_SO"
"$QP" -m pip check

# ───────────────────────────── 9. profiles ───────────────────────────────────
say "9/12" "profiles -> ~/.config/zuaef/profiles"
mkdir -p "$HOME/.config/zuaef/profiles"
# Overwrite semantics per review decision: plain cp -f, no cp -u, no backup/merge.
cp -f "$REPO_ROOT"/profiles/*.toml "$HOME/.config/zuaef/profiles/"
ls "$HOME/.config/zuaef/profiles" | grep -q quant-decision.toml \
  || die "quant-decision.toml missing after profile copy"

# ───────────────────────────── 10. .env ──────────────────────────────────────
say "10/12" "repo .env"
ENV_FILE="$REPO_ROOT/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  cp "$REPO_ROOT/.env.example" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "  .env created from .env.example"
fi
append_if_absent "ZUAEF_QUANT_PYTHON"    "$QP"                 "$ENV_FILE"
append_if_absent "ZUAEF_QUANT_REPO_ROOT" "$REPO_ROOT"          "$ENV_FILE"
dotenv_passthrough $TELEGRAM_KEYS
dotenv_passthrough $MODEL_KEYS
chmod 600 "$ENV_FILE"
grep -q '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" || warn "TELEGRAM_BOT_TOKEN not set — gateway will fail closed"
grep -q '^ZUAEF_TELEGRAM_ALLOWED_USERS=' "$ENV_FILE" || warn "ZUAEF_TELEGRAM_ALLOWED_USERS empty — gateway refuses startup"

( cd "$REPO_ROOT" && .venv/bin/zuaef-agent profile check quant-decision ) \
  || warn "profile check quant-decision non-fatal failure (needs .env/model resolved)"

# ───────────────────────────── 11. systemd ───────────────────────────────────
UNIT_FILES=(zuaef-console.service zuaef-gateway.service zuaef-quant-dashboard.service
            zuaef-quant-monitor.service zuaef-quant-monitor.timer
            zuaef-quant-bridge.service zuaef-quant-bridge.timer)
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"

if [[ "$NO_SYSTEMD" -eq 0 ]]; then
  say "11/12" "install systemd package (ops/systemd -> $UNIT_DIR)"
  for u in "${UNIT_FILES[@]}"; do
    src="$REPO_ROOT/ops/systemd/$u"
    tmp="$(mktemp)"
    if [[ "$REPO_ROOT" == "$HOME/zuaef-agent" ]]; then
      cp "$src" "$tmp"
    else
      # repo not at $HOME/zuaef-agent: rewrite %h/zuaef-agent references
      sed "s|%h/zuaef-agent|$REPO_ROOT|g" "$src" > "$tmp"
    fi
    install -m 0644 -b "$tmp" "$UNIT_DIR/$u"
    rm -f "$tmp"
    echo "  installed $u"
  done
  if [[ -n "${ZUAEF_PROXY:-}" ]]; then
    echo "  ZUAEF_PROXY=$ZUAEF_PROXY -> drop-ins for gateway + bridge (telegram/api.telegram.org path)"
    for svc in zuaef-gateway zuaef-quant-bridge; do
      d="$UNIT_DIR/$svc.service.d"
      mkdir -p "$d"
      printf '[Service]\nEnvironment=HTTPS_PROXY=%s\nEnvironment=HTTP_PROXY=%s\n' \
        "$ZUAEF_PROXY" "$ZUAEF_PROXY" > "$d/proxy.conf"
    done
  fi
  systemctl --user daemon-reload
  systemctl --user enable --now \
    zuaef-console.service zuaef-quant-dashboard.service zuaef-gateway.service
  systemctl --user enable --now zuaef-quant-bridge.timer zuaef-quant-monitor.timer
fi

if [[ "$NO_LINGER" -eq 0 ]]; then
  sudo loginctl enable-linger "$(id -un)" || warn "loginctl enable-linger failed"
fi

# ───────────────────────────── 12. smoke / summary ───────────────────────────
if [[ "$SMOKE" -eq 1 ]]; then
  say "12/12" "smoke: monitor once + bridge --dry-run"
  ( cd "$REPO_ROOT" && .venv/bin/python tools/quant_trading_monitor.py once || true )
  ( cd "$REPO_ROOT" && .venv/bin/python tools/quant_telegram_bridge.py --dry-run || true )
fi

say "done" "Orange Pi Production Node v1 bootstrap complete"
cat <<EOF

Installed layout
  .venv/bin/zuaef-agent                 Agent env (python ${ZUAEF_PYTHON}, plugins + akshare group)
  ${QP}                                 Quant env (conda-forge ARM64)
  $(ls -1 "$REPO_ROOT/.arm-wheels" 2>/dev/null | head -1 || echo 'no wheel?')   saved ARM64 wheel
  ~/.config/zuaef/profiles/             profiles (quant-decision among them)
  $ENV_FILE                             secrets + ZUAEF_QUANT_PYTHON

systemd (user units)
  zuaef-console.service                 Agent Console :8765 (loopback)
  zuaef-quant-dashboard.service         Quant Workbench :8787 (loopback)
  zuaef-gateway.service                 Telegram gateway (profile quant-decision)
  zuaef-quant-monitor.{service,timer}   A-share sessions 09:30 / 13:00, --exit-on-close
  zuaef-quant-bridge.{service,timer}    event bridge every 45 s

Then, from the OLD x86 host (do NOT copy .venv*), migrate runtime evidence:
  systemctl --user stop zuaef-quant-bridge.timer 2>/dev/null || true
  rsync -a --info=progress2 ~/zuaef-agent/data/quant-cache/  orangepi@<IP>:~/zuaef-agent/data/quant-cache/
  rsync -a --info=progress2 ~/zuaef-agent/workspace/         orangepi@<IP>:~/zuaef-agent/workspace/
  rsync -a --info=progress2 ~/zuaef-agent/.zuaef-state/      orangepi@<IP>:~/zuaef-agent/.zuaef-state/

Verify from a workstation:
  curl -fsS http://127.0.0.1:8787/api/quant/now | jq
  ssh -L 8765:127.0.0.1:8765 -L 8787:127.0.0.1:8787 orangepi@<TAILSCALE_IP>

Notes
  - Do NOT schedule quant_daily.sh anymore: M1 monitor + bridge is the single
    decision path (otherwise two competing decision paths).
  - Keep 8765/8787 loopback; quant_serve.py POSTs are loopback-enforced.
  - ops/systemd supervisor-sync units are x86-host artifacts (hardcoded codex
    x64 path) — not part of this package.
EOF