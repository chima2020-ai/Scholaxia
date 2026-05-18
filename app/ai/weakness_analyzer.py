"""
Weakness Analyzer
-----------------
Tracks student AI interactions and CBT results to identify weak topics.
Stores interaction history in Redis for fast access.
Persists summaries to the database for analytics.
"""

import json
from datetime import datetime
from app.core.redis import get_redis


HISTORY_KEY = "ai:history:{student_id}"
WEAKNESS_KEY = "ai:weakness:{student_id}"
MAX_HISTORY = 50  # keep last 50 interactions per student


async def record_interaction(student_id: str, subject: str, question: str, answer: str):
    """Save an AI interaction to Redis history."""
    try:
        redis = await get_redis()
        if not redis:
            return
        key = HISTORY_KEY.format(student_id=student_id)
        entry = json.dumps({
            "subject": subject,
            "question": question,
            "answer": answer,
            "ts": datetime.utcnow().isoformat(),
        })
        await redis.lpush(key, entry)
        await redis.ltrim(key, 0, MAX_HISTORY - 1)
    except Exception:
        pass  # Redis unavailable — don't crash Sia


async def get_student_history(student_id: str) -> list:
    try:
        redis = await get_redis()
        if not redis:
            return []
        key = HISTORY_KEY.format(student_id=student_id)
        raw = await redis.lrange(key, 0, -1)
        return [json.loads(r) for r in raw]
    except Exception:
        return []


async def update_weak_topics(student_id: str, subject: str, weak_topics: list):
    try:
        redis = await get_redis()
        if not redis:
            return
        key = WEAKNESS_KEY.format(student_id=student_id)
        existing_raw = await redis.get(key)
        existing = json.loads(existing_raw) if existing_raw else {}
        subject_weaknesses = existing.get(subject, [])
        for topic in weak_topics:
            if topic not in subject_weaknesses:
                subject_weaknesses.append(topic)
        existing[subject] = subject_weaknesses
        await redis.set(key, json.dumps(existing), ex=86400 * 30)
    except Exception:
        pass


async def get_weak_topics(student_id: str) -> dict:
    try:
        redis = await get_redis()
        if not redis:
            return {}
        key = WEAKNESS_KEY.format(student_id=student_id)
        raw = await redis.get(key)
        return json.loads(raw) if raw else {}
    except Exception:
        return {}
