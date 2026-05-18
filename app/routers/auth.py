from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.models.user import User, UserRole
from app.services.otp_service import send_otp, verify_otp

router = APIRouter(prefix="/auth", tags=["Authentication"])


class StudentSignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OAuthRequest(BaseModel):
    provider: str  # google | apple
    token: str
    full_name: str = ""


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str


# ── Signup ────────────────────────────────────────────────────────────────────

@router.post("/student/signup", status_code=status.HTTP_201_CREATED)
async def student_signup(payload: StudentSignupRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new student. Account is created but NOT verified yet.
    An OTP is sent to their email via Brevo. They must verify before logging in.
    """
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.student,
        is_verified=False,   # not verified until OTP confirmed
    )
    db.add(user)
    await db.flush()

    # Send OTP via Brevo
    await send_otp(email=payload.email, full_name=payload.full_name, purpose="verify_email")

    return {"message": "Account created. Check your email for the verification code."}


@router.post("/verify-email", response_model=TokenResponse)
async def verify_email(payload: OTPVerifyRequest, db: AsyncSession = Depends(get_db)):
    """
    Student submits the OTP from their email.
    On success, account is marked verified and tokens are returned.
    """
    valid = await verify_otp(email=payload.email, otp=payload.otp, purpose="verify_email")
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    await db.flush()

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role),
        refresh_token=create_refresh_token(str(user.id)),
        role=user.role,
    )


@router.post("/resend-otp")
async def resend_otp(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Resend the email verification OTP."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user:
        # Don't reveal whether email exists
        return {"message": "If that email is registered, a new code has been sent."}

    await send_otp(email=user.email, full_name=user.full_name, purpose="verify_email")
    return {"message": "If that email is registered, a new code has been sent."}


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified. Check your inbox for the OTP.")

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role),
        refresh_token=create_refresh_token(str(user.id)),
        role=user.role,
    )


# ── Password Reset ────────────────────────────────────────────────────────────

@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Send a password reset OTP to the user's email via Brevo."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    # Always return the same message — don't reveal if email exists
    if user and user.is_active:
        await send_otp(email=user.email, full_name=user.full_name, purpose="reset_password")

    return {"message": "If that email is registered, a reset code has been sent."}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Verify OTP and set a new password."""
    valid = await verify_otp(email=payload.email, otp=payload.otp, purpose="reset_password")
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(payload.new_password)
    await db.flush()

    return {"message": "Password updated successfully. You can now log in."}


# ── OAuth ─────────────────────────────────────────────────────────────────────

@router.post("/oauth", response_model=TokenResponse)
async def oauth_login(payload: OAuthRequest, db: AsyncSession = Depends(get_db)):
    """Google / Apple OAuth — verify token externally, then issue JWT."""
    # TODO: verify payload.token with Google/Apple SDK
    raise HTTPException(status_code=501, detail="OAuth verification not yet implemented")
