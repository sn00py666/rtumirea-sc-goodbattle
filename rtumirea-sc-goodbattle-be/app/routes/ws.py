from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional

from docker.errors import DockerException
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from jose import JWTError
from pydantic import ValidationError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth import decode_access_token
from app.ai_hint_service import ai_hint_service
from app.code_runner import runner as code_runner
from app.database import AsyncSessionFactory
from app.dependencies import SESSION_COOKIE_NAME
from app.models import (
    AiHintEvent,
    BattleEvent,
    Language,
    Room,
    RoomMember,
    RoomStatus,
    Submission,
    SubmissionStatus,
    SubmissionTestResult,
    User,
)
from app.room_service import (
    get_tasks_by_ids,
    hydrate_room_runtime,
    move_room_to_next_task,
    require_organizer,
    require_room_membership,
    set_room_status,
)
from app.schemas import AskAiHintRequest, RunCodeExecutionLogResponse, RunCodeRequest, RunCodeResultResponse
from app.state import build_battle_results, get_room_runtime, room_connection_manager

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_websocket_user(websocket: WebSocket) -> Optional[User]:
    session_token = websocket.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        return None

    try:
        token_payload = decode_access_token(session_token)
    except JWTError:
        return None

    user_id = token_payload.get('user_id')
    if not user_id:
        return None

    async with AsyncSessionFactory() as session:
        return (await session.exec(select(User).where(User.id == user_id))).first()


async def send_socket_error(websocket: WebSocket, detail: object, status_code: int = 400):
    await websocket.send_json({'type': 'error', 'data': {'detail': detail, 'status': status_code}})


def build_participant_socket_payload(participant_id: str, user: User, room: Room):
    room_runtime = get_room_runtime(room.id)
    if room_runtime is None:
        raise HTTPException(status_code=404, detail='Комната не найдена!')

    participant = room_runtime.participants[participant_id]
    return {
        'id': participant_id,
        'user_id': user.id,
        'username': participant.username,
        'role': participant.role,
        'language': participant.language,
    }


async def broadcast_participant_left(room_id: str, participant_id: str):
    pending_participants = [participant_id]
    announced_participants = set()

    while pending_participants:
        current_participant_id = pending_participants.pop(0)
        if current_participant_id in announced_participants:
            continue

        room_runtime = get_room_runtime(room_id)
        current_participant = room_runtime.participants.get(current_participant_id) if room_runtime is not None else None

        announced_participants.add(current_participant_id)
        disconnected_participants = await room_connection_manager.broadcast(
            room_id,
            {
                'type': 'participant_left',
                'data': {
                    'id': current_participant_id,
                    'user_id': current_participant.user_id if current_participant is not None else None,
                },
            },
        )
        for disconnected_participant_id in disconnected_participants:
            if disconnected_participant_id not in announced_participants:
                pending_participants.append(disconnected_participant_id)


def _normalize_output(raw: str) -> str:
    return raw.strip()


def _build_error_kind(stderr: str, timed_out: bool, exit_code: int, passed: bool) -> Optional[str]:
    if passed:
        return None
    if timed_out:
        return 'time_limit_exceeded'
    if exit_code != 0:
        if 'SyntaxError' in stderr:
            return 'compile_error'
        return 'runtime_error'
    return 'wrong_answer'


def _result_to_submission_status(result: RunCodeResultResponse) -> SubmissionStatus:
    if result.passed:
        return SubmissionStatus.ACCEPTED
    if result.error == 'compile_error':
        return SubmissionStatus.COMPILE_ERROR
    if result.error == 'runtime_error':
        return SubmissionStatus.RUNTIME_ERROR
    if result.error == 'time_limit_exceeded':
        return SubmissionStatus.TIME_LIMIT_EXCEEDED
    return SubmissionStatus.WRONG_ANSWER


def _submission_verdict_from_results(results: list[RunCodeResultResponse]) -> SubmissionStatus:
    if all(result.passed for result in results):
        return SubmissionStatus.ACCEPTED

    for result in results:
        if not result.passed:
            return _result_to_submission_status(result)
    return SubmissionStatus.WRONG_ANSWER


async def _record_battle_event(
    *,
    room_id: str,
    event_type: str,
    session: AsyncSession,
    task_id: Optional[str] = None,
    user_id: Optional[str] = None,
    reason: Optional[str] = None,
):
    session.add(
        BattleEvent(
            room_id=room_id,
            event_type=event_type,
            user_id=user_id,
            task_id=task_id,
            reason=reason,
        )
    )


async def broadcast_room_event(room_id: str, payload: dict):
    disconnected_participants = await room_connection_manager.broadcast(room_id, payload)
    for disconnected_participant_id in disconnected_participants:
        await broadcast_participant_left(room_id, disconnected_participant_id)


async def finish_room(room_id: str, *, reason: str, user_id: Optional[str] = None):
    async with AsyncSessionFactory() as session:
        room = await session.get(Room, room_id)
        if room is None or room.status == RoomStatus.FINISHED:
            return

        room_runtime = await hydrate_room_runtime(session, room)
        room_state_payload = await set_room_status(session, room, room_runtime, RoomStatus.FINISHED)
        await _record_battle_event(
            room_id=room_id,
            event_type='finish_battle',
            user_id=user_id or room.creator_id,
            reason=reason,
            session=session,
        )
        await session.commit()
        results = build_battle_results(room_runtime)
        cancel_room_auto_finish(room_id)

    await broadcast_room_event(
        room_id,
        {
            'type': 'battle_finished',
            'data': {
                **room_state_payload,
                'results': [result.model_dump(by_alias=True) for result in results],
            },
        },
    )


def cancel_room_auto_finish(room_id: str):
    room_runtime = get_room_runtime(room_id)
    if room_runtime is None or room_runtime.auto_finish_task is None:
        return

    if room_runtime.auto_finish_task is not asyncio.current_task():
        room_runtime.auto_finish_task.cancel()
    room_runtime.auto_finish_task = None


def ensure_room_auto_finish(room_id: str, started_at: Optional[datetime]):
    room_runtime = get_room_runtime(room_id)
    if room_runtime is None or room_runtime.status == 'finished' or started_at is None:
        return

    if room_runtime.auto_finish_task is not None and not room_runtime.auto_finish_task.done():
        return

    deadline = started_at + timedelta(minutes=room_runtime.time_limit)

    async def auto_finish_room():
        try:
            delay = max((deadline - datetime.now()).total_seconds(), 0)
            if delay > 0:
                await asyncio.sleep(delay)
            await finish_room(room_id, reason='timer')
        except asyncio.CancelledError:
            raise
        finally:
            current_runtime = get_room_runtime(room_id)
            if current_runtime is not None and current_runtime.auto_finish_task is asyncio.current_task():
                current_runtime.auto_finish_task = None

    room_runtime.auto_finish_task = asyncio.create_task(auto_finish_room())


async def handle_start_battle(room_id: str, user: User):
    async with AsyncSessionFactory() as session:
        room, _ = await require_organizer(session, room_id, user)
        room_runtime = await hydrate_room_runtime(session, room)
        room_state_payload = await set_room_status(session, room, room_runtime, RoomStatus.RUNNING)
        await _record_battle_event(
            room_id=room_id,
            event_type='start_battle',
            user_id=user.id,
            session=session,
        )
        await session.commit()
        ensure_room_auto_finish(room_id, room.started_at)

    await broadcast_room_event(room_id, {'type': 'status_change', 'data': room_state_payload})


async def handle_pause_battle(room_id: str, user: User):
    async with AsyncSessionFactory() as session:
        room, _ = await require_organizer(session, room_id, user)
        room_runtime = await hydrate_room_runtime(session, room)
        room_state_payload = await set_room_status(session, room, room_runtime, RoomStatus.PAUSED)
        await _record_battle_event(
            room_id=room_id,
            event_type='pause_battle',
            user_id=user.id,
            session=session,
        )
        await session.commit()

    await broadcast_room_event(room_id, {'type': 'status_change', 'data': room_state_payload})


async def handle_next_task(room_id: str, user: User):
    async with AsyncSessionFactory() as session:
        room, _ = await require_organizer(session, room_id, user)
        room_runtime = await hydrate_room_runtime(session, room)
        room_state_payload = await move_room_to_next_task(session, room, room_runtime)
        task_id = room_runtime.task_ids[room_runtime.current_task_index] if room_runtime.task_ids else None
        await _record_battle_event(
            room_id=room_id,
            event_type='next_task',
            user_id=user.id,
            task_id=task_id,
            session=session,
        )
        await session.commit()

    await broadcast_room_event(
        room_id,
        {'type': 'next_task', 'data': room_state_payload},
    )


async def handle_finish_battle(room_id: str, user: User):
    async with AsyncSessionFactory() as session:
        room, _ = await require_organizer(session, room_id, user)
        if room.status == RoomStatus.FINISHED:
            return

    await finish_room(room_id, reason='manual', user_id=user.id)


async def handle_run_code(room_id: str, user: User, payload_data: object):
    try:
        payload = RunCodeRequest.model_validate(payload_data)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc

    solved_event_data = None

    async with AsyncSessionFactory() as session:
        room, member = await require_room_membership(session, room_id, user)
        room_runtime = await hydrate_room_runtime(session, room)

        if payload.task_id not in room_runtime.task_ids:
            raise HTTPException(status_code=404, detail='Не найдено')

        tasks = await get_tasks_by_ids(session, [payload.task_id])
        if not tasks:
            raise HTTPException(status_code=404, detail='Не найдено')

        if payload.language not in room_runtime.languages:
            raise HTTPException(status_code=400, detail='Unsupported language')
        language = (await session.exec(select(Language).where(Language.code == payload.language))).first()
        if language is None:
            raise HTTPException(status_code=400, detail='Unsupported language')

        participant = room_runtime.participants[member.id]
        participant.code = payload.code
        participant.language = payload.language
        task = tasks[0]

        if not payload.code.strip():
            raise HTTPException(status_code=400, detail='Code is empty')

        try:
            await asyncio.to_thread(code_runner.ensure_ready)
        except DockerException as exc:
            raise HTTPException(status_code=503, detail=f'Docker is unavailable: {exc}') from exc

        results, raw_results = await _execute_task_tests(task, payload.language, payload.code)
        participant.latest_task_run_results[payload.task_id] = raw_results
        submission = Submission(
            source_code=payload.code,
            verdict=_submission_verdict_from_results(results),
            finished_at=datetime.now(),
            execution_time_ms=0,
            execution_memory_kb=0,
            room_id=room.id,
            user_id=member.user_id,
            task_id=payload.task_id,
            language_id=language.id,
        )
        session.add(submission)
        await session.flush()

        session.add_all([
            SubmissionTestResult(
                submission_id=submission.id,
                test_id=test_case.id,
                verdict=_result_to_submission_status(result),
                execution_time_ms=0,
                execution_memory_kb=0,
                error_message=result.log.stderr if result.log.stderr else (result.error or ''),
            )
            for test_case, result in zip(task.test_cases, results)
        ])

        await _record_battle_event(
            room_id=room.id,
            event_type='run_code',
            user_id=member.user_id,
            task_id=payload.task_id,
            session=session,
        )

        if all(result.passed for result in results) and payload.task_id not in participant.solved_task_ids:
            participant.solved_task_ids.add(payload.task_id)
            participant.total_time_seconds += room_runtime.time_limit * 60
            solved_event_data = {
                'participant_id': member.id,
                'user_id': member.user_id,
                'task_id': payload.task_id,
                'solved_task_ids': [task_id for task_id in room_runtime.task_ids if task_id in participant.solved_task_ids],
            }
            await _record_battle_event(
                room_id=room.id,
                event_type='task_solved',
                user_id=member.user_id,
                task_id=payload.task_id,
                session=session,
            )

        await session.commit()

    await broadcast_room_event(
        room_id,
        {'type': 'language_change', 'data': {'language': payload.language, 'id': member.id, 'user_id': member.user_id}},
    )

    await broadcast_room_event(
        room_id,
        {'type': 'code_update', 'data': {'code': payload.code, 'id': member.id, 'user_id': member.user_id}},
    )

    if solved_event_data is not None:
        await broadcast_room_event(
            room_id,
            {'type': 'participant_task_solved', 'data': solved_event_data},
        )

    return {'type': 'run_code_result', 'data': {'task_id': payload.task_id, 'results': [result.model_dump() for result in results]}}


async def _execute_task_tests(task, language: str, code: str):
    results = []
    raw_results = []
    for test_case in task.test_cases:
        try:
            execution = await asyncio.to_thread(
                code_runner.run_once,
                language,
                code,
                test_case.input_data,
                task.time_limit_ms,
                task.memory_limit_mb,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except DockerException as exc:
            raise HTTPException(status_code=503, detail=f'Docker execution failed: {exc}') from exc

        actual = _normalize_output(execution.stdout)
        expected = _normalize_output(test_case.expected_output)
        passed = (not execution.timed_out) and execution.exit_code == 0 and actual == expected
        error_kind = _build_error_kind(
            stderr=execution.stderr,
            timed_out=execution.timed_out,
            exit_code=execution.exit_code,
            passed=passed,
        )
        execution_log = RunCodeExecutionLogResponse(
            stdout=execution.stdout,
            stderr=execution.stderr,
            exit_code=execution.exit_code,
            timed_out=execution.timed_out,
        )

        if test_case.is_hidden:
            result = RunCodeResultResponse(
                passed=passed,
                error=error_kind,
                log=execution_log,
            )
            ai_public_view = {
                'passed': passed,
                'error': error_kind,
                'input': None,
                'expected': None,
                'actual': None,
                'log': execution_log.model_dump(),
            }
        else:
            result = RunCodeResultResponse(
                input=test_case.input_data,
                expected=test_case.expected_output,
                actual=actual,
                passed=passed,
                error=error_kind,
                log=execution_log,
            )
            ai_public_view = {
                'passed': passed,
                'error': error_kind,
                'input': test_case.input_data,
                'expected': test_case.expected_output,
                'actual': actual,
                'log': execution_log.model_dump(),
            }

        results.append(result)
        raw_results.append({'public_view': ai_public_view})

    return results, raw_results


async def _stream_ai_hint_chunks_to_websocket(websocket: WebSocket, stream_kwargs: dict) -> str:
    queue: asyncio.Queue[tuple[str, str | None]] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def worker() -> None:
        try:
            for chunk in ai_hint_service.stream_hint(**stream_kwargs):
                loop.call_soon_threadsafe(queue.put_nowait, ('chunk', chunk))
            loop.call_soon_threadsafe(queue.put_nowait, ('done', None))
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, ('error', str(exc)))

    threading.Thread(target=worker, daemon=True).start()

    full_text = ''
    while True:
        event_type, payload = await queue.get()
        if event_type == 'chunk':
            chunk = payload or ''
            full_text += chunk
            await websocket.send_json({'type': 'ai_hint_chunk', 'data': {'delta': chunk}})
            continue

        if event_type == 'done':
            return full_text.strip()

        if event_type == 'error':
            raise RuntimeError(payload or 'Unknown AI streaming error')


async def handle_ask_ai_hint(room_id: str, user: User, payload_data: object, websocket: WebSocket):
    try:
        payload = AskAiHintRequest.model_validate(payload_data)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc

    async with AsyncSessionFactory() as session:
        room, member = await require_room_membership(session, room_id, user)
        room_runtime = await hydrate_room_runtime(session, room)
        participant = room_runtime.participants.get(member.id)
        if participant is None:
            raise HTTPException(status_code=404, detail='Участник не найден')

        if payload.task_id not in room_runtime.task_ids:
            raise HTTPException(status_code=404, detail='Задача не найдена')

        tasks = await get_tasks_by_ids(session, [payload.task_id])
        if not tasks:
            raise HTTPException(status_code=404, detail='Задача не найдена')
        task = tasks[0]

        try:
            ai_hint_service.validate_hint_request(
                user_question=payload.question,
                code=participant.code,
                has_used_hint=payload.task_id in participant.asked_ai_task_ids,
            )
        except ValueError as exc:
            if 'уже использована' in str(exc):
                raise HTTPException(status_code=409, detail=str(exc)) from exc
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        run_results = participant.latest_task_run_results.get(payload.task_id)
        if not run_results:
            try:
                await asyncio.to_thread(code_runner.ensure_ready)
            except DockerException as exc:
                raise HTTPException(status_code=503, detail=f'Docker is unavailable: {exc}') from exc

            _, run_results = await _execute_task_tests(task, participant.language, participant.code)
            participant.latest_task_run_results[payload.task_id] = run_results

        stream_kwargs = {
            'task_title': task.title,
            'task_description': task.description,
            'task_examples': [{'input': example.input_data, 'output': example.output_data} for example in task.examples],
            'language': participant.language,
            'code': participant.code,
            'user_question': payload.question,
            'run_results': run_results,
            'role': participant.role,
            'battle_phase': room_runtime.status,
        }

        try:
            logger.info('AI hint requested: room_id=%s user_id=%s task_id=%s', room_id, user.id, payload.task_id)
            await websocket.send_json({'type': 'ai_hint_started', 'data': {'task_id': payload.task_id}})
            hint = await _stream_ai_hint_chunks_to_websocket(websocket, stream_kwargs)
            logger.info('AI hint completed: room_id=%s user_id=%s task_id=%s chars=%s', room_id, user.id, payload.task_id, len(hint))
        except ValueError as exc:
            logger.warning('AI hint failed validation: room_id=%s user_id=%s task_id=%s error=%s', room_id, user.id, payload.task_id, exc)
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception('AI hint request failed: room_id=%s user_id=%s task_id=%s', room_id, user.id, payload.task_id)
            raise HTTPException(status_code=502, detail=f'AI request failed: {exc}') from exc

        participant.asked_ai_task_ids.add(payload.task_id)
        participant.ai_hint_history[payload.task_id] = {
            'question': payload.question,
            'answer': hint,
        }
        session.add(
            AiHintEvent(
                room_id=room.id,
                user_id=member.user_id,
                task_id=payload.task_id,
                question=payload.question,
                answer=hint,
            )
        )
        await _record_battle_event(
            room_id=room.id,
            event_type='ask_ai_hint',
            user_id=member.user_id,
            task_id=payload.task_id,
            session=session,
        )
        await session.commit()

    return {
        'type': 'ai_hint_result',
        'data': {
            'task_id': payload.task_id,
            'hint': hint,
            'remaining': 0,
        },
    }


@router.websocket('/rooms/{room_id}')
async def mirror_room_websocket(websocket: WebSocket, room_id: str):
    user = await get_websocket_user(websocket)
    if user is None:
        return await websocket.close(code=1008)

    async with AsyncSessionFactory() as session:
        room = await session.get(Room, room_id)
        if room is None:
            return await websocket.close(code=1008)

        member = (
            await session.exec(
                select(RoomMember).where(
                    RoomMember.room_id == room_id,
                    RoomMember.user_id == user.id,
                )
            )
        ).first()

        if member is None:
            return await websocket.close(code=1008)

        room_runtime = await hydrate_room_runtime(session, room)
        ensure_room_auto_finish(room_id, room.started_at if room.status != RoomStatus.FINISHED else None)

    first_connection = await room_connection_manager.connect(room_id, member.id, websocket)
    if first_connection:
        await broadcast_room_event(
            room_id,
            {'type': 'participant_joined', 'data': build_participant_socket_payload(member.id, user, room)},
        )

    try:
        while True:
            received_payload = await websocket.receive_json()
            if not isinstance(received_payload, dict):
                await send_socket_error(websocket, 'Invalid payload')
                continue

            payload_type = received_payload.get('type')
            payload_data = received_payload.get('data', {})
            if not isinstance(payload_data, dict):
                payload_data = {}

            participant = room_runtime.participants.get(member.id)
            if participant is None:
                continue

            if payload_type == 'code_update':
                participant.code = payload_data.get('code', participant.code)
                await broadcast_room_event(
                    room_id,
                    {'type': 'code_update', 'data': {'code': participant.code, 'id': member.id, 'user_id': member.user_id}},
                )
                continue

            if payload_type == 'language_change':
                next_language = payload_data.get('language', participant.language)
                if next_language not in room_runtime.languages:
                    await send_socket_error(websocket, 'Unsupported language')
                    continue

                participant.language = next_language
                await broadcast_room_event(
                    room_id,
                    {'type': 'language_change', 'data': {'language': participant.language, 'id': member.id, 'user_id': member.user_id}},
                )
                continue

            try:
                if payload_type == 'start_battle':
                    await handle_start_battle(room_id, user)
                    continue

                if payload_type == 'pause_battle':
                    await handle_pause_battle(room_id, user)
                    continue

                if payload_type == 'next_task':
                    await handle_next_task(room_id, user)
                    continue

                if payload_type == 'finish_battle':
                    await handle_finish_battle(room_id, user)
                    continue

                if payload_type == 'run_code':
                    await websocket.send_json(await handle_run_code(room_id, user, payload_data))
                    continue

                if payload_type == 'ask_ai_hint':
                    await websocket.send_json(await handle_ask_ai_hint(room_id, user, payload_data, websocket))
                    continue

                await send_socket_error(websocket, 'Unknown message type')
            except HTTPException as exc:
                await send_socket_error(websocket, exc.detail, exc.status_code)
    except WebSocketDisconnect:
        pass
    finally:
        disconnected_participant_id = await room_connection_manager.disconnect(room_id, websocket)
        if disconnected_participant_id is not None:
            await broadcast_participant_left(room_id, disconnected_participant_id)
