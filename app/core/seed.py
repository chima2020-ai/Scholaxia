"""
Database Seeder
---------------
Creates the default admin account and community channels on first startup.
Safe to run multiple times — skips if already exists.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.security import hash_password
from app.core.config import settings
from app.models.user import User, UserRole
from app.models.community import CommunityChannel, ChannelType


async def seed_database(db: AsyncSession):
    await _seed_admin(db)
    await _seed_channels(db)
    await db.commit()


async def _seed_admin(db: AsyncSession):
    result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
    if result.scalar_one_or_none():
        return  # already exists

    admin = User(
        email=settings.ADMIN_EMAIL,
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        full_name="Scholaxia Admin",
        role=UserRole.admin,
        is_active=True,
        is_verified=True,
    )
    db.add(admin)
    print(f"[seed] Admin created: {settings.ADMIN_EMAIL}")


async def _seed_channels(db: AsyncSession):
    channels = [
        {
            "name": "General Channel",
            "channel_type": ChannelType.general,
            "description": "Main channel for all students — Science, Art, and Commercial.",
            "is_readonly_for_students": False,
        },
        {
            "name": "Teacher Announcements",
            "channel_type": ChannelType.teacher_announcement,
            "description": "Official announcements from teachers and admin. Students can read only.",
            "is_readonly_for_students": True,
        },
    ]

    for ch in channels:
        result = await db.execute(
            select(CommunityChannel).where(CommunityChannel.channel_type == ch["channel_type"])
        )
        if result.scalar_one_or_none():
            continue  # already seeded

        channel = CommunityChannel(**ch)
        db.add(channel)
        print(f"[seed] Channel created: {ch['name']}")
