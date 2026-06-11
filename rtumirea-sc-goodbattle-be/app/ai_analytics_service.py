from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable
from uuid import UUID

from openai import OpenAI
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.ai_hint_service import LlmClientFactory

logger = logging.getLogger(__name__)

MAX_QUESTION_CHARS = 700
MAX_SQL_CHARS = 6000
MAX_RESULT_ROWS = 200
MAX_REPORT_ROWS_FOR_LLM = 80
MAX_SQL_GENERATION_TOKENS = 420
MAX_SQL_REPAIR_TOKENS = 360
MAX_REPORT_TOKENS = 720

ALLOWED_TABLES = {
    'aihintevent',
    'battleevent',
    'language',
    'room',
    'roomlanguagelink',
    'roommember',
    'roomtasklink',
    'submission',
    'submissiontestresult',
    'task',
    'taskexample',
    'user',
}
BLOCKED_COLUMNS = {
    'password_hash',
    'source_code',
}
FORBIDDEN_SQL_KEYWORDS = (
    'insert',
    'update',
    'delete',
    'drop',
    'alter',
    'truncate',
    'create',
    'grant',
    'revoke',
    'merge',
    'vacuum',
    'analyze',
    'copy',
    'call',
)


@dataclass(slots=True)
class SqlPlan:
    explanation: str
    sql: str


@dataclass(slots=True)
class SqlExecutionResult:
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool


class AiAnalyticsService:
    def __init__(self) -> None:
        self._client: OpenAI | None = None
        self._model = os.getenv('OPENAI_ANALYTICS_MODEL', '').strip() or os.getenv('OPENAI_MODEL', 'gpt-4.1-mini').strip() or 'gpt-4.1-mini'
        self._client_factory = LlmClientFactory()

    def _get_client(self) -> OpenAI:
        if self._client is not None:
            return self._client
        self._client = self._client_factory.create(model=self._model)
        return self._client

    async def run_analytics_query(self, *, session: AsyncSession, question: str) -> dict[str, Any]:
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError('Вопрос не может быть пустым')
        if len(normalized_question) > MAX_QUESTION_CHARS:
            raise ValueError(f'Вопрос слишком длинный. Максимум {MAX_QUESTION_CHARS} символов.')

        dialect_name = self._get_dialect_name(session)
        schema_context = await self._build_schema_context(session)
        plan = self._build_sql_plan(
            question=normalized_question,
            schema_context=schema_context,
            dialect_name=dialect_name,
        )
        sql = self._validate_and_prepare_sql(plan.sql)
        try:
            execution = await self._execute_sql(session=session, sql=sql)
        except OperationalError as exc:
            logger.warning('Initial AI analytics SQL failed, attempting repair: %s', exc)
            sql = self._repair_sql_after_error(
                question=normalized_question,
                schema_context=schema_context,
                dialect_name=dialect_name,
                failed_sql=sql,
                error_message=str(exc),
            )
            execution = await self._execute_sql(session=session, sql=sql)
        report_markdown = self._build_report_markdown(question=normalized_question, sql=sql, execution=execution)

        return {
            'question': normalized_question,
            'sql': sql,
            'sql_explanation': plan.explanation,
            'report_markdown': report_markdown,
            'columns': execution.columns,
            'rows': execution.rows,
            'row_count': execution.row_count,
            'truncated': execution.truncated,
            'model': self._model,
            'generated_at': datetime.now(),
        }

    @staticmethod
    def _get_dialect_name(session: AsyncSession) -> str:
        if session.bind is None:
            return 'unknown'
        return session.bind.dialect.name

    async def _build_schema_context(self, session: AsyncSession) -> str:
        connection = await session.connection()

        def _inspect_schema(sync_connection) -> str:
            inspector = inspect(sync_connection)
            lines: list[str] = []
            for table_name in sorted(inspector.get_table_names()):
                normalized_table = table_name.lower()
                if normalized_table not in ALLOWED_TABLES:
                    continue
                columns = inspector.get_columns(table_name)
                rendered_columns = []
                for column in columns:
                    column_name = str(column['name'])
                    if column_name.lower() in BLOCKED_COLUMNS:
                        continue
                    rendered_columns.append(f"{column_name}:{column.get('type')}")
                lines.append(f"- {table_name}({', '.join(rendered_columns)})")
            return '\n'.join(lines)

        schema_context = await connection.run_sync(_inspect_schema)
        if not schema_context.strip():
            raise RuntimeError('Не удалось получить схему БД для AI-аналитики')
        return schema_context

    def _build_sql_plan(self, *, question: str, schema_context: str, dialect_name: str) -> SqlPlan:
        system_prompt = (
            'Ты SQL-аналитик GoodBattle. '
            'Сгенерируй ОДИН read-only SQL запрос для ответа на вопрос пользователя. '
            'Разрешены только SELECT/CTE (WITH ... SELECT). '
            'Запрещены любые изменения данных и доступ к чувствительным полям.'
        )
        user_prompt = '\n\n'.join(
            [
                'Схема БД (доступные таблицы и поля):',
                schema_context,
                f'Диалект БД: {dialect_name}.',
                self._dialect_guidance(dialect_name),
                'Ограничения:',
                f'1) Только таблицы из списка выше.',
                f"2) Запрещенные поля: {', '.join(sorted(BLOCKED_COLUMNS))}.",
                f'3) Обязательно добавь LIMIT не больше {MAX_RESULT_ROWS}.',
                '4) Никаких DDL/DML, только read-only SELECT.',
                '5) Ответ строго в формате:',
                'EXPLANATION: <короткое объяснение>',
                'SQL:',
                '```sql',
                '<запрос>',
                '```',
                f'Вопрос пользователя: {question}',
            ]
        )
        response = self._get_client().responses.create(
            model=self._model,
            input=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            max_output_tokens=MAX_SQL_GENERATION_TOKENS,
        )
        text_output = (response.output_text or '').strip()
        logger.info('AI analytics SQL plan raw output: %s', text_output)
        return self._parse_sql_plan(text_output)

    def _repair_sql_after_error(
        self,
        *,
        question: str,
        schema_context: str,
        dialect_name: str,
        failed_sql: str,
        error_message: str,
    ) -> str:
        system_prompt = (
            'Ты SQL-аналитик GoodBattle. '
            'Исправь SQL-запрос после ошибки выполнения. '
            'Верни только исправленный read-only SQL в блоке ```sql```.'
        )
        user_prompt = '\n\n'.join(
            [
                f'Диалект БД: {dialect_name}.',
                self._dialect_guidance(dialect_name),
                'Схема БД:',
                schema_context,
                f'Вопрос пользователя: {question}',
                'Упавший SQL:',
                f'```sql\n{failed_sql}\n```',
                f'Текст ошибки БД: {error_message}',
                f'Сохрани смысл запроса, используй только синтаксис {dialect_name}.',
                f'Обязательно добавь LIMIT не больше {MAX_RESULT_ROWS}.',
            ]
        )
        response = self._get_client().responses.create(
            model=self._model,
            input=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            max_output_tokens=MAX_SQL_REPAIR_TOKENS,
        )
        repaired_plan = self._parse_sql_plan((response.output_text or '').strip())
        repaired_sql = self._validate_and_prepare_sql(repaired_plan.sql)
        logger.info('AI analytics SQL repaired after execution error: %s', repaired_sql)
        return repaired_sql

    @staticmethod
    def _dialect_guidance(dialect_name: str) -> str:
        if dialect_name == 'sqlite':
            return (
                'Для SQLite используй синтаксис SQLite. '
                "Не используй NOW(), INTERVAL, ILIKE, DATE_TRUNC, EXTRACT. "
                "Для текущего времени используй datetime('now'). "
                "Для сдвига дат используй datetime('now', '-30 days'). "
                "Для дат используй date(...) или datetime(...)."
            )
        if dialect_name == 'postgresql':
            return (
                'Для PostgreSQL используй синтаксис PostgreSQL. '
                'Разрешены NOW(), CURRENT_DATE, INTERVAL, DATE_TRUNC.'
            )
        return 'Используй синтаксис, совместимый с указанным диалектом БД.'

    def _parse_sql_plan(self, text_output: str) -> SqlPlan:
        sql_block_match = re.search(r'```sql\s*(.*?)```', text_output, flags=re.IGNORECASE | re.DOTALL)
        if sql_block_match:
            sql = sql_block_match.group(1).strip()
        else:
            fallback_match = re.search(r'((with|select)\s+[\s\S]+)', text_output, flags=re.IGNORECASE)
            if fallback_match is None:
                raise ValueError('AI не вернул SQL-запрос в ожидаемом формате')
            sql = fallback_match.group(1).strip()

        explanation_match = re.search(r'EXPLANATION:\s*(.+)', text_output, flags=re.IGNORECASE)
        explanation = explanation_match.group(1).strip() if explanation_match else 'Сформирован SQL-отчет по вопросу.'
        return SqlPlan(sql=sql, explanation=explanation)

    def _validate_and_prepare_sql(self, sql: str) -> str:
        normalized = sql.strip()
        if len(normalized) > MAX_SQL_CHARS:
            raise ValueError('SQL-запрос получился слишком большим')

        if ';' in normalized[:-1]:
            raise ValueError('Разрешен только один SQL-запрос')
        if normalized.endswith(';'):
            normalized = normalized[:-1].strip()

        lowered = normalized.lower()
        if not (lowered.startswith('select') or lowered.startswith('with')):
            raise ValueError('Разрешены только SELECT/CTE запросы')

        for keyword in FORBIDDEN_SQL_KEYWORDS:
            if re.search(rf'\b{re.escape(keyword)}\b', lowered):
                raise ValueError(f'Запрещенная конструкция в SQL: {keyword}')

        for column_name in BLOCKED_COLUMNS:
            if re.search(rf'\b{re.escape(column_name)}\b', lowered):
                raise ValueError(f'Запрещенный столбец в SQL: {column_name}')

        referenced_tables = self._extract_referenced_tables(lowered)
        cte_names = self._extract_cte_names(lowered)
        disallowed_tables = sorted(
            table
            for table in referenced_tables
            if table not in ALLOWED_TABLES and table not in cte_names
        )
        if disallowed_tables:
            raise ValueError(f'Запрещенные таблицы в SQL: {", ".join(disallowed_tables)}')

        normalized_with_limit = self._ensure_limit(normalized)
        return normalized_with_limit

    @staticmethod
    def _extract_referenced_tables(sql: str) -> set[str]:
        tables: set[str] = set()
        for match in re.finditer(r'\b(?:from|join)\s+([a-zA-Z0-9_."`]+)', sql, flags=re.IGNORECASE):
            token = match.group(1).strip().strip('"`')
            if token.startswith('('):
                continue
            table_name = token.split('.')[-1].strip('"`').lower()
            if table_name:
                tables.add(table_name)
        return tables

    @staticmethod
    def _extract_cte_names(sql: str) -> set[str]:
        cte_names: set[str] = set()
        for match in re.finditer(
            r'(?:\bwith\b(?:\s+recursive)?|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\([^)]*\))?\s+as\s*\(',
            sql,
            flags=re.IGNORECASE,
        ):
            cte_names.add(match.group(1).lower())
        return cte_names

    @staticmethod
    def _ensure_limit(sql: str) -> str:
        match = re.search(r'\blimit\s+(\d+)\b', sql, flags=re.IGNORECASE)
        if match is None:
            return f'{sql}\nLIMIT {MAX_RESULT_ROWS}'
        limit_value = int(match.group(1))
        if limit_value <= MAX_RESULT_ROWS:
            return sql
        return re.sub(
            r'\blimit\s+\d+\b',
            f'LIMIT {MAX_RESULT_ROWS}',
            sql,
            count=1,
            flags=re.IGNORECASE,
        )

    async def _execute_sql(self, *, session: AsyncSession, sql: str) -> SqlExecutionResult:
        dialect_name = session.bind.dialect.name if session.bind is not None else ''
        if dialect_name == 'postgresql':
            try:
                await session.exec(text('SET LOCAL TRANSACTION READ ONLY'))
            except Exception:
                logger.warning('Failed to enable read-only transaction mode for AI analytics', exc_info=True)

        result = await session.exec(text(sql))
        rows = result.mappings().all()

        serialized_rows = [self._serialize_row(dict(row)) for row in rows]
        columns = list(result.keys())
        row_count = len(serialized_rows)
        truncated = row_count >= MAX_RESULT_ROWS
        return SqlExecutionResult(columns=columns, rows=serialized_rows, row_count=row_count, truncated=truncated)

    def _build_report_markdown(self, *, question: str, sql: str, execution: SqlExecutionResult) -> str:
        if execution.row_count == 0:
            return 'По запросу не найдено данных. Уточните период, роль или критерии выборки.'

        rows_for_llm = execution.rows[:MAX_REPORT_ROWS_FOR_LLM]
        system_prompt = (
            'Ты аналитик платформы GoodBattle. '
            'Сформируй понятный аналитический отчет в Markdown на русском языке. '
            'Пиши кратко и по делу: выводы, наблюдения, возможные причины, метрики.'
        )
        user_prompt = '\n\n'.join(
            [
                f'Вопрос: {question}',
                f'SQL: {sql}',
                f'Колонки: {", ".join(execution.columns)}',
                f'Количество строк: {execution.row_count}',
                f'Данные (JSON, первые {len(rows_for_llm)} строк):',
                json.dumps(rows_for_llm, ensure_ascii=False),
                'Сформируй отчет с разделами: "Краткий вывод", "Ключевые наблюдения", "Что делать дальше".',
            ]
        )
        try:
            response = self._get_client().responses.create(
                model=self._model,
                input=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                max_output_tokens=MAX_REPORT_TOKENS,
            )
            report = (response.output_text or '').strip()
            if report:
                return report
        except Exception:
            logger.exception('AI report generation failed, falling back to deterministic summary')

        return self._fallback_report_markdown(execution=execution)

    def _fallback_report_markdown(self, *, execution: SqlExecutionResult) -> str:
        preview_lines = self._rows_preview(execution.rows[:10], execution.columns)
        return '\n'.join(
            [
                '### Краткий вывод',
                f'Получено строк: **{execution.row_count}**.',
                '',
                '### Предпросмотр данных',
                preview_lines,
            ]
        )

    @staticmethod
    def _rows_preview(rows: list[dict[str, Any]], columns: list[str]) -> str:
        if not rows:
            return 'Нет данных.'
        header = '| ' + ' | '.join(columns) + ' |'
        separator = '| ' + ' | '.join(['---'] * len(columns)) + ' |'
        body = []
        for row in rows:
            values = [str(row.get(column, '')) for column in columns]
            body.append('| ' + ' | '.join(values) + ' |')
        return '\n'.join([header, separator, *body])

    def _serialize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {key: self._serialize_value(value) for key, value in row.items()}

    def _serialize_value(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, (datetime, date, time)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        if isinstance(value, dict):
            return {str(key): self._serialize_value(item) for key, item in value.items()}
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
            return [self._serialize_value(item) for item in value]
        return str(value)


ai_analytics_service = AiAnalyticsService()
