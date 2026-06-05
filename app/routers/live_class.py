import uuid
import time
import hashlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.core.database import get_db
from app.core.deps import require_teacher, require_student, get_current_user
from app.core.config import settings
from app.models.live_class import LiveClass, ClassAttendance
from app.models.user import StudentProfile
from app.services.notification_service import send_subject_notification

router = APIRouter(prefix="/live-classes", tags=["Live Classes"])


# ── Agora token helper ────────────────────────────────────────────────────────

def _generate_agora_token(channel_id: str, uid: int, is_teacher: bool) -> str:
    """Generate an Agora RTC token. Falls back to a placeholder if no certificate."""
    if not settings.AGORA_APP_CERTIFICATE:
        # No certificate configured — return a placeholder so the app doesn't crash
        return f"AGORA_CERT_NOT_SET_{channel_id}_{uid}"
    try:
        from agora_token_builder import RtcTokenBuilder
        role = 1 if is_teacher else 2  # 1=Publisher, 2=Subscriber
        expire_ts = int(time.time()) + 3600  # 1 hour
        token = RtcTokenBuilder.buildTokenWithUid(
            settings.AGORA_APP_ID,
            settings.AGORA_APP_CERTIFICATE,
            channel_id,
            uid,
            role,
            expire_ts,
        )
        return token
    except Exception:
        return f"TOKEN_ERROR_{channel_id}_{uid}"


def _user_uid(user_id: str) -> int:
    """Convert UUID to a stable integer UID for Agora (Agora needs uint32)."""
    return int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16) % (2**31)


class CreateClassRequest(BaseModel):
    subject: str
    title: str
    description: Optional[str] = None
    start_time: datetime


class ClassResponse(BaseModel):
    id: str
    subject: str
    title: str
    teacher_id: str
    start_time: datetime
    is_live: bool
    room_id: str


@router.post("/", response_model=ClassResponse)
async def create_class(
    payload: CreateClassRequest,
    current_user: dict = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    room_id = f"room-{uuid.uuid4().hex[:12]}"
    live_class = LiveClass(
        teacher_id=current_user["sub"],
        subject=payload.subject,
        title=payload.title,
        description=payload.description,
        start_time=payload.start_time,
        room_id=room_id,
    )
    db.add(live_class)
    await db.flush()
    return ClassResponse(
        id=str(live_class.id),
        subject=live_class.subject,
        title=live_class.title,
        teacher_id=str(live_class.teacher_id),
        start_time=live_class.start_time,
        is_live=live_class.is_live,
        room_id=live_class.room_id,
    )


@router.post("/{class_id}/start")
async def start_class(
    class_id: str,
    current_user: dict = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """Start a class and notify ONLY students subscribed to that subject."""
    result = await db.execute(select(LiveClass).where(LiveClass.id == class_id))
    live_class = result.scalar_one_or_none()
    if not live_class:
        raise HTTPException(status_code=404, detail="Class not found")
    if str(live_class.teacher_id) != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Not your class")

    live_class.is_live = True

    # Notify only students who selected this subject
    await send_subject_notification(
        db=db,
        subject=live_class.subject,
        title=f"Live class starting now",
        body=f"Your {live_class.subject} live class is starting now.",
        notification_type="live_class",
        data={"class_id": str(live_class.id), "room_id": live_class.room_id},
    )
    return {"message": "Class started", "room_id": live_class.room_id}


@router.post("/{class_id}/join")
async def join_class(
    class_id: str,
    current_user: dict = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LiveClass).where(LiveClass.id == class_id))
    live_class = result.scalar_one_or_none()
    if not live_class or not live_class.is_live:
        raise HTTPException(status_code=404, detail="Class not live")

    attendance = ClassAttendance(
        live_class_id=live_class.id,
        student_id=current_user["sub"],
        is_muted=True,
    )
    db.add(attendance)
    await db.flush()

    uid = _user_uid(current_user["sub"])
    token = _generate_agora_token(live_class.room_id, uid, is_teacher=False)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    return {
        "room_id": live_class.room_id,
        "agora_token": token,
        "uid": uid,
        "channel_id": live_class.room_id,
        "app_id": settings.AGORA_APP_ID,
        "is_muted": True,
        "expires_at": expires_at,
    }


@router.get("/{class_id}/token")
async def get_agora_token(
    class_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a fresh Agora RTC token for a live class room."""
    result = await db.execute(select(LiveClass).where(LiveClass.id == class_id))
    live_class = result.scalar_one_or_none()
    if not live_class:
        raise HTTPException(status_code=404, detail="Class not found")

    is_teacher = str(live_class.teacher_id) == current_user["sub"]
    uid = _user_uid(current_user["sub"])
    token = _generate_agora_token(live_class.room_id, uid, is_teacher=is_teacher)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    return {
        "token": token,
        "channel_id": live_class.room_id,
        "uid": uid,
        "app_id": settings.AGORA_APP_ID,
        "expires_at": expires_at,
    }


@router.post("/{class_id}/students/{student_id}/unmute")
async def unmute_student(
    class_id: str,
    student_id: str,
    current_user: dict = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClassAttendance).where(
            ClassAttendance.live_class_id == class_id,
            ClassAttendance.student_id == student_id,
        )
    )
    attendance = result.scalar_one_or_none()
    if not attendance:
        raise HTTPException(status_code=404, detail="Student not in class")
    attendance.is_muted = False
    return {"message": "Student unmuted"}


@router.post("/{class_id}/students/{student_id}/remove")
async def remove_student(
    class_id: str,
    student_id: str,
    current_user: dict = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ClassAttendance).where(
            ClassAttendance.live_class_id == class_id,
            ClassAttendance.student_id == student_id,
        )
    )
    attendance = result.scalar_one_or_none()
    if not attendance:
        raise HTTPException(status_code=404, detail="Student not in class")
    attendance.is_removed = True
    return {"message": "Student removed"}
