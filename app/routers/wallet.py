"""
Teacher Wallet Router
---------------------
Teachers earn money from live classes.
Admin credits wallets. Teachers request withdrawals.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.deps import require_teacher, require_admin
from app.models.wallet import (
    TeacherWallet, WalletTransaction, WithdrawalRequest,
    WalletTransactionType, WithdrawalStatus,
)
from app.models.user import User
from app.services.notification_service import send_user_notification

router = APIRouter(prefix="/wallet", tags=["Teacher Wallet"])


async def _get_or_create_wallet(teacher_id: str, db: AsyncSession) -> TeacherWallet:
    result = await db.execute(
        select(TeacherWallet).where(TeacherWallet.teacher_id == teacher_id)
    )
    wallet = result.scalar_one_or_none()
    if not wallet:
        wallet = TeacherWallet(teacher_id=teacher_id)
        db.add(wallet)
        await db.flush()
    return wallet


# ── Teacher: View own wallet ──────────────────────────────────────────────────

@router.get("/me")
async def get_my_wallet(
    current_user: dict = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """Teacher views their wallet balance and transaction history."""
    wallet = await _get_or_create_wallet(current_user["sub"], db)

    tx_result = await db.execute(
        select(WalletTransaction)
        .where(WalletTransaction.wallet_id == wallet.id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(50)
    )
    transactions = tx_result.scalars().all()

    return {
        "balance": wallet.balance,
        "total_earned": wallet.total_earned,
        "total_withdrawn": wallet.total_withdrawn,
        "currency": wallet.currency,
        "transactions": [
            {
                "id": str(t.id),
                "type": t.transaction_type,
                "amount": t.amount,
                "description": t.description,
                "live_class_id": str(t.live_class_id) if t.live_class_id else None,
                "created_at": t.created_at,
            }
            for t in transactions
        ],
    }


# ── Teacher: Request withdrawal ───────────────────────────────────────────────

class WithdrawalRequestBody(BaseModel):
    amount: float
    bank_name: str
    account_number: str
    account_name: str


@router.post("/withdraw")
async def request_withdrawal(
    payload: WithdrawalRequestBody,
    current_user: dict = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """Teacher requests a withdrawal from their wallet balance."""
    wallet = await _get_or_create_wallet(current_user["sub"], db)

    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")
    if payload.amount > wallet.balance:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Available: ₦{wallet.balance:,.2f}",
        )

    # Check no pending withdrawal already exists
    pending = await db.execute(
        select(WithdrawalRequest).where(
            WithdrawalRequest.teacher_id == current_user["sub"],
            WithdrawalRequest.status == WithdrawalStatus.pending,
        )
    )
    if pending.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="You already have a pending withdrawal request. Wait for it to be processed.",
        )

    withdrawal = WithdrawalRequest(
        wallet_id=wallet.id,
        teacher_id=current_user["sub"],
        amount=payload.amount,
        bank_name=payload.bank_name,
        account_number=payload.account_number,
        account_name=payload.account_name,
    )
    db.add(withdrawal)
    await db.flush()

    return {
        "withdrawal_id": str(withdrawal.id),
        "amount": payload.amount,
        "status": "pending",
        "message": "Withdrawal request submitted. Admin will process within 2-3 business days.",
    }


@router.get("/withdrawals")
async def my_withdrawals(
    current_user: dict = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
):
    """Teacher views their withdrawal history."""
    result = await db.execute(
        select(WithdrawalRequest)
        .where(WithdrawalRequest.teacher_id == current_user["sub"])
        .order_by(WithdrawalRequest.requested_at.desc())
    )
    withdrawals = result.scalars().all()
    return [
        {
            "id": str(w.id),
            "amount": w.amount,
            "bank_name": w.bank_name,
            "account_number": w.account_number[-4:].rjust(len(w.account_number), "*"),  # mask
            "status": w.status,
            "admin_note": w.admin_note,
            "requested_at": w.requested_at,
            "processed_at": w.processed_at,
        }
        for w in withdrawals
    ]


# ── Admin: Credit teacher wallet ──────────────────────────────────────────────

class CreditWalletRequest(BaseModel):
    teacher_id: str
    amount: float
    description: str
    live_class_id: Optional[str] = None


@router.post("/admin/credit")
async def admin_credit_wallet(
    payload: CreditWalletRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin credits a teacher's wallet after a completed live class."""
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")

    # Verify teacher exists
    teacher_result = await db.execute(select(User).where(User.id == payload.teacher_id))
    teacher = teacher_result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    wallet = await _get_or_create_wallet(payload.teacher_id, db)

    # Credit the wallet
    wallet.balance += payload.amount
    wallet.total_earned += payload.amount

    transaction = WalletTransaction(
        wallet_id=wallet.id,
        teacher_id=payload.teacher_id,
        transaction_type=WalletTransactionType.credit,
        amount=payload.amount,
        description=payload.description,
        live_class_id=payload.live_class_id,
        created_by=current_user["sub"],
    )
    db.add(transaction)
    await db.flush()

    # Notify teacher
    await send_user_notification(
        db=db,
        user_id=payload.teacher_id,
        title="Payment Received",
        body=f"₦{payload.amount:,.2f} has been credited to your wallet. {payload.description}",
        notification_type="wallet_credit",
        data={"transaction_id": str(transaction.id), "amount": payload.amount},
    )

    return {
        "message": "Wallet credited successfully",
        "teacher_id": payload.teacher_id,
        "amount_credited": payload.amount,
        "new_balance": wallet.balance,
    }


# ── Admin: Process withdrawal ─────────────────────────────────────────────────

class ProcessWithdrawalRequest(BaseModel):
    status: WithdrawalStatus  # approved | rejected | paid
    admin_note: Optional[str] = None


@router.patch("/admin/withdrawals/{withdrawal_id}")
async def admin_process_withdrawal(
    withdrawal_id: str,
    payload: ProcessWithdrawalRequest,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin approves, rejects, or marks a withdrawal as paid."""
    result = await db.execute(
        select(WithdrawalRequest).where(WithdrawalRequest.id == withdrawal_id)
    )
    withdrawal = result.scalar_one_or_none()
    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal request not found")

    if withdrawal.status == WithdrawalStatus.paid:
        raise HTTPException(status_code=400, detail="This withdrawal has already been paid")

    wallet = await _get_or_create_wallet(str(withdrawal.teacher_id), db)

    # If approving/paying: deduct from balance
    if payload.status in (WithdrawalStatus.approved, WithdrawalStatus.paid):
        if withdrawal.amount > wallet.balance:
            raise HTTPException(status_code=400, detail="Teacher balance insufficient for this withdrawal")
        if payload.status == WithdrawalStatus.paid:
            wallet.balance -= withdrawal.amount
            wallet.total_withdrawn += withdrawal.amount
            # Record debit transaction
            debit = WalletTransaction(
                wallet_id=wallet.id,
                teacher_id=str(withdrawal.teacher_id),
                transaction_type=WalletTransactionType.debit,
                amount=withdrawal.amount,
                description=f"Withdrawal processed — {withdrawal.bank_name}",
                created_by=current_user["sub"],
            )
            db.add(debit)

    withdrawal.status = payload.status
    withdrawal.admin_note = payload.admin_note
    withdrawal.processed_at = datetime.utcnow()
    withdrawal.processed_by = current_user["sub"]
    await db.flush()

    # Notify teacher
    status_msg = {
        WithdrawalStatus.approved: "Your withdrawal request has been approved and will be processed soon.",
        WithdrawalStatus.rejected: f"Your withdrawal request was rejected. {payload.admin_note or ''}",
        WithdrawalStatus.paid: f"₦{withdrawal.amount:,.2f} has been sent to your bank account.",
    }
    await send_user_notification(
        db=db,
        user_id=str(withdrawal.teacher_id),
        title="Withdrawal Update",
        body=status_msg.get(payload.status, "Your withdrawal status has been updated."),
        notification_type="withdrawal_update",
        data={"withdrawal_id": withdrawal_id, "status": payload.status},
    )

    return {
        "withdrawal_id": withdrawal_id,
        "status": payload.status,
        "message": "Withdrawal updated successfully",
    }


@router.get("/admin/withdrawals")
async def admin_list_withdrawals(
    status: Optional[WithdrawalStatus] = None,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin views all withdrawal requests, optionally filtered by status."""
    query = select(WithdrawalRequest).order_by(WithdrawalRequest.requested_at.desc())
    if status:
        query = query.where(WithdrawalRequest.status == status)
    result = await db.execute(query)
    withdrawals = result.scalars().all()
    return [
        {
            "id": str(w.id),
            "teacher_id": str(w.teacher_id),
            "amount": w.amount,
            "bank_name": w.bank_name,
            "account_number": w.account_number,
            "account_name": w.account_name,
            "status": w.status,
            "admin_note": w.admin_note,
            "requested_at": w.requested_at,
            "processed_at": w.processed_at,
        }
        for w in withdrawals
    ]


@router.get("/admin/teachers/{teacher_id}/wallet")
async def admin_view_teacher_wallet(
    teacher_id: str,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin views a specific teacher's wallet details."""
    wallet = await _get_or_create_wallet(teacher_id, db)
    tx_result = await db.execute(
        select(WalletTransaction)
        .where(WalletTransaction.wallet_id == wallet.id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(100)
    )
    transactions = tx_result.scalars().all()
    return {
        "teacher_id": teacher_id,
        "balance": wallet.balance,
        "total_earned": wallet.total_earned,
        "total_withdrawn": wallet.total_withdrawn,
        "currency": wallet.currency,
        "transactions": [
            {
                "id": str(t.id),
                "type": t.transaction_type,
                "amount": t.amount,
                "description": t.description,
                "created_at": t.created_at,
            }
            for t in transactions
        ],
    }
