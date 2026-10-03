"""Claude through the Claude Code CLI, signed in with a Claude subscription (no API key).

Sign-in uses the same flow as the CLI: `claude auth login --claudeai` prints a link, you approve
it in a browser, and paste the code it shows back in. Questions run with `claude -p` in a locked
down mode: no tools that run commands or edit files, web search only.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Iterator

# In the Home Assistant add-on this points at /data/claude so the login survives updates.
CONFIG_DIR = os.getenv("CLAUDE_CONFIG_DIR", "")
TOOLS = ["WebSearch", "WebFetch"]
_status_cache: tuple[float, dict] = (0.0, {})


def binary() -> str | None:
    return shutil.which("claude")


def _env() -> dict:
    env = dict(os.environ, DISABLE_AUTOUPDATER="1", BROWSER="none", NO_COLOR="1")
    # An API key in the environment would take priority over the subscription login.
    env.pop("ANTHROPIC_API_KEY", None)
    if CONFIG_DIR:
        env["CLAUDE_CONFIG_DIR"] = CONFIG_DIR
    return env


def status(max_age: float = 600) -> dict:
    """`claude auth status` as a dict ({} if the CLI is missing or fails); cached for 10 minutes (it starts a\n    separate program, which takes a few seconds on a small device)."""
    global _status_cache
    if time.time() - _status_cache[0] < max_age:
        return _status_cache[1]
    result = {}
    if binary():
        try:
            out = subprocess.run([binary(), "auth", "status"], capture_output=True, text=True, timeout=20,
                                 env=_env()).stdout
            result = json.loads(out[out.find("{"):]) if "{" in out else {}
        except Exception:
            result = {}
    _status_cache = (time.time(), result)
    return result


def signed_in() -> bool:
    s = status()
    return bool(s.get("loggedIn")) and s.get("authMethod") in ("claude.ai", "oauth_token", "claude_ai")


def forget_status() -> None:
    global _status_cache
    _status_cache = (0.0, {})


def logout() -> None:
    if binary():
        subprocess.run([binary(), "auth", "logout"], capture_output=True, text=True, timeout=20, env=_env())
    forget_status()


class Login:
    """One run of `claude auth login --claudeai`, driven from the web page."""

    def __init__(self):
        self.output = ""
        self.started = time.time()
        self.proc = subprocess.Popen(
            [binary(), "auth", "login", "--claudeai"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1, env=_env(),
        )
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.proc.stdout:
            self.output += line

    @property
    def url(self) -> str | None:
        m = re.search(r"https://\S+", self.output)
        return m.group(0) if m else None

    @property
    def done(self) -> bool:
        return self.proc.poll() is not None

    def send_code(self, code: str) -> None:
        if not self.done:
            self.proc.stdin.write(code.strip() + "\n")
            self.proc.stdin.flush()

    def cancel(self) -> None:
        if not self.done:
            self.proc.kill()

    @property
    def result(self) -> str:
        """Last line the CLI printed, with the sign-in link removed."""
        lines = [ln.strip() for ln in self.output.splitlines() if ln.strip() and "http" not in ln]
        return lines[-1] if lines else ""


def _command(system: str, stream: bool) -> list[str]:
    cmd = [binary(), "-p", "--restricted", "--no-session-persistence", "--tools", *TOOLS,
           "--allowedTools", *TOOLS, "--system-prompt", system]
    if stream:
        cmd += ["--output-format", "stream-json", "--verbose", "--include-partial-messages"]
    else:
        cmd += ["--output-format", "json"]
    return cmd


def _workdir() -> str:
    d = os.path.join(CONFIG_DIR or tempfile.gettempdir(), "trading-terminal-work")
    os.makedirs(d, exist_ok=True)
    return d


def ask(prompt: str, system: str, timeout: int = 300) -> str:
    """One complete answer."""
    p = subprocess.run(_command(system, stream=False), input=prompt, capture_output=True, text=True,
                       timeout=timeout, env=_env(), cwd=_workdir())
    try:
        data = json.loads(p.stdout[p.stdout.find("{"):])
    except (ValueError, json.JSONDecodeError):
        raise RuntimeError(f"Claude Code failed: {(p.stderr or p.stdout).strip()[:300]}")
    if data.get("is_error"):
        raise RuntimeError(f"Claude Code: {data.get('result') or data.get('subtype')}")
    return data.get("result") or ""


def stream(prompt: str, system: str, timeout: int = 600) -> Iterator[str]:
    """Yields the answer as it is written."""
    p = subprocess.Popen(_command(system, stream=True), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, bufsize=1, env=_env(), cwd=_workdir())
    p.stdin.write(prompt)
    p.stdin.close()
    started, wrote, final = time.time(), False, None
    for line in p.stdout:
        if time.time() - started > timeout:
            p.kill()
            raise RuntimeError("Claude Code took too long to answer")
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "stream_event":
            delta = (ev.get("event") or {}).get("delta") or {}
            if delta.get("type") == "text_delta" and delta.get("text"):
                wrote = True
                yield delta["text"]
        elif ev.get("type") == "result":
            final = ev
    p.wait(timeout=30)
    if final is None:
        raise RuntimeError(f"Claude Code failed: {p.stderr.read().strip()[:300]}")
    if final.get("is_error"):
        raise RuntimeError(f"Claude Code: {final.get('result') or final.get('subtype')}")
    if not wrote and final.get("result"):
        yield final["result"]
