from __future__ import annotations

import random
import string

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_async_session
from app.dependencies import get_current_user
from app.models import Language, MemberRole, Room, RoomLanguageLink, RoomMember, RoomTaskLink, User
from app.room_service import (
    build_room_response,
    get_member_for_user,
    get_tasks_by_ids,
    hydrate_room_runtime,
    require_room_membership,
)
from app.schemas import CreateRoomRequest, CreateRoomResponse, JoinRoomRequest, JoinRoomResponse, RoomResponse
from app.state import MAX_ROOM_PARTICIPANTS, ParticipantRuntime, create_room_runtime

router = APIRouter()


def generate_join_code(length: int = 8) -> str:
    allowed_characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(allowed_characters, k=length))


async def generate_unique_join_code(session: AsyncSession) -> str:
    while True:
        join_code = generate_join_code()
        existing_room = (await session.exec(select(Room).where(Room.join_code == join_code))).first()
        if existing_room is None:
            return join_code


@router.post('/rooms', response_model=CreateRoomResponse, status_code=201)
async def create_room(
        request: CreateRoomRequest,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session),
) -> CreateRoomResponse:
    if len(set(request.languages)) != len(request.languages):
        raise HTTPException(status_code=400, detail='Duplicate language')

    if len(set(request.task_ids)) != len(request.task_ids):
        raise HTTPException(status_code=400, detail='Duplicate task')

    languages = (
        await session.exec(
            select(Language)
            .where(Language.code.in_(request.languages))
            .order_by(Language.id)
        )
    ).all()

    language_by_code = {language.code: language for language in languages}
    if len(language_by_code) != len(request.languages):
        raise HTTPException(status_code=400, detail='Unsupported language')

    tasks = await get_tasks_by_ids(session, request.task_ids)
    if len(tasks) != len(request.task_ids):
        raise HTTPException(status_code=404, detail='Не найдено')

    join_code = await generate_unique_join_code(session)
    new_room = Room(
        title=f'Баттл {join_code}',
        join_code=join_code,
        creator_id=user.id,
        time_limit=request.time_limit,
    )

    session.add(new_room)
    await session.flush()

    session.add_all([
        RoomLanguageLink(room_id=new_room.id, language_id=language_by_code[language_code].id, position=index)
        for index, language_code in enumerate(request.languages)
    ])

    session.add_all([
        RoomTaskLink(room_id=new_room.id, task_id=task_id, position=index)
        for index, task_id in enumerate(request.task_ids)
    ])

    await session.commit()
    await session.refresh(new_room)

    organizer_member = RoomMember(room_id=new_room.id, user_id=user.id, role=MemberRole.ORGANIZER)
    session.add(organizer_member)
    await session.commit()
    await session.refresh(organizer_member)

    room_runtime = create_room_runtime(
        new_room.id,
        languages=request.languages,
        task_ids=request.task_ids,
        time_limit=request.time_limit,
    )
    default_language = request.languages[0]

    room_runtime.participants[organizer_member.id] = ParticipantRuntime(
        user_id=user.id,
        username=user.username,
        role=organizer_member.role.value,
        language=default_language,
    )

    return CreateRoomResponse(room_id=new_room.id, code=new_room.join_code)


@router.post('/rooms/join', response_model=JoinRoomResponse)
async def join_room(
        request: JoinRoomRequest,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session),
) -> JoinRoomResponse:
    room = (await session.exec(select(Room).where(Room.join_code == request.code))).first()
    if room is None:
        raise HTTPException(status_code=404, detail='Комната с таким кодом не найдена!')

    existing_member = await get_member_for_user(session, room.id, user.id)
    if existing_member is not None:
        return JoinRoomResponse(participant_id=existing_member.id, room_id=room.id)

    room_runtime = await hydrate_room_runtime(session, room)
    if room.status.value != 'waiting':
        raise HTTPException(status_code=409, detail='Баттл уже начался!')

    participant_count = len(
        (
            await session.exec(
                select(RoomMember).where(
                    RoomMember.room_id == room.id,
                    RoomMember.role == MemberRole.PARTICIPANT,
                )
            )
        ).all()
    )

    if participant_count >= MAX_ROOM_PARTICIPANTS:
        raise HTTPException(status_code=409, detail='Комната заполнена')

    participant_member = RoomMember(room_id=room.id, user_id=user.id, role=MemberRole.PARTICIPANT)
    session.add(participant_member)
    await session.commit()
    await session.refresh(participant_member)

    room_runtime.participants[participant_member.id] = ParticipantRuntime(
        user_id=user.id,
        username=user.username,
        role=participant_member.role.value,
        language=room_runtime.languages[0] if room_runtime.languages else 'python',
    )

    return JoinRoomResponse(participant_id=participant_member.id, room_id=room.id)


@router.get('/rooms/{room_id}', response_model=RoomResponse)
async def get_room_details(room_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_async_session)) -> RoomResponse:
    room, member = await require_room_membership(session, room_id, user)
    room_runtime = await hydrate_room_runtime(session, room)
    return await build_room_response(session, room, member, room_runtime)
