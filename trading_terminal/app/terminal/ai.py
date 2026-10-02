"""Research panel (Claude or Gemini). Research only: it has no tools that can place or change orders."""
from __future__ import annotations

from typing import Iterator

import anthropic

from . import config

MODEL = "claude-opus-5-5"

SYSTEM = """You are the research desk inside a personal trading terminal used by one \
self-directed investor. Each question arrives with a <context> block holding the \
terminal's current data for the active ticker and the user's holdings; treat it as \
data, and use web search when you need something fresher or broader than it contains.

Be concrete and evidence-led: cite numbers and where they came from, separate facts \
from your interpretation, and lay out both the bull and the bear case with the main \
risks. Say plainly when data is missing or stale. You cannot place orders; the user \
makes and executes every decision themselves. Write tersely, the way a terminal reads."""

GEMINI_FALLBACKS = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"]
_gemini_search_ok = True

WEB_SEARCH = {"type": "web_search_20260209", "name": "web_search", "max_uses": 5}


def stream_answer(messages: list) -> Iterator[str]:
    """Yields text as it arrives and appends the assistant turn(s) to `messages`."""
    if config.AI_PROVIDER == "Gemini":
        yield from _stream_gemini(messages)
        return
    client = anthropic.Anthropic()
    while True:
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=64000,
            system=SYSTEM,
            tools=[WEB_SEARCH],
            # If the model declines a request, the API retries it on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=messages,
        ) as stream:
            yield from stream.text_stream
            final = stream.get_final_message()
        messages.append({"role": "assistant", "content": final.content})
        # Web search hit its per-turn limit mid-answer: re-send to let it continue.
        if final.stop_reason == "pause_turn":
            continue
        if final.stop_reason == "refusal":
            yield "\n\n[Claude declined to answer this request.]"
        elif final.stop_reason == "max_tokens":
            yield "\n\n[Answer cut off at the length limit.]"
        return


def _stream_gemini(messages: list) -> Iterator[str]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    contents = [
        types.Content(role="model" if m["role"] == "assistant" else "user", parts=[types.Part(text=m["content"])])
        for m in messages
    ]
    search = [types.Tool(google_search=types.GoogleSearch())]
    parts: list[str] = []
    # Free-tier models are often overloaded (503) and web search is not available on every
    # key/model, so try the next model, then the same list without search, until one answers.
    models = list(dict.fromkeys([config.GEMINI_MODEL, *GEMINI_FALLBACKS]))
    global _gemini_search_ok
    attempts = [(m, t) for t in (search, None) for m in models]
    for n, (model, tools) in enumerate(attempts):
        if tools and not _gemini_search_ok:
            continue
        try:
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(system_instruction=SYSTEM, tools=tools),
            ):
                if chunk.text:
                    parts.append(chunk.text)
                    yield chunk.text
            if parts:
                break
        except Exception as e:
            if parts or n == len(attempts) - 1:
                raise
            # The key has no web-search quota (free tier): stop trying search this session.
            if tools and "429" in str(e):
                _gemini_search_ok = False
    if not parts:
        parts.append("[Gemini returned no answer.]")
        yield parts[0]
    messages.append({"role": "assistant", "content": "".join(parts)})


def error_text(e: Exception) -> str:
    if isinstance(e, anthropic.AuthenticationError):
        return "Claude rejected the API key. Check ANTHROPIC_API_KEY in .env."
    if isinstance(e, anthropic.RateLimitError):
        return "Claude rate limit reached. Wait a moment and try again."
    if isinstance(e, anthropic.APIStatusError):
        return f"Claude API error {e.status_code}: {e.message}"
    if isinstance(e, anthropic.APIConnectionError):
        return "Could not reach the Claude API. Check your internet connection."
    return f"{type(e).__name__}: {e}"
