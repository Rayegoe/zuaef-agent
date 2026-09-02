"""用专用 Chrome 配置自动完成 ChatGPT Web 交接。"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from .handoff import HandoffError, import_download

CHATGPT_URL = "https://chatgpt.com/"
ASSISTANT_SELECTOR = '[data-message-author-role="assistant"]'
CDP_URL = "http://127.0.0.1:9222"


def _profile_dir() -> Path:
    configured = os.environ.get("CHATGPT_HANDOFF_PROFILE")
    return Path(configured).expanduser() if configured else Path.home() / ".local/share/chatgpt-handoff/chrome-profile"


def _next_download_path(filename: str) -> Path:
    directory = Path.home() / "Downloads"
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / filename
    stem, suffix = candidate.stem, candidate.suffix
    counter = 2
    while candidate.exists():
        candidate = directory / f"{stem} ({counter}){suffix}"
        counter += 1
    return candidate


def _download_link(message: Locator) -> Locator:
    links = message.locator("a")
    for index in range(links.count() - 1, -1, -1):
        link = links.nth(index)
        href = link.get_attribute("href") or ""
        if any(marker in href for marker in ("sandbox:", "/mnt/data/", "/files/", "download")):
            return link
    raise HandoffError("ChatGPT 回答中没有找到可下载文件。")


def _connect_browser(playwright, profile: Path):
    try:
        return playwright.chromium.connect_over_cdp(CDP_URL, timeout=1_000)
    except PlaywrightError:
        subprocess.Popen(
            [
                os.environ.get("CHATGPT_HANDOFF_CHROME", "/usr/bin/google-chrome"),
                f"--user-data-dir={profile}",
                "--remote-debugging-port=9222",
                "--remote-allow-origins=*",
                os.environ.get("CHATGPT_HANDOFF_URL", CHATGPT_URL),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    for _ in range(30):
        try:
            return playwright.chromium.connect_over_cdp(CDP_URL, timeout=1_000)
        except PlaywrightError:
            time.sleep(1)
    raise HandoffError("无法连接专用 Chrome。")


def run_chatgpt(prompt: str, session: Path, download: bool = False) -> tuple[Path, Path | None]:
    profile = _profile_dir()
    profile.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as playwright:
            browser = _connect_browser(playwright, profile)
            context = browser.contexts[0]
            try:
                page = context.pages[-1] if context.pages else context.new_page()
                if not page.url.startswith(CHATGPT_URL):
                    page.goto(
                        os.environ.get("CHATGPT_HANDOFF_URL", CHATGPT_URL),
                        wait_until="domcontentloaded",
                        timeout=60_000,
                    )
                editor = page.locator("#prompt-textarea")
                editor.wait_for(state="visible", timeout=300_000)
                messages = page.locator(ASSISTANT_SELECTOR)
                previous_count = messages.count()
                editor.fill(prompt)
                editor.press("Enter")

                page.wait_for_function(
                    "([selector, count]) => document.querySelectorAll(selector).length > count",
                    [ASSISTANT_SELECTOR, previous_count],
                    timeout=600_000,
                )
                message = messages.last
                previous_text = ""
                stable_samples = 0
                for _ in range(600):
                    text = message.inner_text().strip()
                    generating = page.locator('[data-testid="stop-button"]').count() > 0
                    if text and text == previous_text and not generating:
                        stable_samples += 1
                        if stable_samples >= 2:
                            break
                    else:
                        stable_samples = 0
                    previous_text = text
                    page.wait_for_timeout(1_000)
                else:
                    raise HandoffError("等待 ChatGPT 回答完成超时。")

                response_path = session / "response.md"
                response_path.write_text(text, encoding="utf-8")
                artifact_path: Path | None = None
                if download:
                    link = _download_link(message)
                    with page.expect_download(timeout=120_000) as pending:
                        link.click()
                    downloaded = pending.value
                    local_file = _next_download_path(downloaded.suggested_filename)
                    downloaded.save_as(local_file)
                    artifact_path, _ = import_download(local_file)
                return response_path, artifact_path
            except Exception:
                page.bring_to_front()
                raise
    except PlaywrightTimeoutError as exc:
        raise HandoffError("ChatGPT 页面等待超时；请检查专用浏览器中的登录状态。") from exc
