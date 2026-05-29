from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_async_session
from app.dependencies import get_current_user
from app.models import Task, TaskExample, TestCase, User
from app.schemas import (
    CreateTaskRequest,
    TaskCreatorResponse,
    TaskDetailResponse,
    TaskExampleResponse,
    TaskResponse,
    TaskTestCaseResponse,
    UpdateTaskRequest,
)

router = APIRouter()


def build_task_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        time_limit_ms=task.time_limit_ms,
        memory_limit_mb=task.memory_limit_mb,
        creator=(
            TaskCreatorResponse(id=task.creator.id, username=task.creator.username)
            if task.creator is not None else None
        ),
        examples=[
            TaskExampleResponse(input=example.input_data, output=example.output_data)
            for example in task.examples
        ],
    )


def build_task_detail_response(task: Task) -> TaskDetailResponse:
    return TaskDetailResponse(
        **build_task_response(task).model_dump(),
        test_cases=[
            TaskTestCaseResponse(
                input=test_case.input_data,
                expected_output=test_case.expected_output,
                is_hidden=test_case.is_hidden,
            )
            for test_case in task.test_cases
        ],
    )


async def get_task_or_404(session: AsyncSession, task_id: str) -> Task:
    query = (
        select(Task)
        .where(Task.id == task_id)
        .options(
            selectinload(Task.creator),
            selectinload(Task.examples),
            selectinload(Task.test_cases),
        )
    )

    task = (await session.exec(query)).first()
    if task is None:
        raise HTTPException(status_code=404, detail='Не найдено')

    return task


async def replace_task_relations(session: AsyncSession, task: Task, request: CreateTaskRequest | UpdateTaskRequest) -> None:
    await session.exec(delete(TaskExample).where(TaskExample.task_id == task.id))
    await session.exec(delete(TestCase).where(TestCase.task_id == task.id))
    await session.flush()

    session.add_all([
        TaskExample(task_id=task.id, input_data=example.input, output_data=example.output)
        for example in request.examples
    ])

    session.add_all([
        TestCase(
            task_id=task.id,
            input_data=test_case.input,
            expected_output=test_case.expected_output,
            is_hidden=test_case.is_hidden,
        )
        for test_case in request.test_cases
    ])


@router.get('/tasks', response_model=List[TaskResponse])
async def list_tasks(session: AsyncSession = Depends(get_async_session)) -> List[TaskResponse]:
    tasks = (
        await session.exec(
            select(Task)
            .order_by(Task.title)
            .options(
                selectinload(Task.creator),
                selectinload(Task.examples),
            )
        )
    ).all()
    return [build_task_response(task) for task in tasks]


@router.get('/tasks/{task_id}', response_model=TaskDetailResponse)
async def get_task(
        task_id: str,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session),
) -> TaskDetailResponse:
    task = await get_task_or_404(session, task_id)
    if task.creator_id is not None and task.creator_id != user.id:
        raise HTTPException(status_code=403, detail='Нет доступа к задаче!')

    return build_task_detail_response(task)


@router.post('/tasks', response_model=TaskDetailResponse, status_code=201)
async def create_task(
        request: CreateTaskRequest,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session),
) -> TaskDetailResponse:
    task = Task(
        title=request.title,
        description=request.description,
        time_limit_ms=request.time_limit_ms,
        memory_limit_mb=request.memory_limit_mb,
        creator_id=user.id,
    )
    session.add(task)
    await session.flush()

    await replace_task_relations(session, task, request)
    await session.commit()

    created_task = await get_task_or_404(session, task.id)
    return build_task_detail_response(created_task)


@router.put('/tasks/{task_id}', response_model=TaskDetailResponse)
async def update_task(
        task_id: str,
        request: UpdateTaskRequest,
        user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_async_session),
) -> TaskDetailResponse:
    task = await get_task_or_404(session, task_id)
    if task.creator_id is not None and task.creator_id != user.id:
        raise HTTPException(status_code=403, detail='Нет доступа к задаче!')

    if task.creator_id is None:
        task.creator_id = user.id

    task.title = request.title
    task.description = request.description
    task.time_limit_ms = request.time_limit_ms
    task.memory_limit_mb = request.memory_limit_mb
    session.add(task)

    await replace_task_relations(session, task, request)
    await session.commit()

    updated_task = await get_task_or_404(session, task.id)
    return build_task_detail_response(updated_task)
