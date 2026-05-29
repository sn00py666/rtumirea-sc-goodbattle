from __future__ import annotations

import pytest

from app.ai_hint_service import (
    MAX_AI_QUESTION_CHARS,
    AiHintService,
    ResponseLengthFilterHandler,
)


def test_validate_hint_request_success():
    service = AiHintService()

    service.validate_hint_request(
        user_question='Как исправить ошибку?',
        code='print(1)',
        has_used_hint=False,
    )


def test_validate_hint_request_empty_question():
    service = AiHintService()

    with pytest.raises(ValueError, match='Question is required'):
        service.validate_hint_request(
            user_question='   ',
            code='print(1)',
            has_used_hint=False,
        )


def test_validate_hint_request_too_long_question():
    service = AiHintService()
    question = 'x' * (MAX_AI_QUESTION_CHARS + 1)

    with pytest.raises(ValueError, match='Question is too long'):
        service.validate_hint_request(
            user_question=question,
            code='print(1)',
            has_used_hint=False,
        )


def test_validate_hint_request_already_used_hint():
    service = AiHintService()

    with pytest.raises(ValueError, match='уже использована'):
        service.validate_hint_request(
            user_question='Что делать?',
            code='print(1)',
            has_used_hint=True,
        )


def test_validate_hint_request_no_code():
    service = AiHintService()

    with pytest.raises(ValueError, match='Сначала нужно написать код'):
        service.validate_hint_request(
            user_question='Что делать?',
            code='   ',
            has_used_hint=False,
        )


def test_post_process_hint_removes_forbidden_parts():
    service = AiHintService()
    raw = (
        "```python\nprint('secret')\n```\n"
        "def solve():\n"
        "если хочешь, могу еще помочь\n"
        "Смотри на граничные случаи"
    )

    processed = service._post_process_hint(raw)

    assert '[code removed by policy]' in processed
    assert 'def solve' not in processed
    assert 'если хочешь' not in processed
    assert 'могу еще' not in processed
    assert 'Смотри на граничные случаи' in processed


def test_response_length_filter_truncates_by_word_count():
    text = 'one two three four five'
    filtered = ResponseLengthFilterHandler(max_words=3).handle(text)
    assert filtered == 'one two three'

