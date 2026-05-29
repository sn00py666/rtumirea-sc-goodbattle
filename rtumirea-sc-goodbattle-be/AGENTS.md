# Good Battle Backend - Project Guide for Agents

This document explains what this repository does, how it is structured, which technologies it uses, and what behavior to keep in mind when working on it.

## 1. Project Purpose

Good Battle is a real-time programming battle platform backend.

Core idea:
- Users join a battle room and solve coding tasks under time pressure.
- Participants can see each other's code progress in real time via WebSocket events.
- The organizer controls battle flow (start, pause, next task, finish) but does not compete.
- Code is executed in isolated Docker containers per supported language.
- Participants can request an AI hint (limited usage per task).

In short: this is a FastAPI backend for synchronized multiplayer coding competitions.

## 2. High-Level Architecture

The system has two execution/state layers:

1. Persistent layer (PostgreSQL via SQLModel/SQLAlchemy)
- Users, rooms, memberships, tasks, examples, test cases, languages, and links are stored in DB.

2. Runtime layer (in-memory process state)
- Real-time battle runtime is held in `app/state.py` (`ROOM_STATES` dict).
- Participant code drafts, selected language, solved tasks, AI hint usage/history, and live connections are kept in memory.

Implication:
- Runtime battle state is process-local and not durable across backend restarts.

## 3. Technology Stack

- Language: Python 3.12
- Web framework: FastAPI + Starlette
- ASGI server: Uvicorn
- ORM/data layer: SQLModel + SQLAlchemy Async + asyncpg
- Validation: Pydantic v2
- Auth: JWT in HTTP-only cookie (`session`), password hashing via bcrypt
- Real-time transport: WebSocket
- Code execution sandbox: Docker SDK for Python, per-language containers
- AI integration: OpenAI Responses API (with streaming)
- Config: `.env` (via `python-dotenv`)
- Containers/orchestration: Docker + Docker Compose

## 4. Repository Structure

`main.py`
- FastAPI app bootstrap.
- Configures logging, CORS, validation error mapping to 400, router registration.
- Lifespan startup initializes DB and optionally pre-pulls runner images.

`app/`
- `models.py`: SQLModel entities and enums.
- `schemas.py`: Pydantic request/response envelopes.
- `database.py`: async engine/session, schema migration helpers, default seeding.
- `auth.py`: password hashing + JWT encode/decode.
- `dependencies.py`: auth dependency to resolve current user from cookie token.
- `state.py`: in-memory room runtime + WebSocket connection manager + ranking logic.
- `room_service.py`: room/battle domain services (membership checks, hydration, payload assembly).
- `code_runner.py`: Docker-based one-shot code runner used by production API.
- `ai_hint_service.py`: OpenAI hint generation/streaming with strict prompt policy and truncation.

`app/routes/`
- `auth.py`: register/login/logout/me.
- `profile.py`: aggregated user profile metrics.
- `languages.py`: list available programming languages.
- `tasks.py`: CRUD-like task APIs (create/list/get/update).
- `rooms.py`: create room, join room, get room details.
- `battles.py`: battle history list for current user.
- `ws.py`: main WebSocket protocol and real-time orchestration.

`docs/ws-events.md`
- WebSocket contract documentation (client -> server and server -> client events).

`scripts/ws_smoke.py`
- Smoke script for WebSocket run-code path and verdict checks.

`code-runner/`
- Standalone local/demo code runner implementation and config.
- `languages.json` defines image, filename, command per language.

`Dockerfile`, `docker-compose.yml`
- Local containerized deployment (app + postgres).
- App mounts Docker socket to run code in sibling containers.

`requirements.txt`
- Backend dependencies (includes web stack, DB drivers, Docker SDK, OpenAI SDK).

## 5. Data Model Summary

Main entities in `app/models.py`:
- `User`: account identity.
- `Room`: battle room with status/time limit/current task index.
- `RoomMember`: room-user link with role (`organizer`/`participant`).
- `Task`: coding problem.
- `TaskExample`: visible examples.
- `TestCase`: judge tests (can be hidden).
- `Language`: supported language metadata.
- `RoomTaskLink`: ordered many-to-many room<->task.
- `RoomLanguageLink`: ordered many-to-many room<->language.
- `Submission` + `SubmissionTestResult`: prepared DB entities for submissions/results (runtime judging currently tracked mainly in memory during battle flow).

Enums:
- `RoomStatus`: waiting/running/paused/finished
- `MemberRole`: organizer/participant
- `SubmissionStatus`: pending/accepted/wrong_answer/runtime_error/time_limit_exceeded

## 6. API Surface

HTTP routers:
- `/api/auth/*`: auth/session endpoints.
- `/api/profile`: profile statistics.
- `/api/languages`: list language options.
- `/api/tasks`, `/api/tasks/{task_id}`: task management.
- `/api/rooms`, `/api/rooms/join`, `/api/rooms/{room_id}`: room lifecycle and details.
- `/api/battles`: user battle history.

WebSocket:
- Endpoint: `/ws/rooms/{room_id}`
- Supports room-wide broadcasts for participant joins/leaves, code updates, language switches, status changes, next-task transitions, solved-task events, and final battle results.
- Supports direct request/response style events for `run_code` and streamed AI hints.

## 7. Runtime Battle Behavior

Room runtime (`RoomRuntime`) stores:
- ordered `languages`
- ordered `task_ids`
- `time_limit` in minutes
- `current_task_index`
- room `status`
- `participants` map (`ParticipantRuntime`)

Participant runtime stores:
- currently typed `code`
- selected `language`
- `solved_task_ids`
- accumulated `total_time_seconds`
- AI hint usage (`asked_ai_task_ids`, `ai_hint_history`)
- latest run result snapshots for AI context

Ranking (`build_battle_results`):
- More solved tasks wins.
- Tie-breaker: lower `total_time_seconds`.
- Final tie-breaker: participant id order.

## 8. Code Execution Flow

Execution path is in `app/routes/ws.py` + `app/code_runner.py`:
- `run_code` validates membership, task/language scope, non-empty source.
- Ensures Docker images are available (`ensure_ready`).
- Runs code against each task test case in a dedicated container.
- Compares normalized stdout (`strip`) against expected output.
- Produces per-test result with `passed`, `error`, and raw execution log.
- Hidden tests mask input/expected/actual in response payload.

Error kinds used in API responses:
- `time_limit_exceeded`
- `compile_error` (currently inferred from `SyntaxError` in stderr)
- `runtime_error`
- `wrong_answer`

Security constraints in runner:
- `network_disabled=True`
- memory limit enforced per container
- timeout enforcement via polling + forced container removal

## 9. AI Hint Flow

AI hint logic lives in `app/ai_hint_service.py` and is triggered via WS `ask_ai_hint`:
- One hint per participant per task.
- Question length max: 100 chars.
- User must have non-empty code.
- If no run logs exist for task, tests are auto-executed first.
- Response is streamed chunk-by-chunk (`ai_hint_chunk`) then final `ai_hint_result`.

Prompt policy (enforced in system prompt):
- Conceptual guidance only, no full solution.
- Short response, Russian language, strict length/style constraints.

## 10. Configuration and Environment

Key env vars (see `.env.example`):
- `SECRET_KEY`
- `JWT_ALGORITHM`
- `TOKEN_EXPIRATION_DAYS`
- `LOG_LEVEL`
- `CODE_RUNNER_WARMUP_PULL_IMAGES`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL` (optional)
- `OPENAI_MODEL`

DB:
- `DATABASE_URL` is mandatory and validated at import time in `app/database.py`.

## 11. Deployment and Local Run

Containerized local setup:
- `docker-compose.yml` runs `app` + `postgres`.
- App uses internal DB URL (`postgres` host).
- Docker socket is mounted into app container so backend can spawn runner containers.

App start command (Dockerfile):
- `uvicorn main:app --host 0.0.0.0 --port 8000`

## 12. Database Initialization and Migration Notes

On startup:
- `SQLModel.metadata.create_all` creates tables.
- lightweight manual schema migration runs in `migrate_database_schema()`.
- default reference data is seeded if empty:
  - 5 languages (JS/Python/C++/Java/Go)
  - 3 starter tasks (Russian descriptions/examples/tests)

Migration helper includes compatibility logic for older room schema (legacy columns to link tables) and adds `task.creator_id` when missing.

## 13. Conventions and Observations

- Many user-facing messages and seeded tasks are in Russian.
- Cookies are set as `httponly`, `secure=True`, `samesite='none'` (designed for HTTPS/cross-site frontend scenarios).
- CORS is currently permissive (`*`).
- There is no dedicated test suite in this repository; `scripts/ws_smoke.py` is a practical integration smoke check.
- Runtime and WebSocket fanout are single-process in-memory; horizontal scaling would require shared state and pub/sub.

## 14. Practical Change Guidance for Future Agents

When editing this project:
- Keep DB models/schemas/service payloads synchronized.
- Preserve room runtime hydration logic in `room_service.py`; it is critical for restoring in-memory state from DB.
- Be careful with WebSocket event names/payload fields; frontend depends on them.
- Treat Docker runner changes as security-sensitive.
- Keep AI prompt constraints aligned with product policy (short hints, no full solutions).
- If adding new language support, update both DB seed language list and `code-runner/languages.json` (and any frontend assumptions).

This file is intentionally detailed so that a new coding agent can understand architecture and contribute safely without re-discovering project behavior from scratch.
