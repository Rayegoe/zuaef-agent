"""chatgpt-handoff 命令行入口。"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .clipboard import ClipboardError, paste_text
from .handoff import (
    HandoffError,
    create_session,
    import_download,
    import_response,
    wait_for_download,
)
from .web import run_chatgpt


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        prog="chatgpt-handoff",
        description="自动把 Codex 指令发送到 ChatGPT Web，并接回答案或下载文件。",
    )
    subcommands = command.add_subparsers(dest="command", required=True)

    ask = subcommands.add_parser("ask", help="自动发送 prompt 并保存 ChatGPT 回答")
    ask.add_argument("prompt", nargs="?")
    ask.add_argument("--prompt-file", type=Path)
    ask.add_argument("--download", action="store_true", help="自动下载回答生成的文件")

    subcommands.add_parser("import-clipboard", help="导入剪贴板中的 ChatGPT 回答")

    import_file = subcommands.add_parser("import-file", help="复制并导入一个下载文件")
    import_file.add_argument("file", type=Path)

    wait_download = subcommands.add_parser("wait-download", help="等待并导入新下载文件")
    wait_download.add_argument("--dir", type=Path, default=Path.home() / "Downloads")
    return command


def _prompt(args: argparse.Namespace) -> str:
    if args.prompt_file is not None and args.prompt is not None:
        raise HandoffError("请只使用 prompt 参数或 --prompt-file，不要同时使用。")
    if args.prompt_file is not None:
        try:
            value = args.prompt_file.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise HandoffError(f"无法读取 prompt 文件：{args.prompt_file}") from exc
    else:
        value = args.prompt or ""
    if not value.strip():
        raise HandoffError("prompt 不能为空。")
    return value


def _ask(args: argparse.Namespace) -> int:
    prompt = _prompt(args)
    session = create_session(prompt)
    print("正在打开 ChatGPT、发送指令并等待回答……")
    response, artifact = run_chatgpt(prompt, session, download=args.download)
    print(f"回答已保存：\n\n{response}")
    if artifact is not None:
        print(f"\n文件已下载并导入：\n\n{artifact}")
    return 0


def _import_clipboard() -> int:
    destination = import_response(paste_text())
    print(f"已导入 ChatGPT 回答：\n\n{destination}")
    return 0


def _print_import(source: Path) -> int:
    destination, extracted = import_download(source)
    print(f"已导入：\n\n{destination}")
    if extracted is not None:
        print(f"\n已解压：\n\n{extracted}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "ask":
            return _ask(args)
        if args.command == "import-clipboard":
            return _import_clipboard()
        if args.command == "import-file":
            return _print_import(args.file)
        if args.command == "wait-download":
            started_at = time.time()
            print(f"等待新下载：{args.dir}（Ctrl+C 停止）")
            return _print_import(wait_for_download(args.dir, started_at))
    except (ClipboardError, HandoffError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已停止等待。", file=sys.stderr)
        return 130
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
