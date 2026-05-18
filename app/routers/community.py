from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.deps import require_student, require_teacher, get_current_user
from app.models.community import (
    CommunityChannel, CommunityMessage, MessageReport,
    AssignmentSubmission, AssignmentStatus, AssignmentFileType, ChannelType,
)
from app.models.user import StudentProfile, UserRole, User
from app.services.moderation_service import check_message_content
from app.services.notification_service import send_user_notification

router = APIRouter(prefix="/community", tags=["Community"])

# ── Channels ──────────────────────────────────────────────────────────────────

@router.get("/channels")
async def list_channels(db: AsyncSession = Depends(get_db)):
    """
    Returns the two available channels:
      1. General Channel  (Art + Science + Commercial students — all in one)
      2. Teacher Announcement Channel (read-only for students)
    """
    result = await db.execute(select(CommunityChannel))
    channels = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "type": c.channel_type,
            "is_readonly_for_students": c.is_readonly_for_students,
        }
        for c in channels
    ]


# ── Join ──────────────────────────────────────────────────────────────────────

class JoinChannelRequest(BaseModel):
    channel_id: str


@router.post("/join")
async def join_channel(
    payload: JoinChannelRequest,
    current_user: dict = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Students join the General channel.
    Teacher Announcement channel cannot be joined — it's auto-visible to all.
    """
    result = await db.execute(select(StudentProfile).where(StudentProfile.user_id == current_user["sub"]))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")

    if not profile.has_active_subscription:
        raise HTTPException(status_code=403, detail="Active subscription required to join community")

    channel_result = await db.execute(select(CommunityChannel).where(CommunityChannel.id == payload.channel_id))
    channel = channel_result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if channel.channel_type == ChannelType.teacher_announcement:
        raise HTTPException(status_code=403, detail="Teacher announcement channel is read-only — no need to join")

    profile.community_channel_id = channel.id
    return {"message": f"Joined {channel.name}"}


# ── Messages ──────────────────────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    channel_id: str
    content: str
    media_url: Optional[str] = None
    media_type: Optional[str] = None  # image | pdf


@router.post("/messages")
async def send_message(
    payload: SendMessageRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    channel_result = await db.execute(select(CommunityChannel).where(CommunityChannel.id == payload.channel_id))
    channel = channel_result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    role = current_user.get("role")

    # Teacher announcement: only teachers/admins can post
    if channel.is_readonly_for_students and role == UserRole.student:
        raise HTTPException(status_code=403, detail="Only teachers and admins can post in this channel")

    # Students must have joined the general channel
    if role == UserRole.student:
        profile_result = await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == current_user["sub"])
        )
        profile = profile_result.scalar_one_or_none()
        if not profile or str(profile.community_channel_id) != payload.channel_id:
            raise HTTPException(status_code=403, detail="You must join this channel first")

    flagged, reason = await check_message_content(payload.content)

    message = CommunityMessage(
        channel_id=payload.channel_id,
        sender_id=current_user["sub"],
        content=payload.content,
        media_url=payload.media_url,
        media_type=payload.media_type,
        is_flagged=flagged,
        flagged_reason=reason,
    )
    db.add(message)
    await db.flush()

    if flagged:
        raise HTTPException(status_code=400, detail=f"Message blocked: {reason}")

    return {"message_id": str(message.id), "status": "sent"}


class ReportMessageRequest(BaseModel):
    message_id: str
    reason: str


@router.post("/messages/report")
async def report_message(
    payload: ReportMessageRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = MessageReport(
        message_id=payload.message_id,
        reported_by=current_user["sub"],
        reason=payload.reason,
    )
    db.add(report)
    await db.flush()
    return {"message": "Report submitted"}


# ── Assignment Board ──────────────────────────────────────────────────────────

class SubmitAssignmentRequest(BaseModel):
    channel_id: str
    tagged_teacher_id: str
    file_url: str
    file_type: AssignmentFileType   # "pdf" | "image"
    caption: Optional[str] = None


class AssignmentFileTypeConfirmRequest(BaseModel):
    """
    Frontend first calls /assignments/confirm-type to ask the student
    whether they want to send as PDF or plain image before uploading.
    This endpoint validates the choice and returns upload instructions.
    """
    file_type: AssignmentFileType


@router.post("/assignments/confirm-type")
async def confirm_assignment_file_type(
    payload: AssignmentFileTypeConfirmRequest,
    current_user: dict = Depends(require_student),
):
    """
    Before submitting, the system asks: 'Send as PDF or plain image?'
    Returns upload instructions based on the student's choice.
    """
    if payload.file_type == AssignmentFileType.pdf:
        return {
            "file_type": "pdf",
            "message": "Please upload your assignment as a PDF file.",
            "accepted_mime_types": ["application/pdf"],
            "max_size_mb": 20,
        }
    return {
        "file_type": "image",
        "message": "Please upload your assignment as an image (JPG or PNG).",
        "accepted_mime_types": ["image/jpeg", "image/png"],
        "max_size_mb": 10,
    }


@router.post("/assignments", status_code=201)
async def submit_assignment(
    payload: SubmitAssignmentRequest,
    current_user: dict = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    """
    Student tags a teacher and submits assignment (PDF or image).
    Teacher gets a notification. Other students cannot see this submission.
    """
    # Verify teacher exists
    teacher_result = await db.execute(
        select(User).where(User.id == payload.tagged_teacher_id, User.role == UserRole.teacher)
    )
    teacher = teacher_result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    submission = AssignmentSubmission(
        channel_id=payload.channel_id,
        student_id=current_user["sub"],
        tagged_teacher_id=payload.tagged_teacher_id,
        file_url=payload.file_url,
        file_type=payload.file_type,
        caption=payload.caption,
    )
    db.add(submission)
    await db.flush()

    # Notify the tagged teacher
    student_result = await db.execute(select(User).where(User.id == current_user["sub"]))
    student = student_result.scalar_one()

    await send_user_notification(
        db=db,
        user_id=payload.tagged_teacher_id,
        title="New Assignment Submission",
        body=f"{student.full_name} tagged you and submitted an assignment.",
        notification_type="assignment_submission",
        data={"submission_id": str(submission.id)},
    )

    return {"submission_id": str(submission.id), "status": "submitted"}


@router.get("/assignments/mine")
async def my_assignments(
    current_user: dict = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    """Student views their own submissions and results (private)."""
    result = await db.execute(
        select(AssignmentSubmission)
        .where(AssignmentSubmission.student_id == current_user["sub"])
        .order_by(AssignmentSubmission.submitted_at.desc())
    )
    submissions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "file_type": s.file_type,
            "caption": s.caption,
            "status": s.status,
            "result_text": s.result_text,
            "result_score": s.result_score,
            "result_feedback": s.result_feedback,
            "result_posted_at": s.result_posted_at,
            "submitted_at": s.submitted_at,
        }
        for s in submissions
    ]


@router.get("/assignments/pending")
async def teacher_pending_assignments(
    current_user: dict = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """Teacher views all assignments tagged to them."""
    result = await db.execute(
        select(AssignmentSubmission)
        .where(
            AssignmentSubmission.tagged_teacher_id == current_user["sub"],
            AssignmentSubmission.status == AssignmentStatus.pending,
        )
        .order_by(AssignmentSubmission.submitted_at.asc())
    )
    submissions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "student_id": str(s.student_id),
            "file_url": s.file_url,
            "file_type": s.file_type,
            "caption": s.caption,
            "submitted_at": s.submitted_at,
        }
        for s in submissions
    ]


class PostResultRequest(BaseModel):
    result_text: str
    result_score: Optional[str] = None   # e.g. "85/100" or "B+"
    result_feedback: Optional[str] = None


@router.post("/assignments/{submission_id}/result")
async def post_assignment_result(
    submission_id: str,
    payload: PostResultRequest,
    current_user: dict = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """
    Teacher posts result for a submission.
    Result is PRIVATE — only the student who submitted can see it.
    Other students cannot see this result.
    """
    result = await db.execute(
        select(AssignmentSubmission).where(
            AssignmentSubmission.id == submission_id,
            AssignmentSubmission.tagged_teacher_id == current_user["sub"],
        )
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.result_text = payload.result_text
    submission.result_score = payload.result_score
    submission.result_feedback = payload.result_feedback
    submission.result_posted_at = datetime.utcnow()
    submission.status = AssignmentStatus.graded

    # Notify the student privately
    await send_user_notification(
        db=db,
        user_id=str(submission.student_id),
        title="Assignment Result Posted",
        body=f"Your teacher has reviewed your assignment. Check your result.",
        notification_type="assignment_result",
        data={"submission_id": submission_id},
    )

    return {"message": "Result posted", "submission_id": submission_id}
