from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_user, require_student, require_admin
from app.models.review_report import (
    Report, TeacherReview,
    ReportTargetType, ReportReason, ReportStatus,
)
from app.models.user import User, UserRole

router = APIRouter(prefix="/reviews-reports", tags=["Reviews & Reports"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class SubmitReportRequest(BaseModel):
    target_id: str
    target_type: ReportTargetType
    reason: ReportReason
    description: Optional[str] = Field(None, max_length=1000)
    evidence_url: Optional[str] = None


class ReportResponse(BaseModel):
    id: str
    target_type: str
    reason: str
    status: str
    created_at: datetime


class SubmitReviewRequest(BaseModel):
    teacher_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)
    is_anonymous: bool = False
    live_class_id: Optional[str] = None


class ReviewResponse(BaseModel):
    id: str
    teacher_id: str
    rating: int
    comment: Optional[str]
    is_anonymous: bool
    reviewer_name: str   # "Anonymous" if is_anonymous=True
    created_at: datetime


class TeacherRatingSummary(BaseModel):
    teacher_id: str
    teacher_name: str
    average_rating: float
    total_reviews: int
    reviews: list[ReviewResponse]


class ResolveReportRequest(BaseModel):
    status: ReportStatus
    resolution_note: str


# ── Reports ──────────────────────────────────────────────────────────────────

@router.post("/reports", response_model=ReportResponse, status_code=201)
async def submit_report(
    payload: SubmitReportRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Any logged-in user can report a teacher or student."""
    if payload.target_id == current_user["sub"]:
        raise HTTPException(status_code=400, detail="You cannot report yourself")

    # Verify target exists
    result = await db.execute(select(User).where(User.id == payload.target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate target_type matches actual role
    if payload.target_type == ReportTargetType.teacher and target.role != UserRole.teacher:
        raise HTTPException(status_code=400, detail="Target is not a teacher")
    if payload.target_type == ReportTargetType.student and target.role != UserRole.student:
        raise HTTPException(status_code=400, detail="Target is not a student")

    # Prevent duplicate pending reports from same reporter
    existing = await db.execute(
        select(Report).where(
            Report.reporter_id == current_user["sub"],
            Report.target_id == payload.target_id,
            Report.status == ReportStatus.pending,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You already have a pending report against this user")

    report = Report(
        reporter_id=current_user["sub"],
        target_id=payload.target_id,
        target_type=payload.target_type,
        reason=payload.reason,
        description=payload.description,
        evidence_url=payload.evidence_url,
    )
    db.add(report)
    await db.flush()

    return ReportResponse(
        id=str(report.id),
        target_type=report.target_type,
        reason=report.reason,
        status=report.status,
        created_at=report.created_at,
    )


@router.get("/reports/mine", response_model=list[ReportResponse])
async def my_reports(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """View reports you have submitted."""
    result = await db.execute(
        select(Report)
        .where(Report.reporter_id == current_user["sub"])
        .order_by(Report.created_at.desc())
    )
    reports = result.scalars().all()
    return [
        ReportResponse(
            id=str(r.id),
            target_type=r.target_type,
            reason=r.reason,
            status=r.status,
            created_at=r.created_at,
        )
        for r in reports
    ]


# ── Reviews ──────────────────────────────────────────────────────────────────

@router.post("/reviews", response_model=ReviewResponse, status_code=201)
async def submit_review(
    payload: SubmitReviewRequest,
    current_user: dict = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    """Students review a teacher. One review per student per teacher — updates if exists."""
    # Verify teacher exists
    result = await db.execute(
        select(User).where(User.id == payload.teacher_id, User.role == UserRole.teacher)
    )
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    # Check for existing review — update it
    existing_result = await db.execute(
        select(TeacherReview).where(
            TeacherReview.student_id == current_user["sub"],
            TeacherReview.teacher_id == payload.teacher_id,
        )
    )
    review = existing_result.scalar_one_or_none()

    if review:
        review.rating = payload.rating
        review.comment = payload.comment
        review.is_anonymous = payload.is_anonymous
        if payload.live_class_id:
            review.live_class_id = payload.live_class_id
    else:
        review = TeacherReview(
            student_id=current_user["sub"],
            teacher_id=payload.teacher_id,
            live_class_id=payload.live_class_id,
            rating=payload.rating,
            comment=payload.comment,
            is_anonymous=payload.is_anonymous,
        )
        db.add(review)

    await db.flush()

    # Get reviewer name
    student_result = await db.execute(select(User).where(User.id == current_user["sub"]))
    student = student_result.scalar_one()

    return ReviewResponse(
        id=str(review.id),
        teacher_id=str(review.teacher_id),
        rating=review.rating,
        comment=review.comment,
        is_anonymous=review.is_anonymous,
        reviewer_name="Anonymous" if review.is_anonymous else student.full_name,
        created_at=review.created_at,
    )


@router.get("/reviews/teacher/{teacher_id}", response_model=TeacherRatingSummary)
async def get_teacher_reviews(
    teacher_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all visible reviews and average rating for a teacher."""
    teacher_result = await db.execute(
        select(User).where(User.id == teacher_id, User.role == UserRole.teacher)
    )
    teacher = teacher_result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    reviews_result = await db.execute(
        select(TeacherReview, User)
        .join(User, User.id == TeacherReview.student_id)
        .where(
            TeacherReview.teacher_id == teacher_id,
            TeacherReview.is_visible == True,
        )
        .order_by(TeacherReview.created_at.desc())
    )
    rows = reviews_result.all()

    review_list = [
        ReviewResponse(
            id=str(r.id),
            teacher_id=str(r.teacher_id),
            rating=r.rating,
            comment=r.comment,
            is_anonymous=r.is_anonymous,
            reviewer_name="Anonymous" if r.is_anonymous else u.full_name,
            created_at=r.created_at,
        )
        for r, u in rows
    ]

    avg = round(sum(r.rating for r in review_list) / len(review_list), 1) if review_list else 0.0

    return TeacherRatingSummary(
        teacher_id=teacher_id,
        teacher_name=teacher.full_name,
        average_rating=avg,
        total_reviews=len(review_list),
        reviews=review_list,
    )


@router.delete("/reviews/{review_id}", status_code=204)
async def delete_my_review(
    review_id: str,
    current_user: dict = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    """Student deletes their own review."""
    result = await db.execute(
        select(TeacherReview).where(
            TeacherReview.id == review_id,
            TeacherReview.student_id == current_user["sub"],
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    await db.delete(review)


# ── Admin moderation ──────────────────────────────────────────────────────────

@router.get("/admin/reports", dependencies=[Depends(require_admin)])
async def admin_list_reports(
    status: Optional[ReportStatus] = Query(None),
    target_type: Optional[ReportTargetType] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Admin views all reports, filterable by status and target type."""
    query = (
        select(Report, User.full_name.label("reporter_name"))
        .join(User, User.id == Report.reporter_id)
        .order_by(Report.created_at.desc())
    )
    if status:
        query = query.where(Report.status == status)
    if target_type:
        query = query.where(Report.target_type == target_type)

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "id": str(r.id),
            "reporter": reporter_name,
            "target_id": str(r.target_id),
            "target_type": r.target_type,
            "reason": r.reason,
            "description": r.description,
            "evidence_url": r.evidence_url,
            "status": r.status,
            "created_at": r.created_at,
            "resolved_at": r.resolved_at,
            "resolution_note": r.resolution_note,
        }
        for r, reporter_name in rows
    ]


@router.patch("/admin/reports/{report_id}", dependencies=[Depends(require_admin)])
async def admin_resolve_report(
    report_id: str,
    payload: ResolveReportRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin resolves or dismisses a report."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.status = payload.status
    report.resolution_note = payload.resolution_note
    report.resolved_by = current_user["sub"]
    report.resolved_at = datetime.utcnow()

    return {
        "id": str(report.id),
        "status": report.status,
        "resolution_note": report.resolution_note,
        "resolved_at": report.resolved_at,
    }


@router.patch("/admin/reviews/{review_id}/hide", dependencies=[Depends(require_admin)])
async def admin_hide_review(
    review_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Admin hides an inappropriate review from public view."""
    result = await db.execute(select(TeacherReview).where(TeacherReview.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    review.is_visible = False
    return {"message": "Review hidden"}
