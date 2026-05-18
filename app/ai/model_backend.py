"""
Scholaxia AI Model Backend — Sia
----------------------------------
Abstraction layer over model inference.
Supports three backends, configured via AI_BACKEND env var:

  1. "groq"    — Groq cloud API (FREE, fast, no install) ← RECOMMENDED
  2. "hosted"  — Self-hosted inference server (Ollama, vLLM, TGI)
  3. "local"   — HuggingFace Transformers running in-process (needs GPU/disk)

Switch backends by setting AI_BACKEND in .env — no other code changes needed.
"""

import asyncio
import httpx
from app.core.config import settings


# ── Backend: GROQ (free cloud API — recommended) ─────────────────────────────

async def _infer_groq(prompt: str, conversation_history: list = None,
                      image_base64: str = None) -> str:
    """
    Calls Groq's API.
    Supports conversation history and image input (vision).
    """
    messages = []

    if conversation_history:
        for msg in conversation_history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    # If image provided, use vision-capable model
    if image_base64:
        model = "meta-llama/llama-4-scout-17b-16e-instruct"
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                },
                {"type": "text", "text": prompt}
            ]
        })
    else:
        model = settings.GROQ_MODEL
        messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": settings.AI_MAX_TOKENS,
                "temperature": settings.AI_TEMPERATURE,
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()


# ── Backend: HOSTED (self-hosted — Ollama / vLLM / TGI) ──────────────────────

async def _infer_hosted(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        if settings.AI_HOSTED_ENDPOINT_TYPE == "chat":
            response = await client.post(
                f"{settings.AI_HOSTED_BASE_URL}/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.AI_HOSTED_API_KEY}"},
                json={
                    "model": settings.AI_HOSTED_MODEL_NAME,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": settings.AI_MAX_TOKENS,
                    "temperature": settings.AI_TEMPERATURE,
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()

        elif settings.AI_HOSTED_ENDPOINT_TYPE == "ollama":
            response = await client.post(
                f"{settings.AI_HOSTED_BASE_URL}/api/generate",
                json={
                    "model": settings.AI_HOSTED_MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": settings.AI_MAX_TOKENS,
                        "temperature": settings.AI_TEMPERATURE,
                    },
                },
            )
            response.raise_for_status()
            return response.json()["response"].strip()

        else:
            response = await client.post(
                settings.AI_HOSTED_BASE_URL,
                headers={"Authorization": f"Bearer {settings.AI_HOSTED_API_KEY}"},
                json={"prompt": prompt, "max_tokens": settings.AI_MAX_TOKENS},
            )
            response.raise_for_status()
            data = response.json()
            return (data.get("result") or data.get("text") or data.get("output") or "").strip()


# ── Backend: LOCAL (HuggingFace in-process) ───────────────────────────────────

_local_pipeline = None


def _load_local_pipeline():
    global _local_pipeline
    if _local_pipeline is None:
        from transformers import pipeline
        _local_pipeline = pipeline(
            "text-generation",
            model=settings.AI_LOCAL_MODEL_NAME,
            device=settings.AI_LOCAL_DEVICE,
            max_new_tokens=settings.AI_MAX_TOKENS,
            do_sample=True,
            temperature=settings.AI_TEMPERATURE,
            top_p=0.9,
            repetition_penalty=1.1,
        )
    return _local_pipeline


async def _infer_local(prompt: str) -> str:
    pipe = await asyncio.get_event_loop().run_in_executor(None, _load_local_pipeline)
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: pipe(prompt)
    )
    generated = result[0]["generated_text"]
    return generated[len(prompt):].strip()


# ── Public interface ──────────────────────────────────────────────────────────

async def run_inference(prompt: str, conversation_history: list = None,
                        image_base64: str = None) -> str:
    backend = settings.AI_BACKEND.lower()
    if backend == "groq":
        return await _infer_groq(prompt, conversation_history, image_base64)
    elif backend == "hosted":
        return await _infer_hosted(prompt)
    elif backend == "local":
        return await _infer_local(prompt)
    else:
        raise ValueError(f"Unknown AI_BACKEND: '{backend}'")
