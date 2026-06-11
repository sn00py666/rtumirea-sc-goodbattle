from __future__ import annotations

from app.analytics_service import (
    _mean_or_none,
    _safe_percent,
)


def test_safe_percent_handles_zero_and_rounds():
    assert _safe_percent(5, 0) == 0.0
    assert _safe_percent(1, 3) == 33.33


def test_mean_or_none_for_empty_and_non_empty():
    assert _mean_or_none([]) is None
    assert _mean_or_none([1, 2, 3]) == 2.0
    assert _mean_or_none([1, 2]) == 1.5
