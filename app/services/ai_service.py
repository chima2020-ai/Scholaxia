"""
Sia AI Service
--------------
Orchestrates the full Sia pipeline for every interaction mode:
  1. Safety filter (input validation)
  2. Prompt building (mode + level + language + student name)
  3. Model inference
  4. Output sanitization
  5. Interaction logging (weakness tracking)
"""

from app.ai.prompt_builder import (
    build_prompt,
    build_explain_prompt,
    build_solve_prompt,
    build_evaluate_prompt,
    build_generate_questions_prompt,
    build_performance_feedback_prompt,
    build_wrong_answer_prompt,
)
from app.ai.model_backend import run_inference
from app.ai.safety_filter import is_educational, sanitize_output
from app.ai.weakness_analyzer import record_interaction


async def get_ai_response(
    question: str,
    subject: str,
    education_level: str,
    language: str,
    student_id: str,
    student_name: str = "there",
) -> str:
    safe, rejection_reason = is_educational(question)
    if not safe:
        return rejection_reason.replace("{student_name}", student_name)

    prompt = build_prompt(
        question=question,
        subject=subject,
        education_level=education_level,
        language=language,
        student_name=student_name,
    )

    raw_answer = await run_inference(prompt)
    answer = sanitize_output(raw_answer)

    await record_interaction(
        student_id=student_id,
        subject=subject,
        question=question,
        answer=answer,
    )

    return answer


async def sia_explain(
    topic: str,
    subject: str,
    education_level: str,
    language: str,
    student_id: str,
    student_name: str,
) -> str:
    safe, reason = is_educational(topic)
    if not safe:
        return reason

    prompt = build_explain_prompt(
        topic=topic,
        subject=subject,
        education_level=education_level,
        language=language,
        student_name=student_name,
    )
    raw = await run_inference(prompt)
    return sanitize_output(raw)


async def sia_solve(
    question: str,
    subject: str,
    education_level: str,
    language: str,
    student_id: str,
    student_name: str,
) -> str:
    safe, reason = is_educational(question)
    if not safe:
        return reason

    prompt = build_solve_prompt(
        question=question,
        subject=subject,
        education_level=education_level,
        language=language,
        student_name=student_name,
    )
    raw = await run_inference(prompt)
    answer = sanitize_output(raw)

    await record_interaction(
        student_id=student_id,
        subject=subject,
        question=question,
        answer=answer,
    )
    return answer


async def sia_evaluate(
    question: str,
    student_answer: str,
    subject: str,
    education_level: str,
    language: str,
    student_id: str,
    student_name: str,
) -> str:
    prompt = build_evaluate_prompt(
        question=question,
        student_answer=student_answer,
        subject=subject,
        education_level=education_level,
        language=language,
        student_name=student_name,
    )
    raw = await run_inference(prompt)
    return sanitize_output(raw)


async def sia_generate_questions(
    topic: str,
    number: int,
    subject: str,
    education_level: str,
    language: str,
    student_name: str,
    curriculum: str = "WAEC",
) -> str:
    prompt = build_generate_questions_prompt(
        topic=topic,
        number=number,
        subject=subject,
        education_level=education_level,
        language=language,
        student_name=student_name,
        curriculum=curriculum,
    )
    raw = await run_inference(prompt)
    return sanitize_output(raw)


async def sia_performance_feedback(
    weak_topics: list,
    subject: str,
    education_level: str,
    language: str,
    student_id: str,
    student_name: str,
    score: float = None,
) -> str:
    prompt = build_performance_feedback_prompt(
        weak_topics=weak_topics,
        subject=subject,
        education_level=education_level,
        language=language,
        student_name=student_name,
        score=score,
    )
    raw = await run_inference(prompt)
    return sanitize_output(raw)


async def sia_explain_wrong_answer(
    question: str,
    wrong_answer: str,
    correct_answer: str,
    subject: str,
    education_level: str,
    language: str,
    student_name: str,
) -> str:
    prompt = build_wrong_answer_prompt(
        question=question,
        wrong_answer=wrong_answer,
        correct_answer=correct_answer,
        subject=subject,
        education_level=education_level,
        language=language,
        student_name=student_name,
    )
    raw = await run_inference(prompt)
    return sanitize_output(raw)
