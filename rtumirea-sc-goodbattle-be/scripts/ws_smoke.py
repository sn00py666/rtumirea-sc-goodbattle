from __future__ import annotations

import asyncio
import json

import requests
import websockets

BASE_URL = 'http://localhost:8000'
WS_BASE_URL = 'ws://localhost:8000/ws/rooms'
TASK_ID = 'd290f1ee-6c54-4b01-90e6-d701748f0851'
EMAIL = 'localtest@example.com'
PASSWORD = '12345678'


def login_and_get_session() -> str:
    response = requests.post(
        f'{BASE_URL}/api/auth/login',
        json={'email': EMAIL, 'password': PASSWORD},
        timeout=15,
    )
    response.raise_for_status()
    token = response.cookies.get('session')
    if not token:
        raise RuntimeError('session cookie is missing in login response')
    return token


def create_room(session_token: str) -> str:
    response = requests.post(
        f'{BASE_URL}/api/rooms',
        json={'languages': ['python'], 'task_ids': [TASK_ID], 'time_limit': 5},
        headers={'Cookie': f'session={session_token}'},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()['room_id']


async def run_case(session_token: str, room_id: str, code: str) -> dict:
    async with websockets.connect(
        f'{WS_BASE_URL}/{room_id}',
        additional_headers={'Cookie': f'session={session_token}'},
    ) as socket:
        await socket.send(
            json.dumps(
                {
                    'type': 'run_code',
                    'data': {
                        'task_id': TASK_ID,
                        'language': 'python',
                        'code': code,
                    },
                }
            )
        )

        while True:
            payload = json.loads(await socket.recv())
            if payload.get('type') == 'run_code_result':
                return payload


def contains_error(results: list[dict], error_kind: str) -> bool:
    return any(result.get('error') == error_kind for result in results)


async def main() -> int:
    token = login_and_get_session()
    room_id = create_room(token)

    checks = [
        ('OK', 's=input()\nprint(s[::-1])', lambda results: all(item.get('passed') for item in results)),
        ('WA', 'print("42")', lambda results: contains_error(results, 'wrong_answer')),
        ('RE', 'raise Exception("x")', lambda results: contains_error(results, 'runtime_error')),
        ('TLE', 'while True:\n    pass', lambda results: contains_error(results, 'time_limit_exceeded')),
    ]

    all_passed = True
    print(f'Room id: {room_id}')

    for label, code, validator in checks:
        response = await run_case(token, room_id, code)
        results = response['data']['results']
        passed = validator(results)
        status = 'PASS' if passed else 'FAIL'
        print(f'[{status}] {label}: {json.dumps(results, ensure_ascii=False)}')
        all_passed = all_passed and passed

    return 0 if all_passed else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
