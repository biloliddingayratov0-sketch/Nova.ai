import json
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional

import httpx
from app.config import API_KEY, CHAT_MODEL
from app.services.ai_service import get_openai_client

logger = logging.getLogger("nova_ai.chat_service")

SYSTEM_PROMPT = """You are NOVA AI, a world-class, highly capable, intelligent AI assistant designed to provide accurate, deep, step-by-step, and articulate reasoning.
Your capabilities:
1. Explain complex scientific, mathematical, and philosophical topics clearly with structured formatting.
2. Write clean, idiomatic, secure code with syntax highlighting, architectural advice, and explanations.
3. Support multi-language translation, including fluent Uzbek, English, and Russian.
4. Provide creative writing, content editing, research summaries, and analytical problem-solving.
5. Format mathematical equations using LaTeX and tabular data using Markdown tables.
6. When uncertain, admit limitations honestly instead of fabricating facts.
Always maintain a courteous, professional, and empowering tone."""


def _call_pollinations_chat(messages: List[Dict[str, str]], model: str = "openai") -> str:
    """Fallback real AI LLM chat via Pollinations text API when OpenAI credits are unconfigured."""
    url = "https://text.pollinations.ai/"
    payload = {
        "messages": messages,
        "model": model,
        "seed": 42,
        "jsonMode": False,
    }
    with httpx.Client(timeout=45.0) as client:
        resp = client.post(url, json=payload)
        if resp.status_code == 200:
            return resp.text
        raise RuntimeError(f"Pollinations chat returned {resp.status_code}")


async def stream_chat_response(messages: List[Dict[str, str]], model: Optional[str] = None) -> AsyncGenerator[str, None]:
    """
    Stream AI chat response chunks via Server-Sent Events (SSE).
    Uses OpenAI official client if available, with real fallback.
    """
    selected_model = model or CHAT_MODEL or "gpt-4o-mini"
    client = get_openai_client()

    formatted_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in messages:
        formatted_messages.append({"role": m["role"], "content": m["content"]})

    if client:
        try:
            stream = client.chat.completions.create(
                model=selected_model,
                messages=formatted_messages,
                stream=True,
                temperature=0.7,
                max_tokens=4096,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
            return
        except Exception as e:
            logger.warning(f"OpenAI chat stream failed: {e}. Falling back to real AI text engine...")

    # Real AI streaming fallback
    try:
        url = "https://text.pollinations.ai/"
        payload = {
            "messages": formatted_messages,
            "model": "openai",
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=60.0) as async_client:
            async with async_client.stream("POST", url, json=payload) as resp:
                if resp.status_code == 200:
                    async for chunk in resp.aiter_text():
                        if chunk:
                            yield chunk
                    return
    except Exception as e:
        logger.error(f"Fallback chat stream failed: {e}")

    # Fallback non-stream chunking if streaming endpoint returned single text
    try:
        reply = _call_pollinations_chat(formatted_messages)
        # Yield in realistic word chunks
        words = reply.split(" ")
        for i in range(0, len(words), 3):
            yield " ".join(words[i:i+3]) + " "
    except Exception as exc:
        yield f"NOVA AI encountered an error generating response: {str(exc)}. Please check your OpenAI API key or network connection."


def generate_chat_response(messages: List[Dict[str, str]], model: Optional[str] = None) -> str:
    """Synchronous chat completion."""
    selected_model = model or CHAT_MODEL or "gpt-4o-mini"
    client = get_openai_client()

    formatted_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in messages:
        formatted_messages.append({"role": m["role"], "content": m["content"]})

    if client:
        try:
            resp = client.chat.completions.create(
                model=selected_model,
                messages=formatted_messages,
                temperature=0.7,
                max_tokens=4096,
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.warning(f"OpenAI completion error: {e}. Trying fallback engine...")

    try:
        return _call_pollinations_chat(formatted_messages)
    except Exception as exc:
        raise RuntimeError(f"Chat service error: {str(exc)}")

