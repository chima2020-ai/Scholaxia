"""
Database Seeder
---------------
Seeds only the community channels on startup.
Admin creates their own account via POST /api/v1/admin/register
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.community import CommunityChannel, ChannelType


async def seed_database(db: AsyncSession):
    await _seed_channels(db)
    await db.commit()


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
            continue
        channel = CommunityChannel(**ch)
        db.add(channel)
        print(f"[seed] Channel created: {ch['name']}")
