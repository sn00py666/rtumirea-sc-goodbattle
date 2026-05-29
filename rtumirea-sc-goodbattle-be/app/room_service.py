from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Language, MemberRole, Room, RoomLanguageLink, RoomMember, RoomStatus, RoomTaskLink, Task, User
from app.schemas import (
    RoomAiHintInfoResponse,
    BattleHistoryItemResponse,
    BattleTaskResponse,
    ParticipantResponse,
    ParticipantSolvedTasksResponse,
    RoomResponse,
    TaskExampleResponse,
)
from app.state import ParticipantRuntime, RoomRuntime, build_battle_results, ensure_room_runtime


async def get_member_for_user(session: AsyncSession, room_id: str, user_id: str) -> Optional[RoomMember]:
    member_query = select(RoomMember).where(
        RoomMember.room_id == room_id,
        RoomMember.user_id == user_id,
    )

    return (await session.exec(member_query)).first()


async def require_room_membership(session: AsyncSession, room_id: str, user: User) -> Tuple[Room, RoomMember]:
    room = await session.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail='Комната не найдена!')

    member = await get_member_for_user(session, room_id, user.id)
    if not member:
        raise HTTPException(status_code=403, detail='Нет доступа к комнате!')

    await hydrate_room_runtime(session, room)
    return room, member


async def require_organizer(session: AsyncSession, room_id: str, user: User) -> Tuple[Room, RoomMember]:
    room, member = await require_room_membership(session, room_id, user)
    if member.role != MemberRole.ORGANIZER:
        raise HTTPException(status_code=403, detail='Нет доступа к комнате!')

    return room, member


async def get_room_tasks(session: AsyncSession, room_id: str) -> List[Task]:
    result = await session.exec(
        select(Task)
        .join(RoomTaskLink, RoomTaskLink.task_id == Task.id)
        .where(RoomTaskLink.room_id == room_id)
        .order_by(RoomTaskLink.position, Task.created_at)
        .options(
            selectinload(Task.examples),
            selectinload(Task.test_cases),
        )
    )
    return list(result.all())


async def get_room_languages(session: AsyncSession, room_id: str) -> List[Language]:
    result = await session.exec(
        select(Language)
        .join(RoomLanguageLink, RoomLanguageLink.language_id == Language.id)
        .where(RoomLanguageLink.room_id == room_id)
        .order_by(RoomLanguageLink.position, Language.id)
    )
    return list(result.all())


async def hydrate_room_runtime(session: AsyncSession, room: Room) -> RoomRuntime:
    room_languages = await get_room_languages(session, room.id)
    room_tasks = await get_room_tasks(session, room.id)
    room_runtime = ensure_room_runtime(
        room.id,
        languages=[language.code for language in room_languages],
        task_ids=[task.id for task in room_tasks],
        time_limit=room.time_limit,
    )

    room_runtime.languages = [language.code for language in room_languages]
    room_runtime.task_ids = [task.id for task in room_tasks]
    room_runtime.time_limit = room.time_limit
    room_runtime.status = room.status.value
    room_runtime.current_task_index = room.current_task_index or 0
    default_language = room_runtime.languages[0] if room_runtime.languages else 'python'

    members_query = (
        select(RoomMember, User)
        .join(User, User.id == RoomMember.user_id)
        .where(RoomMember.room_id == room.id)
    )

    members = (await session.exec(members_query)).all()
    for room_member, member_user in members:
        if room_member.id not in room_runtime.participants:
            room_runtime.participants[room_member.id] = ParticipantRuntime(
                user_id=member_user.id,
                username=member_user.username,
                role=room_member.role.value,
                language=default_language,
            )
        else:
            participant = room_runtime.participants[room_member.id]
            participant.user_id = member_user.id
            participant.username = member_user.username
            participant.role = room_member.role.value
            if participant.language not in room_runtime.languages:
                participant.language = default_language

    return room_runtime


async def get_room_member_usernames(session: AsyncSession, room_id: str) -> dict[str, str]:
    members_query = (
        select(RoomMember, User)
        .join(User, User.id == RoomMember.user_id)
        .where(RoomMember.room_id == room_id)
    )

    members = (await session.exec(members_query)).all()
    return {member.id: member_user.username for member, member_user in members}


async def get_tasks_by_ids(session: AsyncSession, task_ids: List[str]) -> List[Task]:
    if not task_ids:
        return []

    result = await session.exec(
        select(Task)
        .where(Task.id.in_(task_ids))
        .options(
            selectinload(Task.examples),
            selectinload(Task.test_cases),
        )
    )
    tasks = list(result.all())
    order_by_id = {task_id: index for index, task_id in enumerate(task_ids)}
    tasks.sort(key=lambda task: order_by_id.get(task.id, len(task_ids)))
    return tasks


def build_task_response(task: Task) -> BattleTaskResponse:
    return BattleTaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        examples=[
            TaskExampleResponse(input=example.input_data, output=example.output_data)
            for example in task.examples
        ],
    )


def build_participant_response(participant_id: str, participant: ParticipantRuntime) -> ParticipantResponse:
    return ParticipantResponse(
        id=participant_id,
        user_id=participant.user_id,
        username=participant.username,
        role=participant.role,
        language=participant.language,
        code=participant.code,
    )


def build_participant_solved_tasks_response(participant: ParticipantRuntime, task_order: list[str]) -> ParticipantSolvedTasksResponse:
    return ParticipantSolvedTasksResponse(
        user_id=participant.user_id,
        solved_task_ids=[task_id for task_id in task_order if task_id in participant.solved_task_ids],
    )


def build_room_state_payload(room: Room, room_runtime: RoomRuntime) -> dict[str, Any]:
    return {
        'status': room_runtime.status,
        'currentTaskIndex': room_runtime.current_task_index,
        'remainingSeconds': get_room_remaining_seconds(room, room_runtime),
    }


def get_room_remaining_seconds(room: Room, room_runtime: RoomRuntime) -> int:
    if room.status == RoomStatus.FINISHED:
        return 0

    total_seconds = room_runtime.time_limit * 60
    if room.started_at is None:
        return total_seconds

    elapsed_seconds = max(int((datetime.now() - room.started_at).total_seconds()), 0)
    return max(total_seconds - elapsed_seconds, 0)


async def build_room_response(
        session: AsyncSession,
        room: Room,
        room_member: RoomMember,
        room_runtime: RoomRuntime,
) -> RoomResponse:
    room_tasks = await get_room_tasks(session, room.id)
    current_task_id = None
    if 0 <= room_runtime.current_task_index < len(room_runtime.task_ids):
        current_task_id = room_runtime.task_ids[room_runtime.current_task_index]

    current_participant = room_runtime.participants.get(room_member.id)
    hint_question = None
    hint_answer = None
    hint_used = False
    if current_participant is not None and current_task_id is not None:
        hint_used = current_task_id in current_participant.asked_ai_task_ids
        hint_payload = current_participant.ai_hint_history.get(current_task_id)
        if hint_payload is not None:
            hint_question = hint_payload.get('question')
            hint_answer = hint_payload.get('answer')

    return RoomResponse(
        id=room.id,
        code=room.join_code,
        status=room_runtime.status,
        role=room_member.role.value,
        current_task_index=room_runtime.current_task_index,
        total_tasks=len(room_runtime.task_ids),
        time_limit=room_runtime.time_limit,
        remaining_seconds=get_room_remaining_seconds(room, room_runtime),
        languages=room_runtime.languages,
        tasks=[build_task_response(task) for task in room_tasks],
        participants=[
            build_participant_response(participant_id, participant)
            for participant_id, participant in room_runtime.participants.items()
        ],
        participants_solved_tasks=[
            build_participant_solved_tasks_response(participant, room_runtime.task_ids)
            for participant in room_runtime.participants.values()
        ],
        ai_hint=RoomAiHintInfoResponse(
            task_id=current_task_id,
            used=hint_used,
            question=hint_question,
            answer=hint_answer,
        ),
    )


async def update_room_status(session: AsyncSession, room: Room, status: RoomStatus):
    room.status = status
    if status == RoomStatus.RUNNING and not room.started_at:
        room.started_at = datetime.now()

    if status == RoomStatus.FINISHED:
        room.finished_at = datetime.now()

    session.add(room)
    await session.commit()
    await session.refresh(room)


async def set_room_status(session: AsyncSession, room: Room, room_runtime: RoomRuntime, status: RoomStatus) -> dict[str, Any]:
    room_runtime.status = status.value
    room.current_task_index = room_runtime.current_task_index
    await update_room_status(session, room, status=status)
    return build_room_state_payload(room, room_runtime)


async def move_room_to_next_task(session: AsyncSession, room: Room, room_runtime: RoomRuntime) -> dict[str, Any]:
    if room_runtime.current_task_index + 1 >= len(room_runtime.task_ids):
        raise HTTPException(status_code=409, detail='Задач больше нет')

    room_runtime.current_task_index += 1
    return await set_room_status(session, room, room_runtime, RoomStatus.RUNNING)


def get_history_payload(
        room: Room,
        room_member: RoomMember,
        room_runtime: RoomRuntime,
) -> BattleHistoryItemResponse:
    results = build_battle_results(room_runtime)
    participant_count = len(room_runtime.participants)
    current_result = next((result for result in results if result.participant_id == room_member.id), None)
    date_source = room.finished_at or room.started_at or room.created_at

    return BattleHistoryItemResponse(
        id=room.id,
        title=room.title,
        date=date_source.strftime('%Y-%m-%d'),
        status='finished' if room.status == RoomStatus.FINISHED else 'in_progress',
        role=room_member.role.value,
        participants=participant_count,
        languages=room_runtime.languages,
        total_tasks=len(room_runtime.task_ids),
        solved_tasks=current_result.solved_tasks if current_result is not None else 0,
        place=current_result.place if room_member.role == MemberRole.PARTICIPANT and current_result is not None else None,
    )
