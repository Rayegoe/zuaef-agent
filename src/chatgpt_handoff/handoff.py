"""Handoff session、文件导入与下载观察。"""

from __future__ import annotations

import shutil
import time
import zipfile
from datetime import datetime
from pathlib import Path

TEMP_DOWNLOAD_SUFFIXES = (".crdownload", ".part", ".tmp")


class HandoffError(RuntimeError):
    """交接操作无法完成。"""


def session_root(workspace: Path | None = None) -> Path:
    return (workspace or Path.cwd()) / ".chatgpt-handoff"


def artifact_root(workspace: Path | None = None) -> Path:
    return (workspace or Path.cwd()) / "artifacts" / "chatgpt"


def create_session(prompt: str, workspace: Path | None = None) -> Path:
    root = session_root(workspace)
    root.mkdir(parents=True, exist_ok=True)
    name = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    destination = root / name
    counter = 2
    while destination.exists():
        destination = root / f"{name}-{counter}"
        counter += 1
    destination.mkdir()
    (destination / "prompt.md").write_text(prompt, encoding="utf-8")
    return destination


def latest_session(workspace: Path | None = None) -> Path:
    root = session_root(workspace)
    sessions = (
        [
            path
            for path in root.iterdir()
            if path.is_dir() and (path / "prompt.md").is_file()
        ]
        if root.is_dir()
        else []
    )
    if not sessions:
        raise HandoffError("没有可用的 handoff session。请先运行 chatgpt-handoff ask。")
    return max(sessions, key=lambda path: (path.stat().st_mtime_ns, path.name))


def import_response(response: str, workspace: Path | None = None) -> Path:
    destination = latest_session(workspace) / "response.md"
    destination.write_text(response, encoding="utf-8")
    return destination


def import_download(source: Path, workspace: Path | None = None) -> tuple[Path, Path | None]:
    source = source.expanduser()
    if not source.is_file():
        raise HandoffError(f"文件不存在：{source}")

    session = latest_session(workspace)
    session_copy = session / source.name
    shutil.copy2(source, session_copy)

    artifact_dir = artifact_root(workspace) / session.name
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_copy = artifact_dir / source.name
    shutil.copy2(source, artifact_copy)

    extracted: Path | None = None
    if source.suffix.lower() == ".zip":
        extracted = artifact_dir / "spec"
        session_extracted = session / "extracted"
        extracted.mkdir(exist_ok=True)
        session_extracted.mkdir(exist_ok=True)
        try:
            with zipfile.ZipFile(session_copy) as archive:
                archive.extractall(session_extracted)
            with zipfile.ZipFile(artifact_copy) as archive:
                archive.extractall(extracted)
        except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
            raise HandoffError(f"无法解压 ZIP：{source}") from exc
    return artifact_copy, extracted


def download_candidates(directory: Path, started_at: float) -> list[Path]:
    directory = directory.expanduser()
    if not directory.is_dir():
        raise HandoffError(f"下载目录不存在：{directory}")
    candidates: list[tuple[float, Path]] = []
    for path in directory.iterdir():
        if path.name.lower().endswith(TEMP_DOWNLOAD_SUFFIXES):
            continue
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        if path.is_file() and stat.st_mtime >= started_at:
            candidates.append((stat.st_mtime, path))
    return [path for _, path in sorted(candidates, reverse=True)]


def stable_download(
    directory: Path,
    started_at: float,
    previous_sizes: dict[Path, int],
) -> tuple[Path | None, dict[Path, int]]:
    current_sizes: dict[Path, int] = {}
    for path in download_candidates(directory, started_at):
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            continue
        current_sizes[path] = size
        if size > 0 and previous_sizes.get(path) == size:
            return path, current_sizes
    return None, current_sizes


def wait_for_download(
    directory: Path,
    started_at: float | None = None,
    interval: float = 1.0,
) -> Path:
    started_at = time.time() if started_at is None else started_at
    previous_sizes: dict[Path, int] = {}
    while True:
        found, previous_sizes = stable_download(directory, started_at, previous_sizes)
        if found is not None:
            return found
        time.sleep(interval)
