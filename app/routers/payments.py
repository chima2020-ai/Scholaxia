from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.deps import require_student
from app.core.config import settings
from app.models.payment import Subscription, Payment, SubscriptionPlan, PaymentStatus
from app.models.user import StudentProfile
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter(prefix="/payments", tags=["Payments"])

PLAN_PRICES = {
    SubscriptionPlan.basic: 500_00,    # NGN in kobo
    SubscriptionPlan.premium: 2000_00,
    SubscriptionPlan.pro: 5000_00,
}

PLAN_DURATION_DAYS = {
    SubscriptionPlan.basic: 30,
    SubscriptionPlan.premium: 30,
    SubscriptionPlan.pro: 30,
}


class CreatePaymentRequest(BaseModel):
    plan: SubscriptionPlan


@router.post("/checkout")
async def create_checkout(
    payload: CreatePaymentRequest,
    current_user: dict = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    amount = PLAN_PRICES.get(payload.plan)
    intent = stripe.PaymentIntent.create(
        amount=amount,
        currency="ngn",
        metadata={"student_id": current_user["sub"], "plan": payload.plan},
    )

    payment = Payment(
        student_id=current_user["sub"],
        amount=amount / 100,
        currency="NGN",
        stripe_payment_intent_id=intent["id"],
        description=f"{payload.plan} subscription",
    )
    db.add(payment)
    await db.flush()

    return {"client_secret": intent["client_secret"], "payment_id": str(payment.id)}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        student_id = intent["metadata"]["student_id"]
        plan = SubscriptionPlan(intent["metadata"]["plan"])

        # Activate subscription
        result = await db.execute(select(StudentProfile).where(StudentProfile.user_id == student_id))
        profile = result.scalar_one_or_none()
        if profile:
            profile.has_active_subscription = True

        sub = Subscription(
            student_id=student_id,
            plan=plan,
            stripe_subscription_id=intent["id"],
            expires_at=datetime.utcnow() + timedelta(days=PLAN_DURATION_DAYS[plan]),
            has_premium_ai=plan in [SubscriptionPlan.premium, SubscriptionPlan.pro],
            has_community_access=True,
            has_live_class_access=True,
            has_premium_cbt=plan == SubscriptionPlan.pro,
        )
        db.add(sub)

    return {"status": "ok"}
