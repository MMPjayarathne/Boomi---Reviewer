"""
Async wrapper around the Ollama REST API.
Supports streaming and non-streaming responses.

Ollama often returns HTTP 404 when the model tag in config does not match an
installed model (e.g. llama3 vs llama3:latest). We resolve names using
GET /api/tags. If /api/chat fails, we try OpenAI-compatible POST /v1/chat/completions.
"""

import httpx
import json
from typing import AsyncIterator
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def _normalize_base(url: str) -> str:
    return (url or "").strip().rstrip("/")


async def _get_installed_models(client: httpx.AsyncClient, base: str) -> list[str]:
    try:
        resp = await client.get(f"{base}/api/tags")
        if resp.status_code != 200:
            return []
        data = resp.json()
        return [m["name"] for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []


def _resolve_model_name(requested: str, available: list[str]) -> str:
    if not requested or not available:
        return requested
    if requested in available:
        return requested
    req_strip = requested.strip()
    req_l = req_strip.lower()
    req_norm = req_l.replace(" ", "").replace("-", "")
    for name in available:
        base = name.split(":")[0]
        base_l = base.lower()
        base_norm = base_l.replace(" ", "").replace("-", "")
        if name.startswith(req_strip + ":") or name.lower().startswith(req_l + ":"):
            logger.info("Resolved Ollama model %r -> %r", requested, name)
            return name
        if base_l == req_l or base_norm == req_norm:
            logger.info("Resolved Ollama model %r -> %r", requested, name)
            return name
    return requested


def _model_help(requested: str, available: list[str]) -> str:
    if not available:
        return (
            "\n\n⚠️ **No models found** in Ollama. Run e.g. `ollama pull phi3` or `ollama pull llama3.2`, "
            "then set `OLLAMA_MODEL` in `.env` to the exact name from `ollama list`."
        )
    shown = ", ".join(available[:12])
    more = f" (+{len(available) - 12} more)" if len(available) > 12 else ""
    return (
        f"\n\n⚠️ **Model not available:** `{requested}`.\n\n"
        f"Ollama returned **404** (usually: that model is not installed or the tag is wrong).\n\n"
        f"**Installed models:** {shown}{more}.\n\n"
        "Fix: `ollama pull <name>` or set `OLLAMA_MODEL` in `.env` to one of the names above "
        "(examples: `OLLAMA_MODEL=phi3:latest`, `OLLAMA_MODEL=llama3.2:latest`)."
    )


async def _yield_native_stream(response: httpx.Response) -> AsyncIterator[str]:
    async for line in response.aiter_lines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            chunk = data.get("message", {}).get("content", "")
            if chunk:
                yield chunk
            if data.get("done"):
                break
        except json.JSONDecodeError:
            continue


async def _yield_openai_stream(response: httpx.Response) -> AsyncIterator[str]:
    async for line in response.aiter_lines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data_str = line[5:].strip()
        if data_str == "[DONE]":
            break
        try:
            data = json.loads(data_str)
            choices = data.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            content = delta.get("content") or ""
            if content:
                yield content
        except json.JSONDecodeError:
            continue


async def chat_stream(messages: list[dict]) -> AsyncIterator[str]:
    """
    Stream a chat response from Ollama.
    Yields text chunks as they arrive.
    messages = [{"role": "system"|"user"|"assistant", "content": "..."}]
    """
    base = _normalize_base(settings.ollama_base_url)
    if not base:
        yield "\n\n⚠️ **Configuration:** `ollama_base_url` is empty."
        return

    payload = {"model": settings.ollama_model, "messages": messages, "stream": True}

    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            available = await _get_installed_models(client, base)
            model = _resolve_model_name(settings.ollama_model, available)
            payload["model"] = model

            got_any = False

            async with client.stream("POST", f"{base}/api/chat", json=payload) as resp:
                if resp.status_code == 200:
                    async for chunk in _yield_native_stream(resp):
                        got_any = True
                        yield chunk
                else:
                    err_body = (await resp.aread()).decode(errors="replace")[:600]
                    logger.warning(
                        "Ollama /api/chat HTTP %s: %s", resp.status_code, err_body[:200]
                    )

            if not got_any:
                async with client.stream(
                    "POST", f"{base}/v1/chat/completions", json=payload
                ) as resp2:
                    if resp2.status_code == 200:
                        async for chunk in _yield_openai_stream(resp2):
                            got_any = True
                            yield chunk
                    else:
                        await resp2.aread()

            if not got_any:
                if available:
                    yield _model_help(settings.ollama_model, available)
                else:
                    yield (
                        "\n\n⚠️ **Could not reach Ollama or no models installed.** "
                        "Start Ollama, then `ollama pull phi3` (or another model). "
                        "Set `OLLAMA_MODEL` in `.env` to match `ollama list`."
                    )

    except httpx.ConnectError:
        yield (
            "\n\n⚠️ **Ollama is not running.** "
            "Start the Ollama app or `ollama serve`, then `ollama pull` a model "
            f"(set `OLLAMA_MODEL` in `.env` to match an installed tag)."
        )
    except Exception as exc:
        logger.error("Ollama error: %s", exc, exc_info=True)
        yield f"\n\n⚠️ **AI error:** {str(exc)}"


async def chat_complete(messages: list[dict]) -> str:
    """Non-streaming version — collects the full response."""
    chunks: list[str] = []
    async for chunk in chat_stream(messages):
        chunks.append(chunk)
    return "".join(chunks)


async def is_available() -> bool:
    """Check if Ollama is running."""
    try:
        base = _normalize_base(settings.ollama_base_url)
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{base}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False
