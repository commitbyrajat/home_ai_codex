import asyncio
import os
import logging
from pathlib import Path
import subprocess
import time

from playwright.sync_api import sync_playwright
from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from gemini_search.engine import AIModeEngine
import gemini_search.engine as engine_module


logger = logging.getLogger("gemini-search")
mcp = FastMCP("Gemini Search", instructions="Search the web using Google AI Mode and return grounded answers with sources.")
READONLY = ToolAnnotations(readOnlyHint=True)
_engine = None


def patch_google_optional_srtst() -> None:
    """Handle Google's current AI Mode page, where data-srtst is empty."""
    script = engine_module._ASK_JS
    obsolete_guard = "if (!srtst) return {error:'no_token', htmlLen:html.length, preview:html.substring(0,200)};"
    old_params = "const p = new URLSearchParams({srtst,garc,mlro:lro,mlros,ei,q,yv:'3',vet:'1'+ved+'..i',ved,aep:'1',gl:'us',hl:'en',sca_esv:sca,udm:'50',stkp,cs:'0',async:'_fmt:adl,_xsrf:'+xsrf});"
    new_params = old_params + " if (!srtst) p.delete('srtst');"
    if obsolete_guard not in script or old_params not in script:
        raise RuntimeError("Unexpected upstream Google AI Mode script; compatibility patch needs review")
    engine_module._ASK_JS = script.replace(obsolete_guard, "").replace(old_params, new_params)


def clear_stale_browser_locks(profile_dir: str) -> None:
    """Remove Chromium singleton links left behind by a previous container."""
    running_browser = False
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / "cmdline").read_bytes().lower()
        except OSError:
            continue
        if b"/chrome" in command or b"chromium" in command:
            running_browser = True
            break
    if running_browser:
        logger.warning("Leaving Chromium profile locks in place; a browser process is still running")
        return

    profile = Path(profile_dir)
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        lock = profile / name
        if lock.is_symlink() or lock.is_file():
            lock.unlink(missing_ok=True)


async def warmup_with_manual_captcha(self):
    """Keep a visible browser alive when Google requests human verification."""
    await self._navigate("https://www.google.com.hk/search?q=hello&hl=en&gl=us")
    url = await self._evaluate("window.location.href")
    if "/sorry/" in (url or ""):
        logger.warning(
            "Google CAPTCHA is open in the local browser view. Complete it at "
            "http://127.0.0.1:6080/vnc.html?autoconnect=true&resize=scale, "
            "then retry the MCP search."
        )


_original_ask = AIModeEngine.ask


async def ask_with_manual_captcha_notice(self, question: str, timeout_ms: int = 45000):
    try:
        return await _original_ask(self, question, timeout_ms)
    except Exception as exc:
        # The upstream page script catches fetch() exceptions and returns them
        # as {error: "js_exception"}, so AIModeEngine.ask treats a transient
        # network failure as a completed response and never reaches its own
        # retry path. Refresh the Google page once and retry that case here.
        if "js_exception: Failed to fetch" in str(exc):
            logger.warning("Google AI Mode fetch failed; refreshing the page and retrying once")
            try:
                await self._warmup()
                return await _original_ask(self, question, timeout_ms)
            except Exception as retry_exc:
                exc = retry_exc
        try:
            url = await self._evaluate("window.location.href")
        except Exception:
            url = ""
        if "/sorry/" in (url or ""):
            raise RuntimeError(
                "Google CAPTCHA is still open. Complete it in the local browser "
                "view at http://127.0.0.1:6080/vnc.html?autoconnect=true&resize=scale, "
                "then retry web_search."
            ) from exc
        raise


async def get_engine() -> AIModeEngine:
    """Start and return the shared browser engine on first tool call."""
    global _engine
    if _engine is None:
        async with _engine_lock:
            if _engine is None:
                _engine = AIModeEngine()
                await _engine.start(
                    cdp_url=os.environ.get("CDP_URL"),
                    headless=os.environ.get("HEADLESS", "1") != "0",
                    channel=os.environ.get("BROWSER_CHANNEL", "chromium"),
                    user_data_dir=os.environ.get("GEMINI_SEARCH_USER_DATA_DIR"),
                    browser_backend=os.environ.get("GEMINI_SEARCH_BROWSER_BACKEND"),
                    proxy_server=os.environ.get("GEMINI_SEARCH_PROXY_SERVER"),
                    chromedriver_path=os.environ.get("GEMINI_SEARCH_CHROMEDRIVER") or os.environ.get("UC_CHROMEDRIVER"),
                )
    return _engine


_engine_lock = asyncio.Lock()


@mcp.tool(annotations=READONLY)
async def web_search(query: str) -> str:
    """Search the web with Google AI Mode and return a synthesized, sourced answer."""
    engine = await get_engine()
    return await engine.ask(query)


@mcp.tool(annotations=READONLY)
async def ask(prompt: str) -> str:
    """Ask Google AI Mode a general question, with web grounding when appropriate."""
    engine = await get_engine()
    return await engine.ask(prompt)


def start_visible_desktop():
    os.environ.setdefault("DISPLAY", ":99")
    processes = [
        ["Xvfb", ":99", "-screen", "0", "1280x900x24", "-nolisten", "tcp"],
        ["x11vnc", "-display", ":99", "-forever", "-shared", "-nopw", "-rfbport", "5900", "-localhost"],
        ["/usr/share/novnc/utils/novnc_proxy", "--listen", "6080", "--vnc", "localhost:5900", "--web", "/usr/share/novnc"],
    ]
    for command in processes:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.25)


if __name__ == "__main__":
    patch_google_optional_srtst()
    # Preserve the browser process on CAPTCHA so a person can complete the
    # challenge through the loopback-only noVNC view and reuse its profile.
    AIModeEngine._warmup = warmup_with_manual_captcha
    AIModeEngine.ask = ask_with_manual_captcha_notice

    if os.environ.get("HEADLESS", "1") == "0":
        start_visible_desktop()

    # The app searches common system browser locations, but Playwright installs
    # Chromium under ~/.cache/ms-playwright. Point the app at that binary.
    with sync_playwright() as playwright:
        browser_path = playwright.chromium.executable_path

    profile_dir = os.environ.get("GEMINI_SEARCH_USER_DATA_DIR")
    if profile_dir:
        clear_stale_browser_locks(profile_dir)

    # Chrome refuses to start as root in a container unless --no-sandbox is set.
    # The upstream launcher does not add that flag, so expose a small wrapper.
    browser_wrapper = Path("/tmp/gemini-search-chromium")
    browser_wrapper.write_text(
        f'#!/bin/sh\nexec "{browser_path}" --no-sandbox "$@"\n',
        encoding="utf-8",
    )
    browser_wrapper.chmod(0o755)
    os.environ["CHROME_PATH"] = str(browser_wrapper)

    mcp.run(transport="http", host="0.0.0.0", port=3000, path="/mcp")
