"""
Student Analytics — Persistent DB model
-----------------------------------------
Stores long-term learning profile: weak topics, learning speed,
confidence, quiz history, attention patterns, revision frequency.
Used by Sia's Academic Memory Engine and Parent Dashboard.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Float, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class StudentLearningProfile(Base):
    """
    Sia's persistent memory of a student's learning journey.
    Updated after every AI interaction, CBT session, and lesson.
    """
    __tablename__ = "student_learning_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, index=True)

    # Academic memory
    weak_subjects: Mapped[dict] = mapped_column(JSON, default={})       # {subject: [topics]}
    strong_subjects: Mapped[dict] = mapped_column(JSON, default={})     # {subject: [topics]}
    mistake_patterns: Mapped[dict] = mapped_column(JSON, default={})    # {subject: [common_errors]}
    quiz_history: Mapped[list] = mapped_column(JSON, default=[])        # [{subject, score, date, topics}]

    # Learning behaviour
    learning_speed: Mapped[str] = mapped_column(String(20), default="medium")  # slow | medium | fast
    confidence_level: Mapped[str] = mapped_column(String(20), default="building")  # low | building | confident
    attention_pattern: Mapped[str] = mapped_column(String(50), default="normal")   # short | normal | extended
    preferred_language: Mapped[str] = mapped_column(String(50), default="english")
    revision_frequency: Mapped[int] = mapped_column(Integer, default=0)  # sessions per week

    # Engagement
    total_ai_sessions: Mapped[int] = mapped_column(Integer, default=0)
    total_cbt_sessions: Mapped[int] = mapped_column(Integer, default=0)
    total_study_minutes: Mapped[int] = mapped_column(Integer, default=0)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)

    # Emotional state (for Sia's emotional intelligence)
    last_emotional_state: Mapped[str] = mapped_column(String(50), default="neutral")  # frustrated | neutral | confident
    encouragement_needed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Personalized study plan (AI-generated)
    study_plan: Mapped[dict] = mapped_column(JSON, default={})  # {subject: {priority, topics, daily_goal}}

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LessonSession(Base):
    """
    Tracks a structured Sia lesson session (lesson mode).
    Sia teaches step-by-step like a classroom teacher.
    """
    __tablename__ = "lesson_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    education_level: Mapped[str] = mapped_column(String(50), nullable=False)
    curriculum: Mapped[str] = mapped_column(String(50), default="Nigerian")  # Nigerian | Cambridge | WAEC | etc.

    # Lesson progress
    current_step: Mapped[int] = mapped_column(Integer, default=1)  # 1-11 (greeting → homework)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    lesson_notes: Mapped[str] = mapped_column(Text, nullable=True)  # Sia's generated notes for this lesson
    homework: Mapped[str] = mapped_column(Text, nullable=True)
    quiz_score: Mapped[float] = mapped_column(Float, nullable=True)
    understanding_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0-100 Sia's assessment

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
