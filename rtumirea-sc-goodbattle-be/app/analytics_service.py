from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean
from typing import Iterable, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

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
    SubmissionTestResult,
    SubmissionStatus,
    Task,
    User,
)
from app.schemas import (
    AdminFunnelResponse,
    AdminPlatformAnalyticsResponse,
    AnalyticsBattleListItemResponse,
    AnalyticsFrequencyResponse,
    AnalyticsHeatmapCellResponse,
    BattleDetailAnalyticsResponse,
    BattleParticipantAnalyticsResponse,
    BattleSubmissionAnalyticsResponse,
    BattleSubmissionTestResultAnalyticsResponse,
    BattleTaskAnalyticsResponse,
    OrganizerAnalyticsResponse,
    ParticipantAnalyticsResponse,
    PeakLoadBucketResponse,
    TaskPlatformAnalyticsResponse,
)


@dataclass(slots=True)
class RoomSnapshot:
    average_submissions_per_task: float
    average_time_to_solve_seconds: Optional[float]
    battle: Room
    finish_reason: Optional[str]
    hint_usage_share: float
    leaderboard: list[BattleParticipantAnalyticsResponse]
    languages: list[str]
    participants_without_ac_count: int
    problematic_tasks: list[BattleTaskAnalyticsResponse]
    solved_percent: float
    submissions: list[BattleSubmissionAnalyticsResponse]
    tasks: list[BattleTaskAnalyticsResponse]


def _safe_percent(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _mean_or_none(values: Iterable[float]) -> Optional[float]:
    values_list = list(values)
    if not values_list:
        return None
    return round(float(mean(values_list)), 2)


def _room_date(room: Room) -> datetime:
    return room.finished_at or room.started_at or room.created_at


def _room_date_str(room: Room) -> str:
    return _room_date(room).strftime('%Y-%m-%d')


def _room_start_time(room: Room) -> datetime:
    return room.started_at or room.created_at


def _room_deadline(room: Room) -> datetime:
    if room.finished_at is not None:
        return room.finished_at
    return _room_start_time(room) + timedelta(minutes=room.time_limit)


async def _load_room_snapshots(session: AsyncSession, rooms: list[Room]) -> dict[str, RoomSnapshot]:
    if not rooms:
        return {}

    room_ids = [room.id for room in rooms]

    participant_members = (
        await session.exec(
            select(RoomMember)
            .where(
                RoomMember.room_id.in_(room_ids),
                RoomMember.role == MemberRole.PARTICIPANT,
            )
        )
    ).all()
    members_by_room: dict[str, list[RoomMember]] = defaultdict(list)
    member_user_ids = set()
    for member in participant_members:
        members_by_room[member.room_id].append(member)
        member_user_ids.add(member.user_id)

    users = (await session.exec(select(User).where(User.id.in_(member_user_ids)))).all() if member_user_ids else []
    user_by_id = {user.id: user for user in users}
    languages = (await session.exec(select(Language))).all()
    language_code_by_id = {language.id: language.code for language in languages}

    submissions = (
        await session.exec(
            select(Submission)
            .where(Submission.room_id.in_(room_ids))
            .order_by(Submission.created_at)
        )
    ).all()
    submissions_by_room: dict[str, list[Submission]] = defaultdict(list)
    for submission in submissions:
        submissions_by_room[submission.room_id].append(submission)
    submission_ids = [submission.id for submission in submissions]
    submission_test_results = (
        await session.exec(
            select(SubmissionTestResult)
            .where(SubmissionTestResult.submission_id.in_(submission_ids))
            .order_by(SubmissionTestResult.submission_id, SubmissionTestResult.test_id)
        )
    ).all() if submission_ids else []
    test_results_by_submission: dict[str, list[SubmissionTestResult]] = defaultdict(list)
    for test_result in submission_test_results:
        test_results_by_submission[test_result.submission_id].append(test_result)

    hint_events = (
        await session.exec(select(AiHintEvent).where(AiHintEvent.room_id.in_(room_ids)))
    ).all()
    hints_by_room: dict[str, list[AiHintEvent]] = defaultdict(list)
    for hint_event in hint_events:
        hints_by_room[hint_event.room_id].append(hint_event)

    battle_events = (
        await session.exec(
            select(BattleEvent)
            .where(BattleEvent.room_id.in_(room_ids), BattleEvent.event_type == 'finish_battle')
            .order_by(BattleEvent.created_at.desc())
        )
    ).all()
    finish_reason_by_room: dict[str, str] = {}
    for event in battle_events:
        if event.room_id not in finish_reason_by_room and event.reason:
            finish_reason_by_room[event.room_id] = event.reason

    room_tasks_rows = (
        await session.exec(
            select(RoomTaskLink, Task)
            .join(Task, Task.id == RoomTaskLink.task_id)
            .where(RoomTaskLink.room_id.in_(room_ids))
            .order_by(RoomTaskLink.room_id, RoomTaskLink.position)
        )
    ).all()
    tasks_by_room: dict[str, list[Task]] = defaultdict(list)
    for room_task_link, task in room_tasks_rows:
        tasks_by_room[room_task_link.room_id].append(task)

    room_languages_rows = (
        await session.exec(
            select(RoomLanguageLink, Language)
            .join(Language, Language.id == RoomLanguageLink.language_id)
            .where(RoomLanguageLink.room_id.in_(room_ids))
            .order_by(RoomLanguageLink.room_id, RoomLanguageLink.position)
        )
    ).all()
    languages_by_room: dict[str, list[str]] = defaultdict(list)
    for room_language_link, language in room_languages_rows:
        languages_by_room[room_language_link.room_id].append(language.code)

    snapshots: dict[str, RoomSnapshot] = {}
    for room in rooms:
        snapshots[room.id] = _build_room_snapshot(
            battle=room,
            finish_reason=finish_reason_by_room.get(room.id),
            hints=hints_by_room.get(room.id, []),
            members=members_by_room.get(room.id, []),
            submissions=submissions_by_room.get(room.id, []),
            test_results_by_submission=test_results_by_submission,
            tasks=tasks_by_room.get(room.id, []),
            languages=languages_by_room.get(room.id, []),
            language_code_by_id=language_code_by_id,
            user_by_id=user_by_id,
        )

    return snapshots


def _build_room_snapshot(
    *,
    battle: Room,
    finish_reason: Optional[str],
    hints: list[AiHintEvent],
    members: list[RoomMember],
    submissions: list[Submission],
    test_results_by_submission: dict[str, list[SubmissionTestResult]],
    tasks: list[Task],
    languages: list[str],
    language_code_by_id: dict[int, str],
    user_by_id: dict[str, User],
) -> RoomSnapshot:
    task_ids = [task.id for task in tasks]
    participant_count = len(members)
    start_time = _room_start_time(battle)
    deadline = _room_deadline(battle)

    submissions_by_user_task: dict[tuple[str, str], list[Submission]] = defaultdict(list)
    submissions_count_by_user: Counter[str] = Counter()
    for submission in submissions:
        submissions_by_user_task[(submission.user_id, submission.task_id)].append(submission)
        submissions_count_by_user[submission.user_id] += 1

    hints_by_user = {hint.user_id for hint in hints}

    solved_task_ids_by_user: dict[str, set[str]] = defaultdict(set)
    first_ac_time_by_user_task: dict[tuple[str, str], datetime] = {}
    all_ac_time_seconds: list[int] = []

    for (user_id, task_id), task_submissions in submissions_by_user_task.items():
        accepted_submissions = [
            submission
            for submission in task_submissions
            if submission.verdict == SubmissionStatus.ACCEPTED and submission.created_at <= deadline
        ]
        if not accepted_submissions:
            continue

        first_ac = min(accepted_submissions, key=lambda submission: submission.created_at)
        solved_task_ids_by_user[user_id].add(task_id)
        first_ac_time_by_user_task[(user_id, task_id)] = first_ac.created_at
        elapsed_seconds = max(int((first_ac.created_at - start_time).total_seconds()), 0)
        all_ac_time_seconds.append(elapsed_seconds)

    leaderboard: list[BattleParticipantAnalyticsResponse] = []
    members_sorted = sorted(
        members,
        key=lambda member: (
            -len(solved_task_ids_by_user.get(member.user_id, set())),
            _sum_user_solve_time_seconds(
                first_ac_time_by_user_task,
                start_time,
                member.user_id,
                task_ids,
            ),
            member.id,
        ),
    )

    for place, member in enumerate(members_sorted, start=1):
        user = user_by_id.get(member.user_id)
        if user is None:
            continue

        leaderboard.append(
            BattleParticipantAnalyticsResponse(
                participant_id=member.id,
                user_id=member.user_id,
                username=user.username,
                place=place,
                solved_tasks=len(solved_task_ids_by_user.get(member.user_id, set())),
                total_time_seconds=_sum_user_solve_time_seconds(
                    first_ac_time_by_user_task,
                    start_time,
                    member.user_id,
                    task_ids,
                ),
                submissions_count=int(submissions_count_by_user.get(member.user_id, 0)),
                hint_used=member.user_id in hints_by_user,
            )
        )

    tasks_stats: list[BattleTaskAnalyticsResponse] = []
    problematic_tasks: list[tuple[float, int, BattleTaskAnalyticsResponse]] = []
    for task in tasks:
        task_submissions = [submission for submission in submissions if submission.task_id == task.id]
        task_attempts_by_user: Counter[str] = Counter(submission.user_id for submission in task_submissions)
        task_solved_user_ids = {
            user_id
            for (user_id, task_id), _time in first_ac_time_by_user_task.items()
            if task_id == task.id
        }

        solve_times = [
            max(int((ac_time - start_time).total_seconds()), 0)
            for (user_id, task_id), ac_time in first_ac_time_by_user_task.items()
            if task_id == task.id and user_id in task_solved_user_ids
        ]

        error_counter = Counter(
            submission.verdict.value
            for submission in task_submissions
            if submission.verdict != SubmissionStatus.ACCEPTED
        )
        error_frequencies = [
            AnalyticsFrequencyResponse(key=key, count=int(count))
            for key, count in sorted(error_counter.items(), key=lambda item: (-item[1], item[0]))
        ]

        average_submissions = 0.0
        if participant_count > 0:
            average_submissions = round(len(task_submissions) / participant_count, 2)

        solved_percent = _safe_percent(len(task_solved_user_ids), participant_count)
        first_ac_time_seconds = min(solve_times) if solve_times else None
        task_stat = BattleTaskAnalyticsResponse(
            task_id=task.id,
            title=task.title,
            average_time_to_ac_seconds=_mean_or_none(solve_times),
            average_submissions=average_submissions,
            solved_percent=solved_percent,
            error_frequencies=error_frequencies,
            first_ac_time_seconds=first_ac_time_seconds,
        )
        tasks_stats.append(task_stat)

        problematic_tasks.append((task_stat.solved_percent, len(error_counter), task_stat))

    problematic_tasks_sorted = [
        item[2]
        for item in sorted(
            problematic_tasks,
            key=lambda row: (row[0], -row[1], row[2].title),
        )
    ][:3]

    participants_without_ac_count = sum(
        1
        for member in members
        if len(solved_task_ids_by_user.get(member.user_id, set())) == 0
    )

    submissions_payload = [
        _build_submission_payload(
            submission=submission,
            language_code_by_id=language_code_by_id,
            test_results=test_results_by_submission.get(submission.id, []),
            username=user_by_id.get(submission.user_id).username if user_by_id.get(submission.user_id) else 'Unknown',
        )
        for submission in sorted(
            submissions,
            key=lambda item: item.created_at,
            reverse=True,
        )
    ]

    total_possible_solves = participant_count * max(len(tasks), 1)
    total_solves = sum(len(solved_task_ids_by_user.get(member.user_id, set())) for member in members)

    hint_usage_share = _safe_percent(len(hints_by_user), participant_count)

    return RoomSnapshot(
        battle=battle,
        finish_reason=finish_reason,
        leaderboard=leaderboard,
        languages=languages,
        tasks=tasks_stats,
        problematic_tasks=problematic_tasks_sorted,
        submissions=submissions_payload,
        participants_without_ac_count=participants_without_ac_count,
        hint_usage_share=hint_usage_share,
        solved_percent=_safe_percent(total_solves, total_possible_solves),
        average_time_to_solve_seconds=_mean_or_none(all_ac_time_seconds),
        average_submissions_per_task=round(len(submissions) / total_possible_solves, 2) if total_possible_solves else 0.0,
    )


def _build_submission_payload(
    *,
    submission: Submission,
    language_code_by_id: dict[int, str],
    test_results: list[SubmissionTestResult],
    username: str,
) -> BattleSubmissionAnalyticsResponse:
    passed_tests = sum(
        1 for test_result in test_results if test_result.verdict == SubmissionStatus.ACCEPTED
    )
    total_tests = len(test_results)
    failed_tests = max(total_tests - passed_tests, 0)

    return BattleSubmissionAnalyticsResponse(
        submission_id=submission.id,
        user_id=submission.user_id,
        username=username,
        task_id=submission.task_id,
        language=language_code_by_id.get(submission.language_id, str(submission.language_id)),
        verdict=submission.verdict.value,
        created_at=submission.created_at,
        execution_time_ms=submission.execution_time_ms,
        execution_memory_kb=submission.execution_memory_kb,
        passed_tests=passed_tests,
        failed_tests=failed_tests,
        total_tests=total_tests,
        test_results=[
            BattleSubmissionTestResultAnalyticsResponse(
                test_id=test_result.test_id,
                verdict=test_result.verdict.value,
                execution_time_ms=test_result.execution_time_ms,
                execution_memory_kb=test_result.execution_memory_kb,
                error_message=test_result.error_message,
            )
            for test_result in test_results
        ],
        source_code=submission.source_code,
    )


def _sum_user_solve_time_seconds(
    first_ac_time_by_user_task: dict[tuple[str, str], datetime],
    room_start_time: datetime,
    user_id: str,
    task_ids: list[str],
) -> int:
    seconds = 0
    for task_id in task_ids:
        ac_time = first_ac_time_by_user_task.get((user_id, task_id))
        if ac_time is None:
            continue
        seconds += max(int((ac_time - room_start_time).total_seconds()), 0)
    return seconds


def _build_battle_list_item(
    *,
    member: RoomMember,
    room: Room,
    snapshot: RoomSnapshot,
) -> AnalyticsBattleListItemResponse:
    participant_row = next(
        (row for row in snapshot.leaderboard if row.participant_id == member.id),
        None,
    )

    return AnalyticsBattleListItemResponse(
        id=room.id,
        title=room.title,
        date=_room_date_str(room),
        status='finished' if room.status == RoomStatus.FINISHED else 'in_progress',
        role=member.role.value,
        participants=len(snapshot.leaderboard),
        languages=snapshot.languages,
        total_tasks=len(snapshot.tasks),
        solved_tasks=participant_row.solved_tasks if participant_row is not None else 0,
        place=participant_row.place if participant_row is not None else None,
        attempts=participant_row.submissions_count if participant_row is not None else 0,
    )


async def get_participant_analytics(
    session: AsyncSession,
    *,
    viewer: User,
    target_user_id: str,
) -> ParticipantAnalyticsResponse:
    memberships = (
        await session.exec(
            select(RoomMember, Room)
            .join(Room, Room.id == RoomMember.room_id)
            .where(
                RoomMember.user_id == target_user_id,
                RoomMember.role == MemberRole.PARTICIPANT,
            )
        )
    ).all()

    target_user = await session.get(User, target_user_id)
    if target_user is None:
        raise ValueError('User not found')

    rooms = [room for _member, room in memberships]
    snapshots = await _load_room_snapshots(session, rooms)

    battles_count = len(memberships)
    wins = 0
    places: list[float] = []
    solved_tasks_count = 0
    battle_items: list[AnalyticsBattleListItemResponse] = []
    heatmap_counter: Counter[str] = Counter()

    for member, room in memberships:
        snapshot = snapshots.get(room.id)
        if snapshot is None:
            continue

        item = _build_battle_list_item(member=member, room=room, snapshot=snapshot)
        battle_items.append(item)
        heatmap_counter[item.date] += 1

        if item.place is not None:
            places.append(float(item.place))
            if item.place == 1 and room.status == RoomStatus.FINISHED:
                wins += 1

        solved_tasks_count += item.solved_tasks

    battle_items.sort(key=lambda item: item.date, reverse=True)

    user_submissions = (
        await session.exec(
            select(Submission)
            .where(Submission.user_id == target_user_id)
            .order_by(Submission.created_at)
        )
    ).all()

    attempts_per_task_denominator = len({(submission.room_id, submission.task_id) for submission in user_submissions})
    average_attempts_per_task = (
        round(len(user_submissions) / attempts_per_task_denominator, 2)
        if attempts_per_task_denominator > 0
        else 0.0
    )

    error_counter = Counter(
        submission.verdict.value
        for submission in user_submissions
        if submission.verdict != SubmissionStatus.ACCEPTED
    )
    error_frequencies = [
        AnalyticsFrequencyResponse(key=key, count=int(count))
        for key, count in sorted(error_counter.items(), key=lambda item: (-item[1], item[0]))
    ]

    heatmap = [
        AnalyticsHeatmapCellResponse(date=date, count=int(count))
        for date, count in sorted(heatmap_counter.items())
    ]

    win_rate = round((wins / battles_count) * 100) if battles_count else 0

    return ParticipantAnalyticsResponse(
        user_id=target_user.id,
        username=target_user.username,
        is_self=viewer.id == target_user.id,
        battles_count=battles_count,
        win_rate=win_rate,
        solved_tasks_count=solved_tasks_count,
        average_attempts_per_task=average_attempts_per_task,
        average_place=_mean_or_none(places),
        error_frequencies=error_frequencies,
        heatmap=heatmap,
        battles=battle_items,
    )


async def get_battle_detail_analytics(
    session: AsyncSession,
    *,
    battle_id: str,
) -> Optional[BattleDetailAnalyticsResponse]:
    room = await session.get(Room, battle_id)
    if room is None:
        return None

    snapshots = await _load_room_snapshots(session, [room])
    snapshot = snapshots.get(room.id)
    if snapshot is None:
        return None

    return BattleDetailAnalyticsResponse(
        battle_id=room.id,
        title=room.title,
        status='finished' if room.status == RoomStatus.FINISHED else 'in_progress',
        started_at=room.started_at,
        finished_at=room.finished_at,
        participants=snapshot.leaderboard,
        tasks=snapshot.tasks,
        submissions=snapshot.submissions,
        participants_without_ac_count=snapshot.participants_without_ac_count,
        hint_usage_share=snapshot.hint_usage_share,
        problematic_tasks=snapshot.problematic_tasks,
    )


async def get_organizer_analytics(session: AsyncSession, *, organizer_user_id: str) -> OrganizerAnalyticsResponse:
    memberships = (
        await session.exec(
            select(RoomMember, Room)
            .join(Room, Room.id == RoomMember.room_id)
            .where(
                RoomMember.user_id == organizer_user_id,
                RoomMember.role == MemberRole.ORGANIZER,
            )
        )
    ).all()

    rooms = [room for _member, room in memberships]
    snapshots = await _load_room_snapshots(session, rooms)

    battle_items: list[AnalyticsBattleListItemResponse] = []
    participants_counts: list[float] = []
    solved_percents: list[float] = []
    solve_times: list[float] = []
    submissions_per_task: list[float] = []
    durations_seconds: list[float] = []
    finish_by_timer = 0
    finish_early = 0
    language_counter: Counter[str] = Counter()
    hint_usage_values: list[float] = []
    skill_spreads: list[float] = []
    participant_appearance: Counter[str] = Counter()

    for member, room in memberships:
        snapshot = snapshots.get(room.id)
        if snapshot is None:
            continue

        battle_items.append(_build_battle_list_item(member=member, room=room, snapshot=snapshot))

        participants_counts.append(float(len(snapshot.leaderboard)))
        solved_percents.append(snapshot.solved_percent)

        if snapshot.average_time_to_solve_seconds is not None:
            solve_times.append(snapshot.average_time_to_solve_seconds)

        submissions_per_task.append(snapshot.average_submissions_per_task)
        hint_usage_values.append(snapshot.hint_usage_share)

        for submission in snapshot.submissions:
            language_counter[submission.language] += 1

        for row in snapshot.leaderboard:
            participant_appearance[row.user_id] += 1

        if room.started_at is not None and room.finished_at is not None:
            durations_seconds.append(max((room.finished_at - room.started_at).total_seconds(), 0))

        if snapshot.finish_reason == 'timer':
            finish_by_timer += 1
        elif snapshot.finish_reason == 'manual':
            finish_early += 1

        if len(snapshot.leaderboard) >= 3:
            first = snapshot.leaderboard[0]
            third = snapshot.leaderboard[2]
            skill_spreads.append(float(first.solved_tasks - third.solved_tasks))
        elif len(snapshot.leaderboard) >= 2:
            first = snapshot.leaderboard[0]
            last = snapshot.leaderboard[-1]
            skill_spreads.append(float(first.solved_tasks - last.solved_tasks))

    finished_battles_count = sum(1 for _member, room in memberships if room.status == RoomStatus.FINISHED)
    retention_percent = _safe_percent(
        sum(1 for count in participant_appearance.values() if count >= 2),
        len(participant_appearance),
    )

    language_frequencies = [
        AnalyticsFrequencyResponse(key=key, count=int(count))
        for key, count in sorted(language_counter.items(), key=lambda item: (-item[1], item[0]))
    ]

    battle_items.sort(key=lambda item: item.date, reverse=True)

    return OrganizerAnalyticsResponse(
        organized_battles_count=len(memberships),
        average_participants=round(mean(participants_counts), 2) if participants_counts else 0.0,
        average_solved_percent=round(mean(solved_percents), 2) if solved_percents else 0.0,
        average_time_to_solve_seconds=_mean_or_none(solve_times),
        average_submissions_per_task=round(mean(submissions_per_task), 2) if submissions_per_task else 0.0,
        average_battle_duration_seconds=_mean_or_none(durations_seconds),
        finish_by_timer_share=_safe_percent(finish_by_timer, finished_battles_count),
        finish_early_share=_safe_percent(finish_early, finished_battles_count),
        retention_percent=retention_percent,
        hint_usage_share=round(mean(hint_usage_values), 2) if hint_usage_values else 0.0,
        average_skill_spread=_mean_or_none(skill_spreads),
        language_frequencies=language_frequencies,
        battles=battle_items,
    )


async def get_admin_platform_analytics(session: AsyncSession) -> AdminPlatformAnalyticsResponse:
    users = (await session.exec(select(User))).all()
    rooms = (await session.exec(select(Room))).all()
    snapshots = await _load_room_snapshots(session, rooms)

    room_members = (await session.exec(select(RoomMember))).all()
    participant_members = [member for member in room_members if member.role == MemberRole.PARTICIPANT]

    submissions = (await session.exec(select(Submission))).all()
    ai_hints = (await session.exec(select(AiHintEvent))).all()
    languages = (await session.exec(select(Language))).all()
    language_code_by_id = {language.id: language.code for language in languages}

    now = datetime.now()
    day_start = now - timedelta(days=1)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    activity_by_user: dict[str, datetime] = {}
    for member in room_members:
        activity_by_user[member.user_id] = max(activity_by_user.get(member.user_id, datetime.min), member.joined_at)
    for submission in submissions:
        activity_by_user[submission.user_id] = max(activity_by_user.get(submission.user_id, datetime.min), submission.created_at)

    dau = sum(1 for _user_id, at in activity_by_user.items() if at >= day_start)
    wau = sum(1 for _user_id, at in activity_by_user.items() if at >= week_start)
    mau = sum(1 for _user_id, at in activity_by_user.items() if at >= month_start)

    verdict_counter = Counter(submission.verdict.value for submission in submissions)
    language_counter = Counter(language_code_by_id.get(submission.language_id, str(submission.language_id)) for submission in submissions)

    verdict_frequencies = [
        AnalyticsFrequencyResponse(key=key, count=int(count))
        for key, count in sorted(verdict_counter.items(), key=lambda item: (-item[1], item[0]))
    ]
    language_frequencies = [
        AnalyticsFrequencyResponse(key=key, count=int(count))
        for key, count in sorted(language_counter.items(), key=lambda item: (-item[1], item[0]))
    ]

    solved_percents = [snapshot.solved_percent for snapshot in snapshots.values()]

    participants_per_room = [
        len(snapshot.leaderboard)
        for snapshot in snapshots.values()
    ]

    ai_hint_users_share = _safe_percent(len({hint.user_id for hint in ai_hints}), len({member.user_id for member in participant_members}))

    users_with_battle = {member.user_id for member in participant_members}
    first_battle_conversion_percent = _safe_percent(len(users_with_battle), len(users))

    started_battles = sum(1 for room in rooms if room.started_at is not None)
    finished_battles = sum(1 for room in rooms if room.status == RoomStatus.FINISHED)

    task_rows = (
        await session.exec(
            select(RoomTaskLink, Task)
            .join(Task, Task.id == RoomTaskLink.task_id)
            .order_by(RoomTaskLink.position)
        )
    ).all()

    rooms_by_task: dict[str, set[str]] = defaultdict(set)
    title_by_task: dict[str, str] = {}
    for room_task_link, task in task_rows:
        rooms_by_task[task.id].add(room_task_link.room_id)
        title_by_task[task.id] = task.title

    submissions_by_task = Counter(submission.task_id for submission in submissions)
    solved_by_task = Counter(submission.task_id for submission in submissions if submission.verdict == SubmissionStatus.ACCEPTED)

    task_stats: list[TaskPlatformAnalyticsResponse] = []
    for task_id, room_ids in rooms_by_task.items():
        submissions_count = int(submissions_by_task.get(task_id, 0))
        solved_count = int(solved_by_task.get(task_id, 0))
        task_stats.append(
            TaskPlatformAnalyticsResponse(
                task_id=task_id,
                title=title_by_task.get(task_id, task_id),
                rooms_count=len(room_ids),
                submissions_count=submissions_count,
                solved_percent=_safe_percent(solved_count, submissions_count),
            )
        )

    top_tasks_by_difficulty = sorted(task_stats, key=lambda task: (task.solved_percent, -task.submissions_count, task.title))[:5]
    top_tasks_by_popularity = sorted(task_stats, key=lambda task: (-task.submissions_count, task.title))[:5]

    peaks_by_hour_counter = Counter(submission.created_at.strftime('%H:00') for submission in submissions)
    peaks_by_weekday_counter = Counter(submission.created_at.strftime('%A') for submission in submissions)

    peaks_by_hour = [
        PeakLoadBucketResponse(bucket=bucket, count=int(count))
        for bucket, count in sorted(peaks_by_hour_counter.items())
    ]
    peaks_by_weekday = [
        PeakLoadBucketResponse(bucket=bucket, count=int(count))
        for bucket, count in sorted(peaks_by_weekday_counter.items(), key=lambda item: item[0])
    ]

    return AdminPlatformAnalyticsResponse(
        total_users=len(users),
        dau=dau,
        wau=wau,
        mau=mau,
        total_battles=len(rooms),
        finished_battles=finished_battles,
        unique_participants=len(users_with_battle),
        average_participants_per_battle=round(mean(participants_per_room), 2) if participants_per_room else 0.0,
        average_solved_percent=round(mean(solved_percents), 2) if solved_percents else 0.0,
        total_submissions=len(submissions),
        verdict_frequencies=verdict_frequencies,
        language_frequencies=language_frequencies,
        ai_hints_total=len(ai_hints),
        ai_hint_users_share=ai_hint_users_share,
        first_battle_conversion_percent=first_battle_conversion_percent,
        organizer_funnel=AdminFunnelResponse(
            created_rooms=len(rooms),
            started_battles=started_battles,
            finished_battles=finished_battles,
        ),
        top_tasks_by_difficulty=top_tasks_by_difficulty,
        top_tasks_by_popularity=top_tasks_by_popularity,
        peaks_by_hour=peaks_by_hour,
        peaks_by_weekday=peaks_by_weekday,
    )
