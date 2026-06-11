from __future__ import annotations

import pytest

from app.ai_analytics_service import AiAnalyticsService, MAX_RESULT_ROWS


def test_validate_and_prepare_sql_adds_limit_when_missing():
    service = AiAnalyticsService()

    sql = service._validate_and_prepare_sql('SELECT id, username FROM "user"')

    assert f'LIMIT {MAX_RESULT_ROWS}' in sql


def test_validate_and_prepare_sql_replaces_too_large_limit():
    service = AiAnalyticsService()

    sql = service._validate_and_prepare_sql('SELECT id FROM room LIMIT 9999')

    assert sql.lower().endswith(f'limit {MAX_RESULT_ROWS}'.lower())


def test_validate_and_prepare_sql_rejects_dml():
    service = AiAnalyticsService()

    with pytest.raises(ValueError, match='Разрешены только SELECT/CTE'):
        service._validate_and_prepare_sql("DELETE FROM room WHERE id = '1'")


def test_validate_and_prepare_sql_rejects_sensitive_columns():
    service = AiAnalyticsService()

    with pytest.raises(ValueError, match='Запрещенный столбец'):
        service._validate_and_prepare_sql('SELECT password_hash FROM "user" LIMIT 10')


def test_validate_and_prepare_sql_allows_cte_aliases():
    service = AiAnalyticsService()

    sql = service._validate_and_prepare_sql(
        'WITH stats AS (SELECT room_id, COUNT(*) AS cnt FROM submission GROUP BY room_id) '
        'SELECT room_id, cnt FROM stats LIMIT 50'
    )

    assert 'FROM stats' in sql


def test_validate_and_prepare_sql_allows_recursive_cte_with_column_list():
    service = AiAnalyticsService()

    sql = service._validate_and_prepare_sql(
        "WITH RECURSIVE dates(day) AS ("
        "  SELECT date('now', '-2 months') "
        "  UNION ALL "
        "  SELECT date(day, '+1 day') FROM dates WHERE day < date('now')"
        "), new_users AS ("
        '  SELECT date(created_at) AS day, COUNT(*) AS new_users_count FROM "user" GROUP BY date(created_at)'
        ") "
        "SELECT dates.day, COALESCE(new_users.new_users_count, 0) "
        "FROM dates LEFT JOIN new_users ON new_users.day = dates.day "
        "LIMIT 200"
    )

    assert 'FROM dates' in sql
    assert 'JOIN new_users' in sql


def test_sqlite_dialect_guidance_mentions_sqlite_datetime_syntax():
    service = AiAnalyticsService()

    guidance = service._dialect_guidance('sqlite')

    assert "datetime('now')" in guidance
    assert "datetime('now', '-30 days')" in guidance


def test_postgresql_dialect_guidance_mentions_interval():
    service = AiAnalyticsService()

    guidance = service._dialect_guidance('postgresql')

    assert 'INTERVAL' in guidance
