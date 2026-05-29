from __future__ import annotations

from app.analytics_service import (
    ParticipantTaskProgress,
    _build_rule_based_risk,
    _error_code,
    _mean_or_none,
    _risk_level,
    _safe_percent,
)
from app.models import SubmissionStatus


def test_safe_percent_handles_zero_and_rounds():
    assert _safe_percent(5, 0) == 0.0
    assert _safe_percent(1, 3) == 33.33


def test_mean_or_none_for_empty_and_non_empty():
    assert _mean_or_none([]) is None
    assert _mean_or_none([1, 2, 3]) == 2.0
    assert _mean_or_none([1, 2]) == 1.5


def test_error_code_mapping():
    assert _error_code(SubmissionStatus.WRONG_ANSWER.value) == 1
    assert _error_code(SubmissionStatus.RUNTIME_ERROR.value) == 2
    assert _error_code(SubmissionStatus.TIME_LIMIT_EXCEEDED.value) == 3
    assert _error_code(SubmissionStatus.COMPILE_ERROR.value) == 4
    assert _error_code(SubmissionStatus.ACCEPTED.value) == 0


def test_risk_level_boundaries():
    assert _risk_level(0.39) == 'low'
    assert _risk_level(0.4) == 'medium'
    assert _risk_level(0.7) == 'medium'
    assert _risk_level(0.71) == 'high'


def test_rule_based_risk_is_clamped_and_hint_reduces_score():
    no_hint = ParticipantTaskProgress(
        participant_id='p1',
        user_id='u1',
        username='User 1',
        attempts=3,
        elapsed_ratio=0.6,
        failed_ratio=0.5,
        historical_avg_attempts_to_ac=4.0,
        last_error_code=2,
        used_hint=0,
    )
    with_hint = ParticipantTaskProgress(
        participant_id='p1',
        user_id='u1',
        username='User 1',
        attempts=3,
        elapsed_ratio=0.6,
        failed_ratio=0.5,
        historical_avg_attempts_to_ac=4.0,
        last_error_code=2,
        used_hint=1,
    )

    score_no_hint = _build_rule_based_risk(no_hint)
    score_with_hint = _build_rule_based_risk(with_hint)

    assert 0.01 <= score_no_hint <= 0.99
    assert 0.01 <= score_with_hint <= 0.99
    assert score_with_hint < score_no_hint

