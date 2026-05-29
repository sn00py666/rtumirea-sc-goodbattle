from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_async_session
from app.dependencies import get_current_user
from app.models import Room, RoomMember, User
from app.room_service import get_history_payload, get_room_member_usernames, hydrate_room_runtime
from app.schemas import BattleHistoryItemResponse

router = APIRouter()


@router.get('/battles', response_model=List[BattleHistoryItemResponse])
async def list_battles(
        role: Optional[str] = Query(default=None),
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session),
) -> List[BattleHistoryItemResponse]:
    memberships_query = (
        select(RoomMember, Room)
        .join(Room, Room.id == RoomMember.room_id)
        .where(RoomMember.user_id == user.id)
    )

    battle_history = []
    for member, room in (await session.exec(memberships_query)).all():
        if role is not None and member.role.value != role:
            continue

        room_runtime = await hydrate_room_runtime(session, room)
        battle_history.append(get_history_payload(room, member, room_runtime))

    battle_history.sort(key=lambda item: item.date, reverse=True)
    return battle_history
