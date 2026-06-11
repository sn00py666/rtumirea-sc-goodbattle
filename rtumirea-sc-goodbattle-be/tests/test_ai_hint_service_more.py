from __future__ import annotations

import pytest

from app.ai_hint_service import (
    LOG_TEXT_LIMIT,
    AiHintService,
    AntiFullSolutionFilterHandler,
    ForbiddenPhraseFilterHandler,
    ResponseLengthFilterHandler,
)


def test_trim_without_truncation():
    assert AiHintService._trim('abc', 5) == 'abc'


def test_trim_with_truncation_adds_suffix():
    text = 'x' * 30
    trimmed = AiHintService._trim(text, 20)
    assert trimmed.endswith('\n... [truncated]')
    assert len(trimmed) <= 20


def test_log_text_without_truncation():
    assert AiHintService._log_text('ok') == 'ok'


def test_log_text_with_truncation_adds_suffix():
    text = 'x' * (LOG_TEXT_LIMIT + 10)
    logged = AiHintService._log_text(text)
    assert logged.endswith('\n... [log truncated]')
    assert len(logged) > LOG_TEXT_LIMIT


def test_format_run_results_renders_expected_fields():
    run_results = [
        {
            'public_view': {
                'passed': False,
                'error': 'wrong_answer',
                'input': '1 2',
                'expected': '3',
                'actual': '4',
                'log': {'stdout': '4', 'stderr': '', 'exit_code': 0, 'timed_out': False},
            }
        }
    ]

    formatted = AiHintService._format_run_results(run_results)
    assert 'Test #1' in formatted
    assert 'passed: False' in formatted
    assert 'error: wrong_answer' in formatted
    assert 'input: 1 2' in formatted
    assert 'expected: 3' in formatted
    assert 'actual: 4' in formatted
    assert 'stdout: 4' in formatted


@pytest.mark.parametrize(
    ('role', 'phase', 'expected_role_note'),
    [
        ('organizer', 'running', 'User role: organizer.'),
        ('participant', 'waiting', 'User role: participant.'),
        ('participant', 'paused', 'Battle phase: paused.'),
    ],
)
def test_build_system_prompt_contains_role_and_phase(role: str, phase: str, expected_role_note: str):
    prompt = AiHintService._build_system_prompt(role=role, battle_phase=phase)
    assert expected_role_note in prompt
    assert f'Battle phase: {phase}.' in prompt
    assert 'Respond in Russian.' in prompt


def test_anti_full_solution_filter_removes_code_blocks_and_definitions():
    handler = AntiFullSolutionFilterHandler()
    raw = "```python\nprint('x')\n```\ndef solve():\n  pass\nuse idea"
    filtered = handler.handle(raw)
    assert '[code removed by policy]' in filtered
    assert 'def solve' not in filtered
    assert 'use idea' in filtered


def test_forbidden_phrase_filter_strips_phrases():
    handler = ForbiddenPhraseFilterHandler()
    text = 'если хочешь, могу еще помочь, но уже все'
    filtered = handler.handle(text)
    assert 'если хочешь' not in filtered
    assert 'могу еще' not in filtered


@pytest.mark.parametrize(
    ('text', 'max_words', 'expected'),
    [
        ('one two three', 5, 'one two three'),
        ('one two three', 3, 'one two three'),
        ('one two three four', 3, 'one two three'),
        ('a b c d e', 1, 'a'),
    ],
)
def test_response_length_filter_handler(text: str, max_words: int, expected: str):
    assert ResponseLengthFilterHandler(max_words=max_words).handle(text) == expected


def test_post_process_hint_strips_outer_whitespace():
    service = AiHintService()
    processed = service._post_process_hint('   полезный намек   ')
    assert processed == 'полезный намек'

