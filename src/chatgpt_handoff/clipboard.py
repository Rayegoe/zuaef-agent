"""Linux 系统剪贴板命令适配。"""

from __future__ import annotations

import shutil
import subprocess


class ClipboardError(RuntimeError):
    """系统剪贴板不可用。"""


def _commands() -> tuple[list[str], list[str]]:
    if shutil.which("wl-copy") and shutil.which("wl-paste"):
        return ["wl-copy"], ["wl-paste", "--no-newline"]
    if shutil.which("xclip"):
        return (
            ["xclip", "-selection", "clipboard"],
            ["xclip", "-selection", "clipboard", "-o"],
        )
    if shutil.which("xsel"):
        return ["xsel", "--clipboard", "--input"], ["xsel", "--clipboard", "--output"]
    raise ClipboardError(
        "没有可用的剪贴板后端。请安装 wl-clipboard、xclip 或 xsel。"
    )


def copy_text(value: str) -> None:
    write_command, _ = _commands()
    try:
        subprocess.run(
            write_command,
            input=value,
            text=True,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ClipboardError(f"写入剪贴板失败：{exc}") from exc


def paste_text() -> str:
    _, read_command = _commands()
    try:
        result = subprocess.run(
            read_command,
            text=True,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ClipboardError(f"读取剪贴板失败：{exc}") from exc
    return result.stdout

