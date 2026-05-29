from __future__ import annotations

import os
import random
from collections import defaultdict
from datetime import datetime, timedelta

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import hash_password
from app.models import (
    AiHintEvent,
    BattleEvent,
    Language,
    MemberRole,
    Room,
    RoomLanguageLink,
    RoomMember,
    RoomStatus,
    RoomTaskLink,
    Submission,
    SubmissionStatus,
    SubmissionTestResult,
    Task,
    TestCase,
    User,
)

DEMO_FLAG_ENV = 'ANALYTICS_DEMO_SEED_ENABLED'
DEMO_OWNER_EMAIL = 'andrey42kot@gmail.com'
DEMO_OWNER_PASSWORD = 'qwerty123'
DEMO_OWNER_USERNAME = 'Andrey'
DEMO_MARKER_PREFIX = '[DEMO]'


def is_demo_seed_enabled() -> bool:
    raw_value = os.getenv(DEMO_FLAG_ENV, '').strip().lower()
    return raw_value in {'1', 'true', 'yes', 'on'}


async def seed_demo_analytics_data(session: AsyncSession) -> bool:
    rng = random.Random(42)

    owner = (await session.exec(select(User).where(User.email == DEMO_OWNER_EMAIL))).first()
    if owner is None:
        owner = User(
            email=DEMO_OWNER_EMAIL,
            username=DEMO_OWNER_USERNAME,
            password_hash=hash_password(DEMO_OWNER_PASSWORD),
            is_admin=True,
        )
        session.add(owner)
        await session.flush()
    else:
        owner.username = DEMO_OWNER_USERNAME
        owner.password_hash = hash_password(DEMO_OWNER_PASSWORD)
        owner.is_admin = True
        session.add(owner)

    marker_room = (
        await session.exec(select(Room.id).where(Room.title.startswith(DEMO_MARKER_PREFIX)))
    ).first()
    if marker_room is not None:
        await session.commit()
        return False

    languages = (await session.exec(select(Language).order_by(Language.id))).all()
    if not languages:
        await session.commit()
        return False

    tasks = (await session.exec(select(Task).order_by(Task.created_at))).all()
    if not tasks:
        await session.commit()
        return False

    test_cases = (await session.exec(select(TestCase))).all()
    test_cases_by_task = defaultdict(list)
    for test_case in test_cases:
        test_cases_by_task[test_case.task_id].append(test_case)

    bot_users: list[User] = []
    for idx in range(1, 20):
        email = f'demo_user_{idx:02d}@goodbattle.local'
        existing = (await session.exec(select(User).where(User.email == email))).first()
        if existing is None:
            existing = User(
                email=email,
                username=f'DemoUser{idx:02d}',
                password_hash=hash_password('demo12345'),
                is_admin=False,
            )
            session.add(existing)
            await session.flush()
        bot_users.append(existing)

    await session.flush()

    owner_org_room_count = 12
    owner_participant_room_count = 10

    await _build_owner_organizer_rooms(
        owner=owner,
        languages=languages,
        rng=rng,
        session=session,
        tasks=tasks,
        test_cases_by_task=test_cases_by_task,
        bot_users=bot_users,
        count=owner_org_room_count,
    )

    await _build_owner_participant_rooms(
        owner=owner,
        languages=languages,
        rng=rng,
        session=session,
        tasks=tasks,
        test_cases_by_task=test_cases_by_task,
        bot_users=bot_users,
        count=owner_participant_room_count,
    )

    await _build_extra_rooms(
        owner=owner,
        languages=languages,
        rng=rng,
        session=session,
        tasks=tasks,
        test_cases_by_task=test_cases_by_task,
        bot_users=bot_users,
    )

    await session.commit()
    return True


async def _build_owner_organizer_rooms(
    *,
    owner: User,
    languages: list[Language],
    rng: random.Random,
    session: AsyncSession,
    tasks: list[Task],
    test_cases_by_task: dict[str, list[TestCase]],
    bot_users: list[User],
    count: int,
) -> list[Room]:
    rooms: list[Room] = []
    for index in range(count):
        status = RoomStatus.FINISHED if index < count - 2 else RoomStatus.RUNNING
        now = datetime.now()
        days_ago = 40 - index
        started_at = now - timedelta(days=days_ago, minutes=15)
        finished_at = None
        if status == RoomStatus.FINISHED:
            finished_at = started_at + timedelta(minutes=rng.randint(4, 9))

        room = Room(
            title=f'{DEMO_MARKER_PREFIX} OwnerOrg #{index + 1:02d}',
            join_code=f'DEMOOG{index + 1:02d}',
            creator_id=owner.id,
            status=status,
            time_limit=rng.randint(5, 10),
            current_task_index=rng.randint(0, 2),
            started_at=started_at,
            finished_at=finished_at,
            created_at=started_at - timedelta(minutes=5),
        )
        session.add(room)
        await session.flush()

        chosen_tasks = _pick_tasks(tasks, rng, count=rng.randint(3, 4))
        chosen_languages = _pick_languages(languages, rng, count=rng.randint(2, 4))
        _attach_tasks_and_languages(
            room=room,
            chosen_languages=chosen_languages,
            chosen_tasks=chosen_tasks,
            session=session,
        )

        organizer_member = RoomMember(
            room_id=room.id,
            user_id=owner.id,
            role=MemberRole.ORGANIZER,
            joined_at=room.created_at,
        )
        session.add(organizer_member)

        participants = rng.sample(bot_users, k=rng.randint(5, 8))
        participant_members = [
            RoomMember(
                room_id=room.id,
                user_id=participant.id,
                role=MemberRole.PARTICIPANT,
                joined_at=room.created_at + timedelta(minutes=1),
            )
            for participant in participants
        ]
        session.add_all(participant_members)
        await session.flush()

        if status == RoomStatus.FINISHED:
            _insert_battle_events(
                organizer_user_id=owner.id,
                room=room,
                rng=rng,
                session=session,
                task_ids=[task.id for task in chosen_tasks],
            )
            await _insert_submissions_for_members(
                room=room,
                rng=rng,
                session=session,
                task_ids=[task.id for task in chosen_tasks],
                test_cases_by_task=test_cases_by_task,
                language_ids=[language.id for language in chosen_languages],
                participant_members=participant_members,
                hint_probability=0.35,
                force_owner_participant=False,
            )

        rooms.append(room)

    return rooms


async def _build_owner_participant_rooms(
    *,
    owner: User,
    languages: list[Language],
    rng: random.Random,
    session: AsyncSession,
    tasks: list[Task],
    test_cases_by_task: dict[str, list[TestCase]],
    bot_users: list[User],
    count: int,
) -> None:
    for index in range(count):
        organizer = bot_users[index % len(bot_users)]
        now = datetime.now()
        days_ago = 20 - index
        started_at = now - timedelta(days=days_ago, minutes=10)
        finished_at = started_at + timedelta(minutes=rng.randint(4, 12))

        room = Room(
            title=f'{DEMO_MARKER_PREFIX} OwnerPart #{index + 1:02d}',
            join_code=f'DEMOOP{index + 1:02d}',
            creator_id=organizer.id,
            status=RoomStatus.FINISHED,
            time_limit=rng.randint(6, 12),
            current_task_index=rng.randint(0, 2),
            started_at=started_at,
            finished_at=finished_at,
            created_at=started_at - timedelta(minutes=4),
        )
        session.add(room)
        await session.flush()

        chosen_tasks = _pick_tasks(tasks, rng, count=rng.randint(3, 5))
        chosen_languages = _pick_languages(languages, rng, count=rng.randint(2, 4))
        _attach_tasks_and_languages(
            room=room,
            chosen_languages=chosen_languages,
            chosen_tasks=chosen_tasks,
            session=session,
        )

        organizer_member = RoomMember(
            room_id=room.id,
            user_id=organizer.id,
            role=MemberRole.ORGANIZER,
            joined_at=room.created_at,
        )
        session.add(organizer_member)

        participants_pool = [user for user in bot_users if user.id != organizer.id]
        participants = rng.sample(participants_pool, k=rng.randint(4, 7))
        if all(participant.id != owner.id for participant in participants):
            participants[0] = owner

        participant_members = [
            RoomMember(
                room_id=room.id,
                user_id=participant.id,
                role=MemberRole.PARTICIPANT,
                joined_at=room.created_at + timedelta(minutes=1),
            )
            for participant in participants
        ]
        session.add_all(participant_members)
        await session.flush()

        _insert_battle_events(
            organizer_user_id=organizer.id,
            room=room,
            rng=rng,
            session=session,
            task_ids=[task.id for task in chosen_tasks],
        )
        await _insert_submissions_for_members(
            room=room,
            rng=rng,
            session=session,
            task_ids=[task.id for task in chosen_tasks],
            test_cases_by_task=test_cases_by_task,
            language_ids=[language.id for language in chosen_languages],
            participant_members=participant_members,
            hint_probability=0.4,
            force_owner_participant=True,
            owner_user_id=owner.id,
        )


async def _build_extra_rooms(
    *,
    owner: User,
    languages: list[Language],
    rng: random.Random,
    session: AsyncSession,
    tasks: list[Task],
    test_cases_by_task: dict[str, list[TestCase]],
    bot_users: list[User],
) -> None:
    for index in range(12):
        organizer = bot_users[(index + 7) % len(bot_users)]
        status = RoomStatus.FINISHED if index < 9 else RoomStatus.WAITING
        now = datetime.now()
        days_ago = 60 - index
        started_at = now - timedelta(days=days_ago, minutes=12) if status != RoomStatus.WAITING else None
        finished_at = started_at + timedelta(minutes=rng.randint(5, 11)) if status == RoomStatus.FINISHED and started_at else None

        room = Room(
            title=f'{DEMO_MARKER_PREFIX} Extra #{index + 1:02d}',
            join_code=f'DEMOEX{index + 1:02d}',
            creator_id=organizer.id,
            status=status,
            time_limit=rng.randint(5, 12),
            current_task_index=0,
            started_at=started_at,
            finished_at=finished_at,
            created_at=(started_at - timedelta(minutes=5)) if started_at else now - timedelta(days=days_ago, minutes=5),
        )
        session.add(room)
        await session.flush()

        chosen_tasks = _pick_tasks(tasks, rng, count=rng.randint(2, 4))
        chosen_languages = _pick_languages(languages, rng, count=rng.randint(2, 4))
        _attach_tasks_and_languages(
            room=room,
            chosen_languages=chosen_languages,
            chosen_tasks=chosen_tasks,
            session=session,
        )

        session.add(
            RoomMember(
                room_id=room.id,
                user_id=organizer.id,
                role=MemberRole.ORGANIZER,
                joined_at=room.created_at,
            )
        )

        participants = rng.sample(bot_users + [owner], k=rng.randint(3, 8))
        participant_members = [
            RoomMember(
                room_id=room.id,
                user_id=participant.id,
                role=MemberRole.PARTICIPANT,
                joined_at=room.created_at + timedelta(minutes=1),
            )
            for participant in participants
        ]
        session.add_all(participant_members)
        await session.flush()

        if status == RoomStatus.FINISHED:
            _insert_battle_events(
                organizer_user_id=organizer.id,
                room=room,
                rng=rng,
                session=session,
                task_ids=[task.id for task in chosen_tasks],
            )
            await _insert_submissions_for_members(
                room=room,
                rng=rng,
                session=session,
                task_ids=[task.id for task in chosen_tasks],
                test_cases_by_task=test_cases_by_task,
                language_ids=[language.id for language in chosen_languages],
                participant_members=participant_members,
                hint_probability=0.3,
                force_owner_participant=False,
            )


def _attach_tasks_and_languages(
    *,
    room: Room,
    chosen_languages: list[Language],
    chosen_tasks: list[Task],
    session: AsyncSession,
) -> None:
    session.add_all([
        RoomLanguageLink(room_id=room.id, language_id=language.id, position=index)
        for index, language in enumerate(chosen_languages)
    ])
    session.add_all([
        RoomTaskLink(room_id=room.id, task_id=task.id, position=index)
        for index, task in enumerate(chosen_tasks)
    ])


def _pick_tasks(tasks: list[Task], rng: random.Random, *, count: int) -> list[Task]:
    count = min(max(1, count), len(tasks))
    return rng.sample(tasks, k=count)


def _pick_languages(languages: list[Language], rng: random.Random, *, count: int) -> list[Language]:
    count = min(max(1, count), len(languages))
    return rng.sample(languages, k=count)


def _insert_battle_events(
    *,
    organizer_user_id: str,
    room: Room,
    rng: random.Random,
    session: AsyncSession,
    task_ids: list[str],
) -> None:
    if room.started_at is None:
        return

    events = [
        BattleEvent(
            room_id=room.id,
            user_id=organizer_user_id,
            task_id=None,
            event_type='start_battle',
            created_at=room.started_at,
        )
    ]

    cursor = room.started_at + timedelta(minutes=1)
    for task_id in task_ids[1:]:
        if room.finished_at is not None and cursor >= room.finished_at:
            break
        events.append(
            BattleEvent(
                room_id=room.id,
                user_id=organizer_user_id,
                task_id=task_id,
                event_type='next_task',
                created_at=cursor,
            )
        )
        cursor += timedelta(minutes=rng.randint(1, 2))

    if rng.random() < 0.2 and room.finished_at is not None:
        pause_time = room.started_at + timedelta(minutes=2)
        if pause_time < room.finished_at:
            events.append(
                BattleEvent(
                    room_id=room.id,
                    user_id=organizer_user_id,
                    task_id=None,
                    event_type='pause_battle',
                    created_at=pause_time,
                )
            )

    if room.finished_at is not None:
        events.append(
            BattleEvent(
                room_id=room.id,
                user_id=organizer_user_id,
                task_id=None,
                event_type='finish_battle',
                reason='timer' if rng.random() < 0.45 else 'manual',
                created_at=room.finished_at,
            )
        )

    session.add_all(events)


async def _insert_submissions_for_members(
    *,
    room: Room,
    rng: random.Random,
    session: AsyncSession,
    task_ids: list[str],
    test_cases_by_task: dict[str, list[TestCase]],
    language_ids: list[int],
    participant_members: list[RoomMember],
    hint_probability: float,
    force_owner_participant: bool,
    owner_user_id: str | None = None,
) -> None:
    if room.started_at is None:
        return

    room_duration_seconds = room.time_limit * 60
    deadline = room.finished_at or (room.started_at + timedelta(seconds=room_duration_seconds))

    for member in participant_members:
        solved_target = rng.randint(0, len(task_ids))
        if force_owner_participant and owner_user_id and member.user_id == owner_user_id:
            solved_target = max(1, min(len(task_ids), rng.randint(2, len(task_ids))))

        solved_counter = 0
        had_hint = False

        for task_index, task_id in enumerate(task_ids):
            attempts = rng.randint(1, 5)
            if force_owner_participant and owner_user_id and member.user_id == owner_user_id:
                attempts = rng.randint(2, 6)

            should_solve = solved_counter < solved_target and rng.random() < 0.85
            pass_attempt = rng.randint(2, attempts) if should_solve and attempts > 1 else (1 if should_solve else None)

            for attempt_index in range(1, attempts + 1):
                if should_solve and pass_attempt == attempt_index:
                    verdict = SubmissionStatus.ACCEPTED
                else:
                    verdict = rng.choice([
                        SubmissionStatus.WRONG_ANSWER,
                        SubmissionStatus.RUNTIME_ERROR,
                        SubmissionStatus.TIME_LIMIT_EXCEEDED,
                        SubmissionStatus.COMPILE_ERROR,
                    ])

                seconds_offset = int((task_index * 70) + attempt_index * rng.randint(15, 35))
                created_at = room.started_at + timedelta(seconds=seconds_offset)
                if created_at > deadline:
                    created_at = deadline - timedelta(seconds=rng.randint(5, 30))

                submission = Submission(
                    room_id=room.id,
                    user_id=member.user_id,
                    task_id=task_id,
                    language_id=rng.choice(language_ids),
                    source_code=_fake_source_code(task_id=task_id, verdict=verdict, attempt=attempt_index),
                    verdict=verdict,
                    created_at=created_at,
                    finished_at=created_at + timedelta(seconds=1),
                    execution_time_ms=rng.randint(30, 400),
                    execution_memory_kb=rng.randint(1000, 12000),
                )
                session.add(submission)
                await session.flush()

                task_tests = test_cases_by_task.get(task_id, [])
                session.add_all([
                    SubmissionTestResult(
                        submission_id=submission.id,
                        test_id=test_case.id,
                        verdict=verdict if verdict != SubmissionStatus.ACCEPTED else SubmissionStatus.ACCEPTED,
                        execution_time_ms=rng.randint(5, 120),
                        execution_memory_kb=rng.randint(200, 2000),
                        error_message='' if verdict == SubmissionStatus.ACCEPTED else verdict.value,
                    )
                    for test_case in task_tests
                ])

                session.add(
                    BattleEvent(
                        room_id=room.id,
                        user_id=member.user_id,
                        task_id=task_id,
                        event_type='run_code',
                        created_at=created_at,
                    )
                )

                if verdict == SubmissionStatus.ACCEPTED:
                    solved_counter += 1
                    session.add(
                        BattleEvent(
                            room_id=room.id,
                            user_id=member.user_id,
                            task_id=task_id,
                            event_type='task_solved',
                            created_at=created_at,
                        )
                    )
                    break

            if not had_hint and rng.random() < hint_probability:
                hint_time = room.started_at + timedelta(seconds=(task_index + 1) * rng.randint(40, 75))
                if hint_time < deadline:
                    session.add(
                        AiHintEvent(
                            room_id=room.id,
                            user_id=member.user_id,
                            task_id=task_id,
                            question='Почему тесты падают на скрытых кейсах?',
                            answer='Проверьте обработку пустого ввода и крайних значений.',
                            created_at=hint_time,
                        )
                    )
                    session.add(
                        BattleEvent(
                            room_id=room.id,
                            user_id=member.user_id,
                            task_id=task_id,
                            event_type='ask_ai_hint',
                            created_at=hint_time,
                        )
                    )
                    had_hint = True


def _fake_source_code(*, task_id: str, verdict: SubmissionStatus, attempt: int) -> str:
    if verdict == SubmissionStatus.ACCEPTED:
        return f"# accepted attempt {attempt}\nprint('ok for {task_id[:8]}')\n"

    if verdict == SubmissionStatus.COMPILE_ERROR:
        return "print('oops'\n"

    if verdict == SubmissionStatus.RUNTIME_ERROR:
        return "arr=[]\nprint(arr[1])\n"

    if verdict == SubmissionStatus.TIME_LIMIT_EXCEEDED:
        return "while True:\n    pass\n"

    return "print('wrong answer')\n"
