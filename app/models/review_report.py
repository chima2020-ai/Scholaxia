import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Integer, Float, Enum, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
import enum


class ReportTargetType(str, enum.Enum):
    teacher = "teacher"
    student = "student"


class ReportReason(str, enum.Enum):
    inappropriate_behavior = "inappropriate_behavior"
    harassment = "harassment"
    abusive_language = "abusive_language"
    unprofessional_conduct = "unprofessional_conduct"
    poor_teaching = "poor_teaching"
    cheating = "cheating"
    spam = "spam"
    other = "other"


class ReportStatus(str, enum.Enum):
    pending = "pending"
    under_review = "under_review"
    resolved = "resolved"
    dismissed = "dismissed"


class ReviewTargetType(str, enum.Enum):
    teacher = "teacher"


class Report(Base):
    """
    Any user can report a teacher or student.
    Admin reviews and takes action.
    """
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    target_type: Mapped[ReportTargetType] = mapped_column(Enum(ReportTargetType), nullable=False)
    reason: Mapped[ReportReason] = mapped_column(Enum(ReportReason), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)          # optional extra detail
    evidence_url: Mapped[str] = mapped_column(String(500), nullable=True)  # screenshot/file upload
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.pending)

    # Admin resolution
    resolved_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    resolution_note: Mapped[str] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    reporter: Mapped["User"] = relationship("User", foreign_keys=[reporter_id])
    target: Mapped["User"] = relationship("User", foreign_keys=[target_id])
    resolver: Mapped["User"] = relationship("User", foreign_keys=[resolved_by])


class TeacherReview(Base):
    """
    Students review teachers after a live class or course.
    One review per student per teacher — updatable.
    """
    __tablename__ = "teacher_reviews"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="rating_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    teacher_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    live_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("live_classes.id"), nullable=True
    )  # optional — link to specific class

    rating: Mapped[int] = mapped_column(Integer, nullable=False)           # 1–5 stars
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)        # admin can hide
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student: Mapped["User"] = relationship("User", foreign_keys=[student_id])
    teacher: Mapped["User"] = relationship("User", foreign_keys=[teacher_id])
