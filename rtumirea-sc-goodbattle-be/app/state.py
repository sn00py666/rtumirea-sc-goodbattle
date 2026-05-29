from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket

from app.schemas import BattleResultResponse

MAX_ROOM_PARTICIPANTS = 8


@dataclass(slots=True)
class ParticipantRuntime:
    user_id: str
    username: str
    role: str
    code: str = ''
    language: str = 'javascript'
    solved_task_ids: Set[str] = field(default_factory=set)
    total_time_seconds: int = 0
    asked_ai_task_ids: Set[str] = field(default_factory=set)
    latest_task_run_results: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    ai_hint_history: Dict[str, Dict[str, str]] = field(default_factory=dict)


@dataclass(slots=True)
class RoomRuntime:
    languages: List[str]
    task_ids: List[str]
    time_limit: int
    current_task_index: int = 0
    status: str = 'waiting'
    participants: Dict[str, ParticipantRuntime] = field(default_factory=dict)
    auto_finish_task: Optional[asyncio.Task] = None


ROOM_STATES = {}


def create_room_runtime(room_id: str, languages: List[str], task_ids: List[str], time_limit: int) -> RoomRuntime:
    room_runtime = RoomRuntime(languages=languages, task_ids=task_ids, time_limit=time_limit)
    ROOM_STATES[room_id] = room_runtime
    return room_runtime


def get_room_runtime(room_id: str) -> Optional[RoomRuntime]:
    return ROOM_STATES.get(room_id)


def ensure_room_runtime(room_id: str, languages: List[str], task_ids: List[str], time_limit: int) -> RoomRuntime:
    existing_runtime = ROOM_STATES.get(room_id)
    if existing_runtime:
        return existing_runtime

    return create_room_runtime(room_id, languages=languages, task_ids=task_ids, time_limit=time_limit)


def build_battle_results(room_runtime: RoomRuntime) -> List[BattleResultResponse]:
    ranked_participants = sorted(
        (
            (participant_id, participant)
            for participant_id, participant in room_runtime.participants.items()
            if participant.role == 'participant'
        ),
        key=lambda item: (
            -len(item[1].solved_task_ids),
            item[1].total_time_seconds,
            item[0],
        ),
    )

    battle_results = []
    for place, (participant_id, participant) in enumerate(ranked_participants, start=1):
        battle_results.append(
            BattleResultResponse(
                place=place,
                username=participant.username,
                participant_id=participant_id,
                solved_tasks=len(participant.solved_task_ids),
                total_tasks=len(room_runtime.task_ids),
                total_time=participant.total_time_seconds
            )
        )

    return battle_results


class RoomConnectionManager:
    def __init__(self):
        self._connections = {}
        self._participant_connections = {}
        self._lock = asyncio.Lock()

    async def connect(self, room_id: str, participant_id: str, websocket: WebSocket) -> bool:
        await websocket.accept()
        async with self._lock:
            room_connections = self._connections.setdefault(room_id, {})
            room_connections[websocket] = participant_id

            participant_connections = self._participant_connections.setdefault(room_id, {})
            participant_connections[participant_id] = participant_connections.get(participant_id, 0) + 1
            return participant_connections[participant_id] == 1

    async def disconnect(self, room_id: str, websocket: WebSocket) -> Optional[str]:
        async with self._lock:
            room_connections = self._connections.get(room_id, {})
            participant_id = room_connections.pop(websocket, None)
            if participant_id is None:
                return None

            participant_connections = self._participant_connections.get(room_id, {})
            active_connections = participant_connections.get(participant_id, 0) - 1
            if active_connections > 0:
                participant_connections[participant_id] = active_connections
                participant_left = None
            else:
                participant_connections.pop(participant_id, None)
                participant_left = participant_id

            if not room_connections and room_id in self._connections:
                del self._connections[room_id]
            if not participant_connections and room_id in self._participant_connections:
                del self._participant_connections[room_id]

            return participant_left

    async def broadcast(self, room_id: str, payload: Dict[str, Any]) -> List[str]:
        async with self._lock:
            room_connections = list(self._connections.get(room_id, {}).keys())

        disconnected_connections = []
        for websocket in room_connections:
            try:
                await websocket.send_json(payload)
            except Exception:
                disconnected_connections.append(websocket)

        disconnected_participants = []
        for websocket in disconnected_connections:
            participant_id = await self.disconnect(room_id, websocket)
            if participant_id is not None and participant_id not in disconnected_participants:
                disconnected_participants.append(participant_id)

        return disconnected_participants


room_connection_manager = RoomConnectionManager()
