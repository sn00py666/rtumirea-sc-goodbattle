from __future__ import annotations

import random

import pytest

from app.demo_seed import _fake_source_code, _pick_languages, _pick_tasks, is_demo_seed_enabled
from app.models import Language, SubmissionStatus, Task


@pytest.mark.parametrize('raw', ['1', 'true', 'TRUE', 'yes', 'on', ' On '])
def test_is_demo_seed_enabled_true_values(monkeypatch, raw: str):
    monkeypatch.setenv('ANALYTICS_DEMO_SEED_ENABLED', raw)
    assert is_demo_seed_enabled() is True


@pytest.mark.parametrize('raw', ['', '0', 'false', 'no', 'off', 'random'])
def test_is_demo_seed_enabled_false_values(monkeypatch, raw: str):
    monkeypatch.setenv('ANALYTICS_DEMO_SEED_ENABLED', raw)
    assert is_demo_seed_enabled() is False


def test_pick_tasks_clamps_count_lower_bound():
    tasks = [
        Task(id='t1', title='T1', description='d', time_limit_ms=1000, memory_limit_mb=64),
        Task(id='t2', title='T2', description='d', time_limit_ms=1000, memory_limit_mb=64),
    ]
    picked = _pick_tasks(tasks, random.Random(1), count=0)
    assert len(picked) == 1


def test_pick_tasks_clamps_count_upper_bound():
    tasks = [
        Task(id='t1', title='T1', description='d', time_limit_ms=1000, memory_limit_mb=64),
        Task(id='t2', title='T2', description='d', time_limit_ms=1000, memory_limit_mb=64),
    ]
    picked = _pick_tasks(tasks, random.Random(1), count=10)
    assert len(picked) == 2
    assert {task.id for task in picked} == {'t1', 't2'}


def test_pick_languages_clamps_count_lower_and_upper_bounds():
    languages = [
        Language(id=1, code='python', name='Python'),
        Language(id=2, code='javascript', name='JavaScript'),
        Language(id=3, code='cpp', name='C++'),
    ]

    low = _pick_languages(languages, random.Random(2), count=-5)
    high = _pick_languages(languages, random.Random(2), count=50)

    assert len(low) == 1
    assert len(high) == 3
    assert {lang.id for lang in high} == {1, 2, 3}


@pytest.mark.parametrize(
    ('verdict', 'expected_fragment'),
    [
        (SubmissionStatus.ACCEPTED, '# accepted attempt'),
        (SubmissionStatus.COMPILE_ERROR, "print('oops'"),
        (SubmissionStatus.RUNTIME_ERROR, 'arr=[]'),
        (SubmissionStatus.TIME_LIMIT_EXCEEDED, 'while True'),
        (SubmissionStatus.WRONG_ANSWER, 'wrong answer'),
    ],
)
def test_fake_source_code_variants(verdict: SubmissionStatus, expected_fragment: str):
    code = _fake_source_code(task_id='task-1234', verdict=verdict, attempt=2)
    assert expected_fragment in code

