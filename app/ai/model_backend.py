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
    """Groq fallback — used if Gemini is not configured."""
    import asyncio

    messages = []
    if conversation_history:
        for msg in conversation_history[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    if image_base64:
        model = "meta-llama/llama-4-scout-17b-16e-instruct"
        messages.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                {"type": "text", "text": prompt}
            ]
        })
    else:
        model = settings.GROQ_MODEL
        messages.append({"role": "user", "content": prompt})

    for attempt in range(3):
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

            if response.status_code == 429:
                retry_after = int(response.headers.get("retry-after", 10))
                wait = min(retry_after, 30)
                await asyncio.sleep(wait)
                continue

            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()

    raise Exception("Groq rate limit exceeded. Please try again in a moment.")


async def _infer_gemini(prompt: str, conversation_history: list = None,
                        image_base64: str = None) -> str:
    """
    Google Gemini — primary AI backend.
    Uses Gemini 1.5 Pro (smartest) with automatic fallback to Flash if quota exceeded.
    - Pro: 50 req/day free, 2M token context, best quality
    - Flash: 1,500 req/day free, 1M token context, very fast
    """
    contents = []

    if conversation_history:
        for msg in conversation_history[-8:]:
            role = "user" if msg.get("role") == "user" else "model"
            content = msg.get("content", "")
            if content:
                contents.append({"role": role, "parts": [{"text": content}]})

    if image_base64:
        contents.append({
            "role": "user",
            "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": image_base64}},
                {"text": prompt}
            ]
        })
    else:
        contents.append({"role": "user", "parts": [{"text": prompt}]})

    gen_config = {
        "maxOutputTokens": settings.AI_MAX_TOKENS,
        "temperature": settings.AI_TEMPERATURE,
    }

    safety = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
    ]

    # Try Pro first, fall back to Flash if quota exceeded
    for model in [settings.GEMINI_MODEL, settings.GEMINI_FLASH_MODEL]:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"Content-Type": "application/json"},
                params={"key": settings.GEMINI_API_KEY},
                json={"contents": contents, "generationConfig": gen_config, "safetySettings": safety},
            )

            if response.status_code == 429:
                # Quota exceeded on this model — try next
                continue

            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Both models quota exceeded — fall back to Groq
    if settings.GROQ_API_KEY:
        return await _infer_groq(prompt, conversation_history, image_base64)

    raise Exception("All AI providers are currently rate limited. Please try again in a moment.")


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

async def _infer_openai(prompt: str, conversation_history: list = None) -> str:
    """OpenAI GPT-4o — highest quality, paid."""
    messages = []
    if conversation_history:
        for msg in conversation_history[-8:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.OPENAI_MODEL,
                "messages": messages,
                "max_tokens": settings.AI_MAX_TOKENS,
                "temperature": settings.AI_TEMPERATURE,
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()


async def _infer_deepseek(prompt: str, conversation_history: list = None) -> str:
    """DeepSeek — very smart, cheap, OpenAI-compatible API."""
    messages = []
    if conversation_history:
        for msg in conversation_history[-8:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.DEEPSEEK_MODEL,
                "messages": messages,
                "max_tokens": settings.AI_MAX_TOKENS,
                "temperature": settings.AI_TEMPERATURE,
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()



                        image_base64: str = None) -> str:
    backend = settings.AI_BACKEND.lower()

    # Auto-select: use Gemini if key is set, fall back to Groq
    if backend == "gemini" or (backend == "groq" and settings.GEMINI_API_KEY):
        if settings.GEMINI_API_KEY:
            return await _infer_gemini(prompt, conversation_history, image_base64)

    if backend == "groq":
        return await _infer_groq(prompt, conversation_history, image_base64)
    elif backend == "hosted":
        return await _infer_hosted(prompt)
    elif backend == "local":
        return await _infer_local(prompt)
    else:
        raise ValueError(f"Unknown AI_BACKEND: '{backend}'")

async def _infer_openai(prompt: str, conversation_history: list = None) -> str:
    """OpenAI GPT-4o — highest quality."""
    messages = []
    if conversation_history:
        for msg in conversation_history[-8:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={"model": settings.OPENAI_MODEL, "messages": messages,
                  "max_tokens": settings.AI_MAX_TOKENS, "temperature": settings.AI_TEMPERATURE},
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()


async def _infer_deepseek(prompt: str, conversation_history: list = None) -> str:
    """DeepSeek — very smart, cheap, OpenAI-compatible."""
    messages = []
    if conversation_history:
        for msg in conversation_history[-8:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={"model": settings.DEEPSEEK_MODEL, "messages": messages,
                  "max_tokens": settings.AI_MAX_TOKENS, "temperature": settings.AI_TEMPERATURE},
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()


async def run_inference(prompt: str, conversation_history: list = None,
                        image_base64: str = None, subject: str = "") -> str:
    """
    Smart AI routing based on subject type.

    Math/Physics/Chemistry → DeepSeek Reasoner (best for calculations)
    History/Literature/Research → OpenAI GPT-4o (best for research)
    Everything else → Gemini 2.5 Pro (best for deep explanations)
    Automatic fallback if any provider fails or hits limits.
    """
    errors = []

    math_subjects = {"mathematics", "further mathematics", "physics", "chemistry",
                     "statistics", "engineering", "calculus", "algebra", "trigonometry",
                     "further maths", "additional maths"}
    research_subjects = {"history", "government", "literature", "economics",
                         "geography", "civic education", "english", "general knowledge",
                         "social studies", "christian religious studies", "islamic religious studies"}

    subject_lower = subject.lower() if subject else ""
    is_math = any(s in subject_lower for s in math_subjects)
    is_research = any(s in subject_lower for s in research_subjects)

    available = {
        "gemini": bool(settings.GEMINI_API_KEY),
        "openai": bool(settings.OPENAI_API_KEY),
        "deepseek": bool(settings.DEEPSEEK_API_KEY),
        "groq": bool(settings.GROQ_API_KEY),
    }

    if is_math:
        # Math → DeepSeek Reasoner first
        order = ["deepseek", "gemini", "openai", "groq"]
    elif is_research:
        # Research → OpenAI first
        order = ["openai", "gemini", "deepseek", "groq"]
    else:
        # Default → Gemini first (deep explanations)
        order = ["gemini", "deepseek", "openai", "groq"]

    fns = {
        "gemini":   lambda: _infer_gemini(prompt, conversation_history, image_base64),
        "openai":   lambda: _infer_openai(prompt, conversation_history),
        "deepseek": lambda: _infer_deepseek(prompt, conversation_history),
        "groq":     lambda: _infer_groq(prompt, conversation_history, image_base64),
    }

    providers = [(name, fns[name]) for name in order if available.get(name)]

    if not providers:
        raise ValueError("No AI provider configured.")

    for name, fn in providers:
        try:
            return await fn()
        except Exception as e:
            errors.append(f"{name}: {str(e)[:80]}")
            continue

    raise Exception(f"All AI providers failed: {'; '.join(errors)}")
