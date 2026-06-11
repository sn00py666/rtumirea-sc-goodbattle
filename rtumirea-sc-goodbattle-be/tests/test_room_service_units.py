from __future__ import annotations

from datetime import datetime, timedelta

import pytest

import app.room_service as room_service
from app.models import MemberRole, Room, RoomMember, RoomStatus, Task, TaskExample
from app.state import ParticipantRuntime, RoomRuntime


def _make_task(task_id: str = 'task-1') -> Task:
    task = Task(
        id=task_id,
        title='Task',
        description='Description',
        time_limit_ms=1000,
        memory_limit_mb=64,
    )
    task.examples = [TaskExample(input_data='1 2', output_data='3', task_id=task_id)]
    return task


def _make_room(status: RoomStatus = RoomStatus.WAITING, started_at: datetime | None = None) -> Room:
    return Room(
        id='room-1',
        title='Battle',
        join_code='ABCDEFG1',
        creator_id='creator-1',
        status=status,
        time_limit=10,
        started_at=started_at,
    )


def test_build_task_response_maps_fields():
    task = _make_task('task-42')
    response = room_service.build_task_response(task)

    assert response.id == 'task-42'
    assert response.title == 'Task'
    assert len(response.examples) == 1
    assert response.examples[0].input == '1 2'


def test_build_participant_response_maps_runtime():
    participant = ParticipantRuntime(
        user_id='u1',
        username='User 1',
        role='participant',
        code='print(1)',
        language='python',
    )

    response = room_service.build_participant_response('p1', participant)
    assert response.id == 'p1'
    assert response.user_id == 'u1'
    assert response.code == 'print(1)'


def test_build_participant_solved_tasks_keeps_task_order():
    participant = ParticipantRuntime(
        user_id='u1',
        username='User 1',
        role='participant',
        solved_task_ids={'t3', 't1'},
    )

    response = room_service.build_participant_solved_tasks_response(participant, ['t1', 't2', 't3'])
    assert response.solved_task_ids == ['t1', 't3']


def test_get_room_remaining_seconds_for_finished_room():
    room = _make_room(status=RoomStatus.FINISHED)
    runtime = RoomRuntime(languages=['python'], task_ids=['t1'], time_limit=10)
    assert room_service.get_room_remaining_seconds(room, runtime) == 0


def test_get_room_remaining_seconds_when_not_started():
    room = _make_room(status=RoomStatus.WAITING, started_at=None)
    runtime = RoomRuntime(languages=['python'], task_ids=['t1'], time_limit=7)
    assert room_service.get_room_remaining_seconds(room, runtime) == 420


def test_get_room_remaining_seconds_with_elapsed_time(monkeypatch):
    base_now = datetime(2026, 5, 29, 12, 0, 0)
    started_at = base_now - timedelta(minutes=2)
    room = _make_room(status=RoomStatus.RUNNING, started_at=started_at)
    runtime = RoomRuntime(languages=['python'], task_ids=['t1'], time_limit=10)

    class FakeDateTime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ARG003
            return base_now

    monkeypatch.setattr(room_service, 'datetime', FakeDateTime)

    assert room_service.get_room_remaining_seconds(room, runtime) == 480


def test_build_room_state_payload():
    room = _make_room(status=RoomStatus.RUNNING, started_at=datetime.now() - timedelta(minutes=1))
    runtime = RoomRuntime(
        languages=['python'],
        task_ids=['t1', 't2'],
        time_limit=10,
        current_task_index=1,
        status='running',
    )
    payload = room_service.build_room_state_payload(room, runtime)
    assert payload['status'] == 'running'
    assert payload['currentTaskIndex'] == 1
    assert isinstance(payload['remainingSeconds'], int)


@pytest.mark.parametrize(
    ('role', 'expected_place'),
    [
        (MemberRole.PARTICIPANT, 1),
        (MemberRole.ORGANIZER, None),
    ],
)
def test_get_history_payload_place_visibility(role: MemberRole, expected_place: int | None):
    room = _make_room(status=RoomStatus.FINISHED, started_at=datetime.now() - timedelta(minutes=5))
    room.finished_at = datetime.now()
    room_member = RoomMember(id='p1', room_id=room.id, user_id='u1', role=role)
    runtime = RoomRuntime(
        languages=['python'],
        task_ids=['t1', 't2'],
        time_limit=10,
        status='finished',
        participants={
            'p1': ParticipantRuntime(
                user_id='u1',
                username='User 1',
                role='participant',
                solved_task_ids={'t1', 't2'},
                total_time_seconds=50,
            ),
            'p2': ParticipantRuntime(
                user_id='u2',
                username='User 2',
                role='participant',
                solved_task_ids={'t1'},
                total_time_seconds=100,
            ),
        },
    )

    payload = room_service.get_history_payload(room, room_member, runtime)
    assert payload.place == expected_place
    assert payload.solved_tasks == 2

