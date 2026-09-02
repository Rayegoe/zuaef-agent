from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest

from chatgpt_handoff import cli, clipboard
from chatgpt_handoff.handoff import (
    HandoffError,
    create_session,
    download_candidates,
    import_download,
    latest_session,
    stable_download,
)


def test_ask_sends_and_saves_response(tmp_path: Path, monkeypatch, capsys) -> None:
    sent: list[tuple[str, Path, bool]] = []
    monkeypatch.chdir(tmp_path)

    def run(prompt: str, session: Path, download: bool = False):
        sent.append((prompt, session, download))
        response = session / "response.md"
        response.write_text("回答", encoding="utf-8")
        return response, None

    monkeypatch.setattr(cli, "run_chatgpt", run)

    assert cli.main(["ask", "检查这段实现"]) == 0

    session = latest_session(tmp_path)
    assert (session / "prompt.md").read_text(encoding="utf-8") == "检查这段实现"
    assert sent == [("检查这段实现", session, False)]
    assert "回答已保存" in capsys.readouterr().out


def test_ask_reads_prompt_file(tmp_path: Path, monkeypatch) -> None:
    prompt = tmp_path / "request.md"
    prompt.write_text("来自文件的 prompt", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "run_chatgpt", lambda value, session, download=False: (session / "response.md", None))

    assert cli.main(["ask", "--prompt-file", str(prompt)]) == 0
    assert (latest_session(tmp_path) / "prompt.md").read_text(encoding="utf-8") == "来自文件的 prompt"


def test_ask_reports_non_utf8_prompt(tmp_path: Path, monkeypatch) -> None:
    prompt = tmp_path / "request.md"
    prompt.write_bytes(b"\xff")
    monkeypatch.chdir(tmp_path)
    assert cli.main(["ask", "--prompt-file", str(prompt)]) == 1


@pytest.mark.parametrize("argv", [["ask"], ["ask", "x", "--prompt-file", "missing.md"]])
def test_ask_rejects_invalid_prompt(tmp_path: Path, monkeypatch, argv: list[str]) -> None:
    monkeypatch.chdir(tmp_path)
    assert cli.main(argv) == 1


def test_import_clipboard_writes_latest_session(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    session = create_session("问题", tmp_path)
    monkeypatch.setattr(cli, "paste_text", lambda: "ChatGPT 的回答")

    assert cli.main(["import-clipboard"]) == 0
    assert (session / "response.md").read_text(encoding="utf-8") == "ChatGPT 的回答"


def test_import_clipboard_reports_missing_session(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "paste_text", lambda: "回答")
    assert cli.main(["import-clipboard"]) == 1


def test_clipboard_command_order(monkeypatch) -> None:
    monkeypatch.setattr(clipboard.shutil, "which", lambda name: f"/bin/{name}" if name in {"wl-copy", "wl-paste"} else None)
    assert clipboard._commands() == (["wl-copy"], ["wl-paste", "--no-newline"])


@pytest.mark.parametrize(
    ("available", "expected"),
    [
        (
            {"xclip"},
            (["xclip", "-selection", "clipboard"], ["xclip", "-selection", "clipboard", "-o"]),
        ),
        (
            {"xsel"},
            (["xsel", "--clipboard", "--input"], ["xsel", "--clipboard", "--output"]),
        ),
    ],
)
def test_clipboard_x_backends(monkeypatch, available, expected) -> None:
    monkeypatch.setattr(clipboard.shutil, "which", lambda name: f"/bin/{name}" if name in available else None)
    assert clipboard._commands() == expected


def test_clipboard_without_backend_is_clear(monkeypatch) -> None:
    monkeypatch.setattr(clipboard.shutil, "which", lambda name: None)
    with pytest.raises(clipboard.ClipboardError, match="wl-clipboard"):
        clipboard._commands()


def test_clipboard_transfers_text(monkeypatch) -> None:
    calls: list[tuple[list[str], str | None]] = []

    class Result:
        stdout = "复制的回答"

    monkeypatch.setattr(clipboard, "_commands", lambda: (["copy"], ["paste"]))

    def run(command, *, input=None, **kwargs):
        calls.append((command, input))
        return Result()

    monkeypatch.setattr(clipboard.subprocess, "run", run)
    clipboard.copy_text("问题")
    assert clipboard.paste_text() == "复制的回答"
    assert calls == [(["copy"], "问题"), (["paste"], None)]


def test_ask_download_flag_reaches_browser(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    seen: list[bool] = []

    def run(prompt: str, session: Path, download: bool = False):
        seen.append(download)
        return session / "response.md", session / "spec.zip"

    monkeypatch.setattr(cli, "run_chatgpt", run)
    assert cli.main(["ask", "生成文件", "--download"]) == 0
    assert seen == [True]


def test_import_file_copies_extracts_and_preserves_original(tmp_path: Path) -> None:
    create_session("生成 spec.zip", tmp_path)
    source = tmp_path / "Downloads" / "spec.zip"
    source.parent.mkdir()
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("00_README.md", "可以实施")

    artifact, extracted = import_download(source, tmp_path)

    assert source.is_file()
    assert artifact.read_bytes() == source.read_bytes()
    assert extracted is not None
    assert (extracted / "00_README.md").read_text(encoding="utf-8") == "可以实施"
    assert (latest_session(tmp_path) / "extracted" / "00_README.md").is_file()


def test_import_file_cli_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    create_session("下载文件", tmp_path)
    source = tmp_path / "answer.txt"
    source.write_text("answer", encoding="utf-8")
    assert cli.main(["import-file", str(source)]) == 0
    assert (tmp_path / "artifacts" / "chatgpt" / latest_session(tmp_path).name / "answer.txt").is_file()


def test_import_file_rejects_missing_source(tmp_path: Path) -> None:
    create_session("问题", tmp_path)
    with pytest.raises(HandoffError, match="文件不存在"):
        import_download(tmp_path / "missing.zip", tmp_path)


def test_download_candidates_ignore_temporary_and_old_files(tmp_path: Path) -> None:
    started_at = 1000.0
    old = tmp_path / "old.zip"
    old.write_bytes(b"old")
    os.utime(old, (900.0, 900.0))
    for name in ("spec.zip.crdownload", "spec.zip.part", "spec.zip.tmp"):
        path = tmp_path / name
        path.write_bytes(b"partial")
        os.utime(path, (1100.0, 1100.0))
    complete = tmp_path / "spec.zip"
    complete.write_bytes(b"complete")
    os.utime(complete, (1100.0, 1100.0))

    assert download_candidates(tmp_path, started_at) == [complete]


def test_download_requires_two_equal_nonempty_samples(tmp_path: Path) -> None:
    source = tmp_path / "spec.zip"
    source.write_bytes(b"content")
    started_at = source.stat().st_mtime - 1

    first, sizes = stable_download(tmp_path, started_at, {})
    second, _ = stable_download(tmp_path, started_at, sizes)

    assert first is None
    assert second == source


def test_wait_download_cli_imports_detected_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    session = create_session("下载文件", tmp_path)
    source = tmp_path / "Downloads" / "answer.md"
    source.parent.mkdir()
    source.write_text("answer", encoding="utf-8")
    seen: list[tuple[Path, float]] = []

    def wait(directory: Path, started_at: float) -> Path:
        seen.append((directory, started_at))
        return source

    monkeypatch.setattr(cli.time, "time", lambda: 123.0)
    monkeypatch.setattr(cli, "wait_for_download", wait)
    assert cli.main(["wait-download", "--dir", str(source.parent)]) == 0
    assert seen == [(source.parent, 123.0)]
    assert (tmp_path / "artifacts" / "chatgpt" / session.name / "answer.md").is_file()


def test_latest_session_uses_mtime_not_suffix_sort(tmp_path: Path) -> None:
    root = tmp_path / ".chatgpt-handoff"
    older = root / "20260828-120000-9"
    newer = root / "20260828-120000-10"
    for path in (older, newer):
        path.mkdir(parents=True)
        (path / "prompt.md").write_text("prompt", encoding="utf-8")
    os.utime(older, ns=(1_000_000_000, 1_000_000_000))
    os.utime(newer, ns=(2_000_000_000, 2_000_000_000))
    assert latest_session(tmp_path) == newer


def test_download_directory_must_exist(tmp_path: Path) -> None:
    with pytest.raises(HandoffError, match="下载目录不存在"):
        download_candidates(tmp_path / "missing", 0)
