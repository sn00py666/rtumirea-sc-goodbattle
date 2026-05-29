from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.demo_seed import is_demo_seed_enabled, seed_demo_analytics_data
from app.models import Language, Task, TaskExample, TestCase

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL environment variable is required')

async_engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionFactory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

DEFAULT_LANGUAGES = [
    {'id': 1, 'code': 'javascript', 'name': 'JavaScript'},
    {'id': 2, 'code': 'python', 'name': 'Python'},
    {'id': 3, 'code': 'cpp', 'name': 'C++'},
    {'id': 4, 'code': 'java', 'name': 'Java'},
    {'id': 5, 'code': 'go', 'name': 'Go'},
]

DEFAULT_TASKS = [
    {
        'id': 'd290f1ee-6c54-4b01-90e6-d701748f0851',
        'title': 'Реверс строки',
        'description': 'Напишите функцию `reverse`, которая принимает строку и возвращает её в обратном порядке.',
        'examples': [
            {'input': '"hello"', 'output': '"olleh"'},
            {'input': '"world"', 'output': '"dlrow"'},
        ],
        'tests': [
            {'input': '"hello"', 'expected': '"olleh"'},
            {'input': '"world"', 'expected': '"dlrow"'},
            {'input': '""', 'expected': '""'},
        ],
    },
    {
        'id': 'e4d909c2-90d0-4c3f-b1a2-6f135ab1c5d8',
        'title': 'Сумма массива',
        'description': 'Напишите функцию, которая принимает массив чисел и возвращает их сумму.',
        'examples': [
            {'input': '[1, 2, 3]', 'output': '6'},
            {'input': '[5, 5, 5]', 'output': '15'},
        ],
        'tests': [
            {'input': '[1, 2, 3]', 'expected': '6'},
            {'input': '[5, 5, 5]', 'expected': '15'},
            {'input': '[]', 'expected': '0'},
        ],
    },
    {
        'id': '6ba7b810-9dad-11d1-80b4-00c04fd430c8',
        'title': 'Палиндром',
        'description': 'Проверьте, является ли строка палиндромом.',
        'examples': [
            {'input': '"level"', 'output': 'true'},
            {'input': '"battle"', 'output': 'false'},
        ],
        'tests': [
            {'input': '"level"', 'expected': 'true'},
            {'input': '"battle"', 'expected': 'false'},
            {'input': '""', 'expected': 'true'},
        ],
    },
]


async def migrate_database_schema():
    async with async_engine.begin() as connection:
        def _ensure_room_columns(sync_connection):
            inspector = inspect(sync_connection)
            if not inspector.has_table('room'):
                return

            room_columns = {column['name'] for column in inspector.get_columns('room')}
            missing_columns = {
                'time_limit': 'ALTER TABLE room ADD COLUMN time_limit INTEGER NOT NULL DEFAULT 10',
                'current_task_index': 'ALTER TABLE room ADD COLUMN current_task_index INTEGER NOT NULL DEFAULT 0',
            }
            for column_name, statement in missing_columns.items():
                if column_name not in room_columns:
                    sync_connection.execute(text(statement))

            if inspector.has_table('roomlanguagelink') and 'languages' in room_columns:
                existing_room_language_links = sync_connection.execute(text('SELECT COUNT(*) FROM roomlanguagelink')).scalar_one()
                if int(existing_room_language_links) == 0:
                    rooms = sync_connection.execute(text('SELECT id, languages FROM room')).fetchall()
                    language_rows = sync_connection.execute(text('SELECT id, code FROM language')).fetchall()
                    language_ids_by_code = {row[1]: row[0] for row in language_rows}
                    for room_id, raw_languages in rooms:
                        for position, language_code in enumerate(json.loads(raw_languages or '[]')):
                            language_id = language_ids_by_code.get(language_code)
                            if language_id is None:
                                continue
                            sync_connection.execute(
                                text(
                                    'INSERT INTO roomlanguagelink (room_id, language_id, position) '
                                    'VALUES (:room_id, :language_id, :position)'
                                ),
                                {'room_id': room_id, 'language_id': language_id, 'position': position},
                            )

            if inspector.has_table('roomtasklink') and 'task_ids' in room_columns:
                existing_room_task_links = sync_connection.execute(text('SELECT COUNT(*) FROM roomtasklink')).scalar_one()
                if int(existing_room_task_links) == 0:
                    rooms = sync_connection.execute(text('SELECT id, task_ids FROM room')).fetchall()
                    for room_id, raw_task_ids in rooms:
                        for position, task_id in enumerate(json.loads(raw_task_ids or '[]')):
                            sync_connection.execute(
                                text(
                                    'INSERT INTO roomtasklink (room_id, task_id, position) '
                                    'VALUES (:room_id, :task_id, :position)'
                                ),
                                {'room_id': room_id, 'task_id': task_id, 'position': position},
                            )

        def _ensure_task_columns(sync_connection):
            inspector = inspect(sync_connection)
            if not inspector.has_table('task'):
                return

            task_columns = {column['name'] for column in inspector.get_columns('task')}
            if 'creator_id' not in task_columns:
                sync_connection.execute(text('ALTER TABLE task ADD COLUMN creator_id VARCHAR NULL'))

        def _ensure_user_columns(sync_connection):
            inspector = inspect(sync_connection)
            if not inspector.has_table('user'):
                return

            user_columns = {column['name'] for column in inspector.get_columns('user')}
            if 'is_admin' not in user_columns:
                sync_connection.execute(text('ALTER TABLE "user" ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE'))

        def _ensure_submission_status_enum(sync_connection):
            # PostgreSQL enum used by `submission.verdict` may come from an older
            # schema version without COMPILE_ERROR. Make migration idempotent.
            if sync_connection.dialect.name != 'postgresql':
                return
            sync_connection.execute(text("ALTER TYPE submissionstatus ADD VALUE IF NOT EXISTS 'COMPILE_ERROR'"))

        await connection.run_sync(_ensure_room_columns)
        await connection.run_sync(_ensure_task_columns)
        await connection.run_sync(_ensure_user_columns)
        await connection.run_sync(_ensure_submission_status_enum)


async def seed_reference_data():
    async with AsyncSessionFactory() as session:
        existing_languages = (await session.exec(text('SELECT COUNT(*) FROM language'))).one()
        if int(existing_languages[0]) == 0:
            session.add_all([Language(**language) for language in DEFAULT_LANGUAGES])

        existing_tasks = (await session.exec(text('SELECT COUNT(*) FROM task'))).one()
        if int(existing_tasks[0]) == 0:
            for task_payload in DEFAULT_TASKS:
                task = Task(
                    id=str(task_payload['id']),
                    title=str(task_payload['title']),
                    description=str(task_payload['description']),
                    time_limit_ms=1000,
                    memory_limit_mb=64,
                )

                session.add(task)
                session.add_all([
                    TaskExample(
                        task_id=task.id,
                        input_data=str(example['input']),
                        output_data=str(example['output']),
                    ) for example in task_payload['examples']
                ])

                session.add_all([
                    TestCase(
                        task_id=task.id,
                        input_data=str(test_case['input']),
                        expected_output=str(test_case['expected']),
                        is_hidden=False,
                    ) for test_case in task_payload['tests']
                ])

        await session.commit()


async def initialize_database():
    async with async_engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)

    await migrate_database_schema()
    await seed_reference_data()

    if is_demo_seed_enabled():
        async with AsyncSessionFactory() as session:
            await seed_demo_analytics_data(session)


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        yield session
