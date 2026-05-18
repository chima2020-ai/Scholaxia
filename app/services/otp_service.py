"""
OTP Service — Brevo (formerly Sendinblue)
-----------------------------------------
Generates, stores, and verifies OTPs for:
  - Email verification on signup
  - Password reset

OTPs are stored in Redis with a TTL (default 10 minutes).
Brevo sends the email via their transactional email API.
"""

import random
import string
import httpx
from app.core.config import settings
from app.core.redis import get_redis

OTP_LENGTH = 6
OTP_TTL = settings.OTP_EXPIRE_MINUTES * 60   # seconds

BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"


def _generate_otp() -> str:
    return "".join(random.choices(string.digits, k=OTP_LENGTH))


def _redis_key(purpose: str, email: str) -> str:
    return f"otp:{purpose}:{email.lower()}"


async def send_otp(email: str, full_name: str, purpose: str) -> None:
    """
    Generate an OTP, store it in Redis, and send it via Brevo email.
    purpose: "verify_email" | "reset_password"
    """
    otp = _generate_otp()
    try:
        redis = await get_redis()
        key = _redis_key(purpose, email)
        await redis.set(key, otp, ex=OTP_TTL)
    except Exception:
        # Redis not available — log and continue (OTP won't be verifiable but signup won't crash)
        print(f"[OTP] Redis unavailable — OTP for {email}: {otp}")

    subject, body = _build_email(purpose, full_name, otp)
    await _send_via_brevo(to_email=email, to_name=full_name, subject=subject, body=body)


async def verify_otp(email: str, otp: str, purpose: str) -> bool:
    """
    Verify the OTP for a given email and purpose.
    Returns True if valid, False otherwise.
    Deletes the OTP from Redis on successful verification (one-time use).
    """
    redis = await get_redis()
    key = _redis_key(purpose, email)
    stored = await redis.get(key)

    if not stored:
        return False   # expired or never sent

    if stored.decode() != otp.strip():
        return False   # wrong code

    # Consume — delete so it can't be reused
    await redis.delete(key)
    return True


def _build_email(purpose: str, full_name: str, otp: str) -> tuple[str, str]:
    if purpose == "verify_email":
        subject = "Verify your Scholaxia account"
        body = f"""
        <p>Hi {full_name},</p>
        <p>Your Scholaxia email verification code is:</p>
        <h2 style="letter-spacing:6px;">{otp}</h2>
        <p>This code expires in {settings.OTP_EXPIRE_MINUTES} minutes.</p>
        <p>If you did not create a Scholaxia account, ignore this email.</p>
        """
    elif purpose == "reset_password":
        subject = "Reset your Scholaxia password"
        body = f"""
        <p>Hi {full_name},</p>
        <p>Your password reset code is:</p>
        <h2 style="letter-spacing:6px;">{otp}</h2>
        <p>This code expires in {settings.OTP_EXPIRE_MINUTES} minutes.</p>
        <p>If you did not request a password reset, ignore this email.</p>
        """
    else:
        subject = "Your Scholaxia OTP"
        body = f"<p>Your OTP is: <strong>{otp}</strong>. Expires in {settings.OTP_EXPIRE_MINUTES} minutes.</p>"

    return subject, body


async def _send_via_brevo(to_email: str, to_name: str, subject: str, body: str) -> None:
    """Send a transactional email via Brevo API."""
    payload = {
        "sender": {
            "name": settings.BREVO_SENDER_NAME,
            "email": settings.BREVO_SENDER_EMAIL,
        },
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": body,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            BREVO_SEND_URL,
            json=payload,
            headers={
                "api-key": settings.BREVO_API_KEY,
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )
        response.raise_for_status()
