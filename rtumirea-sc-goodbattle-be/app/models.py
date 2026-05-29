from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel


def generate_uuid() -> str:
    return str(uuid4())


class RoomStatus(str, Enum):
    WAITING = 'waiting'
    RUNNING = 'running'
    PAUSED = 'paused'
    FINISHED = 'finished'


class MemberRole(str, Enum):
    ORGANIZER = 'organizer'
    PARTICIPANT = 'participant'


class SubmissionStatus(str, Enum):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    WRONG_ANSWER = 'wrong_answer'
    COMPILE_ERROR = 'compile_error'
    RUNTIME_ERROR = 'runtime_error'
    TIME_LIMIT_EXCEEDED = 'time_limit_exceeded'


class User(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)

    email: str = Field(index=True, unique=True)
    username: str
    password_hash: str
    is_admin: bool = False

    created_rooms: Mapped[list['Room']] = Relationship(back_populates='creator')
    created_tasks: Mapped[list['Task']] = Relationship(back_populates='creator')
    room_members: Mapped[list['RoomMember']] = Relationship(back_populates='user')
    submissions: Mapped[list['Submission']] = Relationship(back_populates='user')
    battle_events: Mapped[list['BattleEvent']] = Relationship(back_populates='user')
    ai_hint_events: Mapped[list['AiHintEvent']] = Relationship(back_populates='user')


class Room(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)

    title: str
    join_code: str = Field(index=True, unique=True)
    status: RoomStatus = Field(default=RoomStatus.WAITING)
    time_limit: int = 30
    current_task_index: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    creator_id: str = Field(foreign_key='user.id')
    creator: Mapped[Optional[User]] = Relationship(back_populates='created_rooms')

    members: Mapped[list['RoomMember']] = Relationship(back_populates='room')
    submissions: Mapped[list['Submission']] = Relationship(back_populates='room')
    task_links: Mapped[list['RoomTaskLink']] = Relationship(back_populates='room')
    language_links: Mapped[list['RoomLanguageLink']] = Relationship(back_populates='room')
    battle_events: Mapped[list['BattleEvent']] = Relationship(back_populates='room')
    ai_hint_events: Mapped[list['AiHintEvent']] = Relationship(back_populates='room')


class RoomMember(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    role: MemberRole
    joined_at: datetime = Field(default_factory=datetime.now)

    room_id: str = Field(foreign_key='room.id')
    room: Mapped[Optional[Room]] = Relationship(back_populates='members')

    user_id: str = Field(foreign_key='user.id')
    user: Mapped[Optional[User]] = Relationship(back_populates='room_members')


class Task(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)

    title: str
    description: str
    time_limit_ms: int
    memory_limit_mb: int
    creator_id: Optional[str] = Field(default=None, foreign_key='user.id')

    creator: Mapped[Optional[User]] = Relationship(back_populates='created_tasks')

    test_cases: Mapped[list['TestCase']] = Relationship(back_populates='task')
    submissions: Mapped[list['Submission']] = Relationship(back_populates='task')
    examples: Mapped[list['TaskExample']] = Relationship(back_populates='task')
    room_links: Mapped[list['RoomTaskLink']] = Relationship(back_populates='task')
    ai_hint_events: Mapped[list['AiHintEvent']] = Relationship(back_populates='task')


class TaskExample(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    input_data: str
    output_data: str

    task_id: str = Field(foreign_key='task.id')
    task: Mapped[Optional[Task]] = Relationship(back_populates='examples')


class TestCase(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    input_data: str
    expected_output: str
    is_hidden: bool = True

    task_id: str = Field(foreign_key='task.id')
    task: Mapped[Optional[Task]] = Relationship(back_populates='test_cases')
    test_results: Mapped[list['SubmissionTestResult']] = Relationship(back_populates='test_case')


class Language(SQLModel, table=True):
    id: int = Field(primary_key=True)
    code: str
    name: str
    room_links: Mapped[list['RoomLanguageLink']] = Relationship(back_populates='language')


class RoomTaskLink(SQLModel, table=True):
    room_id: str = Field(foreign_key='room.id', primary_key=True)
    task_id: str = Field(foreign_key='task.id', primary_key=True)
    position: int = 0

    room: Mapped[Optional[Room]] = Relationship(back_populates='task_links')
    task: Mapped[Optional[Task]] = Relationship(back_populates='room_links')


class RoomLanguageLink(SQLModel, table=True):
    room_id: str = Field(foreign_key='room.id', primary_key=True)
    language_id: int = Field(foreign_key='language.id', primary_key=True)
    position: int = 0

    room: Mapped[Optional[Room]] = Relationship(back_populates='language_links')
    language: Mapped[Optional[Language]] = Relationship(back_populates='room_links')


class Submission(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)

    source_code: str
    verdict: SubmissionStatus = Field(default=SubmissionStatus.PENDING)
    finished_at: Optional[datetime] = None
    execution_time_ms: int = 0
    execution_memory_kb: int = 0

    room_id: str = Field(foreign_key='room.id')
    room: Mapped[Optional[Room]] = Relationship(back_populates='submissions')

    user_id: str = Field(foreign_key='user.id')
    user: Mapped[Optional[User]] = Relationship(back_populates='submissions')

    task_id: str = Field(foreign_key='task.id')
    task: Mapped[Optional[Task]] = Relationship(back_populates='submissions')

    language_id: int = Field(foreign_key='language.id')
    language: Mapped[Optional[Language]] = Relationship()

    test_results: Mapped[list['SubmissionTestResult']] = Relationship(back_populates='submission')


class SubmissionTestResult(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    verdict: SubmissionStatus = Field(default=SubmissionStatus.PENDING)
    execution_time_ms: int = 0
    execution_memory_kb: int = 0
    error_message: str = ''

    submission_id: str = Field(foreign_key='submission.id')
    submission: Mapped[Optional[Submission]] = Relationship(back_populates='test_results')

    test_id: str = Field(foreign_key='testcase.id')
    test_case: Mapped[Optional[TestCase]] = Relationship(back_populates='test_results')


class BattleEvent(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)

    event_type: str
    room_id: str = Field(foreign_key='room.id', index=True)
    user_id: Optional[str] = Field(default=None, foreign_key='user.id', index=True)
    task_id: Optional[str] = Field(default=None, foreign_key='task.id', index=True)
    reason: Optional[str] = None

    room: Mapped[Optional[Room]] = Relationship(back_populates='battle_events')
    user: Mapped[Optional[User]] = Relationship(back_populates='battle_events')
    task: Mapped[Optional[Task]] = Relationship()


class AiHintEvent(SQLModel, table=True):
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)

    room_id: str = Field(foreign_key='room.id', index=True)
    user_id: str = Field(foreign_key='user.id', index=True)
    task_id: str = Field(foreign_key='task.id', index=True)
    question: str
    answer: str

    room: Mapped[Optional[Room]] = Relationship(back_populates='ai_hint_events')
    user: Mapped[Optional[User]] = Relationship(back_populates='ai_hint_events')
    task: Mapped[Optional[Task]] = Relationship(back_populates='ai_hint_events')
