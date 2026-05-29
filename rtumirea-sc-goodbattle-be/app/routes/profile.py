from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_async_session
from app.dependencies import get_current_user
from app.models import MemberRole, Room, RoomMember, RoomStatus, User
from app.room_service import hydrate_room_runtime
from app.schemas import ProfileResponse

router = APIRouter()


@router.get('/profile', response_model=ProfileResponse)
async def get_profile(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_async_session)) -> ProfileResponse:
    member_query = (
        select(RoomMember, Room)
        .join(Room, Room.id == RoomMember.room_id)
        .where(RoomMember.user_id == user.id)
    )

    memberships = (await session.exec(member_query)).all()
    battles_played = sum(1 for member, _room in memberships if member.role == MemberRole.PARTICIPANT)
    battles_organized = sum(1 for member, _room in memberships if member.role == MemberRole.ORGANIZER)
    total_battles = battles_played + battles_organized

    wins_count = 0
    languages_used = defaultdict(int)

    for member, room in memberships:
        room_runtime = await hydrate_room_runtime(session, room)
        participant = room_runtime.participants.get(member.id)
        if participant is None:
            continue

        languages_used[participant.language] += 1
        if room.status == RoomStatus.FINISHED:
            sorted_members = sorted(
                room_runtime.participants.items(),
                key=lambda item: (
                    -len(item[1].solved_task_ids),
                    item[1].total_time_seconds,
                    item[0],
                ),
            )

            if sorted_members and sorted_members[0][0] == member.id:
                wins_count += 1

    top_language = max(languages_used, key=languages_used.get) if languages_used else None
    win_rate = round((wins_count / total_battles) * 100) if total_battles else 0

    return ProfileResponse(
        email=user.email,
        username=user.username,
        created_at=user.created_at,
        top_language=top_language,
        battles_played=battles_played,
        battles_organized=battles_organized,
        win_rate=win_rate,
        wins_count=wins_count,
    )
