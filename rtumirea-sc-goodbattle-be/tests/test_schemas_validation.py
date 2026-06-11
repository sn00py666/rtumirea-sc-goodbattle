from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import (
    AskAiHintRequest,
    CreateRoomRequest,
    LoginRequest,
    RegisterRequest,
    RunCodeRequest,
    TaskExampleRequest,
    TaskTestCaseRequest,
)


def test_register_request_valid():
    payload = RegisterRequest(
        email='test@mail.com',
        username='Andrey',
        password='qwerty123',
    )
    assert payload.email == 'test@mail.com'


@pytest.mark.parametrize(
    'email',
    ['bad-email', 'test', 'abc@', '@mail.com'],
)
def test_register_request_invalid_email(email: str):
    with pytest.raises(ValidationError):
        RegisterRequest(email=email, username='User', password='qwerty123')


@pytest.mark.parametrize('username', ['', 'a'])
def test_register_request_invalid_username_length(username: str):
    with pytest.raises(ValidationError):
        RegisterRequest(email='test@mail.com', username=username, password='qwerty123')


@pytest.mark.parametrize('password', ['', '12345'])
def test_register_request_invalid_password_length(password: str):
    with pytest.raises(ValidationError):
        RegisterRequest(email='test@mail.com', username='User', password=password)


def test_login_request_valid():
    request = LoginRequest(email='test@mail.com', password='x')
    assert request.password == 'x'


def test_login_request_invalid_empty_password():
    with pytest.raises(ValidationError):
        LoginRequest(email='test@mail.com', password='')


def test_create_room_request_valid():
    request = CreateRoomRequest(
        languages=['python', 'javascript'],
        task_ids=['t1', 't2'],
        time_limit=10,
    )
    assert request.time_limit == 10


@pytest.mark.parametrize('time_limit', [0, -1, 31, 100])
def test_create_room_request_invalid_time_limit(time_limit: int):
    with pytest.raises(ValidationError):
        CreateRoomRequest(languages=['python'], task_ids=['t1'], time_limit=time_limit)


def test_create_room_request_requires_languages():
    with pytest.raises(ValidationError):
        CreateRoomRequest(languages=[], task_ids=['t1'], time_limit=10)


def test_create_room_request_requires_task_ids():
    with pytest.raises(ValidationError):
        CreateRoomRequest(languages=['python'], task_ids=[], time_limit=10)


def test_ask_ai_hint_request_max_length_allowed():
    req = AskAiHintRequest(task_id='t1', question='x' * 100)
    assert len(req.question) == 100


def test_ask_ai_hint_request_too_long():
    with pytest.raises(ValidationError):
        AskAiHintRequest(task_id='t1', question='x' * 101)


def test_task_example_request_valid():
    req = TaskExampleRequest(input='1 2', output='3')
    assert req.output == '3'


@pytest.mark.parametrize(
    ('input_value', 'output_value'),
    [
        ('', '1'),
        ('1', ''),
        ('', ''),
    ],
)
def test_task_example_request_invalid(input_value: str, output_value: str):
    with pytest.raises(ValidationError):
        TaskExampleRequest(input=input_value, output=output_value)


def test_task_test_case_request_default_hidden_true():
    req = TaskTestCaseRequest(input='1', expected_output='1')
    assert req.is_hidden is True


def test_run_code_request_valid():
    req = RunCodeRequest(code='print(1)', language='python', task_id='t1')
    assert req.language == 'python'


def test_run_code_request_missing_task_id():
    with pytest.raises(ValidationError):
        RunCodeRequest(code='print(1)', language='python')  # type: ignore[call-arg]

