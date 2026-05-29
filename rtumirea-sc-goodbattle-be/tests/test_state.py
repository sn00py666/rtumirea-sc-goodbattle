from __future__ import annotations

from app.state import (
    ROOM_STATES,
    ParticipantRuntime,
    build_battle_results,
    create_room_runtime,
    ensure_room_runtime,
)


def setup_function():
    ROOM_STATES.clear()


def test_ensure_room_runtime_returns_existing_instance():
    room = create_room_runtime('room-1', ['python'], ['t1', 't2'], 10)

    same_room = ensure_room_runtime('room-1', ['javascript'], ['x'], 99)

    assert same_room is room
    assert same_room.languages == ['python']
    assert same_room.task_ids == ['t1', 't2']
    assert same_room.time_limit == 10


def test_build_battle_results_sorts_by_score_time_and_id():
    room = create_room_runtime('room-2', ['python'], ['t1', 't2', 't3'], 10)
    room.participants['z-id'] = ParticipantRuntime(
        user_id='u-z',
        username='Zed',
        role='participant',
        solved_task_ids={'t1', 't2'},
        total_time_seconds=100,
    )
    room.participants['a-id'] = ParticipantRuntime(
        user_id='u-a',
        username='Ann',
        role='participant',
        solved_task_ids={'t1', 't2'},
        total_time_seconds=100,
    )
    room.participants['b-id'] = ParticipantRuntime(
        user_id='u-b',
        username='Bob',
        role='participant',
        solved_task_ids={'t1'},
        total_time_seconds=50,
    )
    room.participants['org-id'] = ParticipantRuntime(
        user_id='u-org',
        username='Organizer',
        role='organizer',
        solved_task_ids={'t1', 't2', 't3'},
        total_time_seconds=1,
    )

    results = build_battle_results(room)

    assert [item.participant_id for item in results] == ['a-id', 'z-id', 'b-id']
    assert [item.place for item in results] == [1, 2, 3]
    assert results[0].total_tasks == 3

