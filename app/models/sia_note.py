import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class SiaNoteTag(str):
    pass


class SiaNote(Base):
    """
    A note saved from a Sia AI interaction.
    Student can save any Sia response as a personal note to review later.
    Notes are private — only visible to the student who saved them.
    """
    __tablename__ = "sia_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # What the student asked
    question: Mapped[str] = mapped_column(Text, nullable=True)

    # Sia's response saved as the note content
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Student can give the note a custom title
    title: Mapped[str] = mapped_column(String(255), nullable=True)

    # Subject and topic for organisation
    subject: Mapped[str] = mapped_column(String(100), nullable=True)
    topic: Mapped[str] = mapped_column(String(255), nullable=True)

    # Which Sia mode generated this note
    # ask | explain | solve | evaluate | generate_questions | feedback | explain_wrong
    source_mode: Mapped[str] = mapped_column(String(50), nullable=True)

    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
