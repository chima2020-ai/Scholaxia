"""
Sia AI Service
--------------
Orchestrates the full Sia pipeline with student memory injection.
"""

from app.ai.prompt_builder import (
    build_prompt, build_explain_prompt, build_solve_prompt,
    build_evaluate_prompt, build_generate_questions_prompt,
    build_performance_feedback_prompt, build_wrong_answer_prompt,
)
from app.ai.model_backend import run_inference
from app.ai.safety_filter import is_educational, sanitize_output
from app.ai.weakness_analyzer import record_interaction, get_weak_topics, get_student_history


async def _get_memory(student_id: str, subject: str) -> dict:
    """Build student memory profile for prompt injection."""
    try:
        weak = await get_weak_topics(student_id)
        history = await get_student_history(student_id)
        weak_list = weak.get(subject, []) if isinstance(weak, dict) else []
        # Derive strong topics from history (subjects with many interactions)
        subjects_seen = {}
        for h in history:
            s = h.get("subject", "")
            subjects_seen[s] = subjects_seen.get(s, 0) + 1
        strong = [s for s, c in subjects_seen.items() if c >= 3 and s != subject]
        return {
            "weak_topics": weak_list,
            "strong_topics": strong[:3],
            "learning_style": "adaptive",
            "confidence_score": "building",
        }
    except Exception:
        return {}


async def get_ai_response(question: str, subject: str, education_level: str,
                          language: str, student_id: str, student_name: str = "there") -> str:
    safe, reason = is_educational(question)
    if not safe:
        return reason

    memory = await _get_memory(student_id, subject)
    prompt = build_prompt(question=question, subject=subject, education_level=education_level,
                          language=language, student_name=student_name, student_memory=memory)
    raw = await run_inference(prompt)
    answer = sanitize_output(raw)
    await record_interaction(student_id=student_id, subject=subject, question=question, answer=answer)
    return answer


async def sia_explain(topic: str, subject: str, education_level: str,
                      language: str, student_id: str, student_name: str) -> str:
    safe, reason = is_educational(topic)
    if not safe:
        return reason
    memory = await _get_memory(student_id, subject)
    prompt = build_explain_prompt(topic=topic, subject=subject, education_level=education_level,
                                  language=language, student_name=student_name, student_memory=memory)
    return sanitize_output(await run_inference(prompt))


async def sia_solve(question: str, subject: str, education_level: str,
                    language: str, student_id: str, student_name: str) -> str:
    safe, reason = is_educational(question)
    if not safe:
        return reason
    memory = await _get_memory(student_id, subject)
    prompt = build_solve_prompt(question=question, subject=subject, education_level=education_level,
                                language=language, student_name=student_name, student_memory=memory)
    answer = sanitize_output(await run_inference(prompt))
    await record_interaction(student_id=student_id, subject=subject, question=question, answer=answer)
    return answer


async def sia_evaluate(question: str, student_answer: str, subject: str,
                       education_level: str, language: str, student_id: str, student_name: str) -> str:
    memory = await _get_memory(student_id, subject)
    prompt = build_evaluate_prompt(question=question, student_answer=student_answer, subject=subject,
                                   education_level=education_level, language=language,
                                   student_name=student_name, student_memory=memory)
    return sanitize_output(await run_inference(prompt))


async def sia_generate_questions(topic: str, number: int, subject: str, education_level: str,
                                  language: str, student_name: str, curriculum: str = "WAEC",
                                  student_id: str = "") -> str:
    memory = await _get_memory(student_id, subject) if student_id else {}
    prompt = build_generate_questions_prompt(topic=topic, number=number, subject=subject,
                                             education_level=education_level, language=language,
                                             student_name=student_name, curriculum=curriculum,
                                             student_memory=memory)
    return sanitize_output(await run_inference(prompt))


async def sia_performance_feedback(weak_topics: list, subject: str, education_level: str,
                                    language: str, student_id: str, student_name: str,
                                    score: float = None) -> str:
    memory = await _get_memory(student_id, subject)
    prompt = build_performance_feedback_prompt(weak_topics=weak_topics, subject=subject,
                                               education_level=education_level, language=language,
                                               student_name=student_name, score=score,
                                               student_memory=memory)
    return sanitize_output(await run_inference(prompt))


async def sia_explain_wrong_answer(question: str, wrong_answer: str, correct_answer: str,
                                    subject: str, education_level: str, language: str,
                                    student_name: str, student_id: str = "") -> str:
    memory = await _get_memory(student_id, subject) if student_id else {}
    prompt = build_wrong_answer_prompt(question=question, wrong_answer=wrong_answer,
                                       correct_answer=correct_answer, subject=subject,
                                       education_level=education_level, language=language,
                                       student_name=student_name, student_memory=memory)
    return sanitize_output(await run_inference(prompt))
