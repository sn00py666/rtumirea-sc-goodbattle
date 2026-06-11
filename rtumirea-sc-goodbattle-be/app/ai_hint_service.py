from __future__ import annotations

import os
import logging
import re
from dataclasses import dataclass
from collections.abc import Iterator
from typing import Any, Dict, List, Protocol
from urllib.parse import urlparse

from openai import OpenAI

logger = logging.getLogger(__name__)
LOG_TEXT_LIMIT = 12000

MAX_CODE_CHARS = 8000
MAX_LOG_CHARS = 3500
MAX_TASK_DESC_CHARS = 3500
MAX_AI_QUESTION_CHARS = 100


class AiHintService:
    def __init__(self) -> None:
        self._client: OpenAI | None = None
        self._model = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini').strip() or 'gpt-4.1-mini'
        self._client_factory = LlmClientFactory()
        self._strategy_selector = ContextStrategySelector()
        self._request_validator = self._build_request_validation_chain()
        self._response_filter = self._build_response_filter_chain()

    def _get_client(self) -> OpenAI:
        if self._client is not None:
            return self._client

        self._client = self._client_factory.create(model=self._model)
        return self._client

    @staticmethod
    def _build_request_validation_chain() -> 'RequestValidationHandler':
        question_required = QuestionRequiredValidationHandler()
        question_length = QuestionLengthValidationHandler()
        usage_limit = HintUsageLimitValidationHandler()
        code_required = CodePresenceValidationHandler()
        question_required.set_next(question_length).set_next(usage_limit).set_next(code_required)
        return question_required

    @staticmethod
    def _build_response_filter_chain() -> 'ResponseFilterHandler':
        anti_solution = AntiFullSolutionFilterHandler()
        phrase_filter = ForbiddenPhraseFilterHandler()
        length_filter = ResponseLengthFilterHandler(max_words=120)
        anti_solution.set_next(phrase_filter).set_next(length_filter)
        return anti_solution

    @staticmethod
    def _trim(value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        suffix = '\n... [truncated]'
        return value[: max(0, limit - len(suffix))] + suffix

    @staticmethod
    def _log_text(value: str) -> str:
        if len(value) <= LOG_TEXT_LIMIT:
            return value
        return value[:LOG_TEXT_LIMIT] + '\n... [log truncated]'

    @staticmethod
    def _format_run_results(run_results: List[Dict[str, Any]]) -> str:
        chunks: List[str] = []
        for index, item in enumerate(run_results, start=1):
            public_view = item.get('public_view', {})
            log = public_view.get('log', {})
            chunks.append(
                '\n'.join(
                    [
                        f'Test #{index}',
                        f"passed: {public_view.get('passed')}",
                        f"error: {public_view.get('error')}",
                        f"input: {public_view.get('input')}",
                        f"expected: {public_view.get('expected')}",
                        f"actual: {public_view.get('actual')}",
                        f"stdout: {log.get('stdout', '')}",
                        f"stderr: {log.get('stderr', '')}",
                        f"exit_code: {log.get('exit_code')}",
                        f"timed_out: {log.get('timed_out')}",
                    ]
                )
            )
        return '\n\n'.join(chunks)

    @staticmethod
    def _build_system_prompt(role: str, battle_phase: str) -> str:
        role_note = 'User role: organizer.' if role == 'organizer' else 'User role: participant.'
        phase_note = f'Battle phase: {battle_phase}.'
        return (
            'You are an algorithmic contest mentor. '
            f'{role_note} {phase_note} '
            'Give only a short conceptual hint, not full solution code. '
            'Never provide complete working implementation, full pseudocode, or exact final algorithm steps. '
            'Focus on mistakes in current code and on the next step to try. '
            'Respond in Russian. Keep it under 120 words and at most one tiny code snippet of up to 3 lines if absolutely needed. '
            'Do not ask follow-up questions, do not offer additional help, and do not add phrases like "если хочешь" or "могу еще". '
            'Finish the response right after the hint.'
        )

    def validate_hint_request(self, *, user_question: str, code: str, has_used_hint: bool) -> None:
        self._request_validator.handle(
            HintRequestContext(user_question=user_question, code=code, has_used_hint=has_used_hint)
        )

    def _post_process_hint(self, text: str) -> str:
        return self._response_filter.handle(text).strip()

    def build_hint(
        self,
        *,
        task_title: str,
        task_description: str,
        task_examples: List[Dict[str, str]],
        language: str,
        code: str,
        user_question: str,
        run_results: List[Dict[str, Any]],
        role: str = 'participant',
        battle_phase: str = 'running',
    ) -> str:
        self.validate_hint_request(user_question=user_question, code=code, has_used_hint=False)

        rendered_examples = '\n'.join(
            f"Example {idx + 1}:\ninput:\n{example.get('input', '')}\noutput:\n{example.get('output', '')}"
            for idx, example in enumerate(task_examples[:5])
        )
        rendered_results = self._format_run_results(run_results)

        system_prompt = self._build_system_prompt(role=role, battle_phase=battle_phase)

        strategy = self._strategy_selector.pick()
        user_prompt = strategy.build_user_prompt(
            task_title=task_title,
            task_description=self._trim(task_description, MAX_TASK_DESC_CHARS),
            rendered_examples=rendered_examples,
            language=language,
            code=self._trim(code, MAX_CODE_CHARS),
            rendered_results=self._trim(rendered_results, MAX_LOG_CHARS),
            user_question=user_question,
        )

        logger.info(
            'OpenAI request (non-stream): model=%s system_prompt=%s user_prompt=%s',
            self._model,
            self._log_text(system_prompt),
            self._log_text(user_prompt),
        )
        response = self._get_client().responses.create(
            model=self._model,
            input=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            max_output_tokens=220,
        )
        logger.info('AI hint generated (non-stream), chars=%s', len(response.output_text or ''))
        logger.info('OpenAI response (non-stream): %s', self._log_text(response.output_text or ''))

        return self._post_process_hint(response.output_text or '')

    def stream_hint(
        self,
        *,
        task_title: str,
        task_description: str,
        task_examples: List[Dict[str, str]],
        language: str,
        code: str,
        user_question: str,
        run_results: List[Dict[str, Any]],
        role: str = 'participant',
        battle_phase: str = 'running',
    ) -> Iterator[str]:
        self.validate_hint_request(user_question=user_question, code=code, has_used_hint=False)

        rendered_examples = '\n'.join(
            f"Example {idx + 1}:\ninput:\n{example.get('input', '')}\noutput:\n{example.get('output', '')}"
            for idx, example in enumerate(task_examples[:5])
        )
        rendered_results = self._format_run_results(run_results)

        system_prompt = self._build_system_prompt(role=role, battle_phase=battle_phase)
        strategy = self._strategy_selector.pick()
        user_prompt = strategy.build_user_prompt(
            task_title=task_title,
            task_description=self._trim(task_description, MAX_TASK_DESC_CHARS),
            rendered_examples=rendered_examples,
            language=language,
            code=self._trim(code, MAX_CODE_CHARS),
            rendered_results=self._trim(rendered_results, MAX_LOG_CHARS),
            user_question=user_question,
        )

        with self._get_client().responses.stream(
            model=self._model,
            input=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            max_output_tokens=220,
        ) as stream:
            logger.info(
                'OpenAI request (stream): model=%s system_prompt=%s user_prompt=%s',
                self._model,
                self._log_text(system_prompt),
                self._log_text(user_prompt),
            )
            logger.info('AI hint stream started')
            chunk_count = 0
            full_text = ''
            for event in stream:
                if event.type == 'response.output_text.delta':
                    chunk_count += 1
                    delta = event.delta or ''
                    full_text += delta
            logger.info('AI hint stream finished, chunks=%s', chunk_count)
            filtered_text = self._post_process_hint(full_text)
            logger.info('OpenAI response (stream): %s', self._log_text(filtered_text))
            yield filtered_text


class LlmClientFactory:
    def create(self, *, model: str) -> OpenAI:
        provider = os.getenv('LLM_PROVIDER', 'openai').strip().lower()
        api_key = os.getenv('OPENAI_API_KEY', '').strip()
        if not api_key:
            raise ValueError('OPENAI_API_KEY is not configured')

        base_url = self._resolve_base_url(provider=provider)
        if provider in {'openai', 'openai_compatible', 'nekocode'}:
            logger.info('AI client init: provider=%s model=%s base_url=%s', provider, model, base_url or '<default>')
            return OpenAI(api_key=api_key, base_url=base_url)

        raise ValueError(f'Unsupported LLM provider: {provider}')

    def _resolve_base_url(self, *, provider: str) -> str | None:
        configured_base_url = os.getenv('OPENAI_BASE_URL', '').strip()
        if configured_base_url:
            return self._normalize_base_url(configured_base_url)

        if provider == 'nekocode':
            channel = os.getenv('NEKOCODE_CHANNEL', '').strip() or 'alpha'
            return f'https://gateway.nekocode.app/{channel}/v1'

        return None

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        normalized = base_url.strip()
        if not normalized:
            raise ValueError('OPENAI_BASE_URL is empty')

        if not re.match(r'^https?://', normalized, flags=re.IGNORECASE):
            normalized = f'https://{normalized}'

        parsed = urlparse(normalized)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(
                'OPENAI_BASE_URL has invalid format. Expected full URL like '
                'https://gateway.nekocode.app/alpha/v1'
            )

        return normalized.rstrip('/')


class HintContextStrategy(Protocol):
    def build_user_prompt(
        self,
        *,
        task_title: str,
        task_description: str,
        rendered_examples: str,
        language: str,
        code: str,
        rendered_results: str,
        user_question: str,
    ) -> str: ...


class DefaultHintContextStrategy:
    def build_user_prompt(
        self,
        *,
        task_title: str,
        task_description: str,
        rendered_examples: str,
        language: str,
        code: str,
        rendered_results: str,
        user_question: str,
    ) -> str:
        return '\n\n'.join(
            [
                f'Task: {task_title}',
                f'Description:\n{task_description}',
                f'Examples:\n{rendered_examples}',
                f'Language: {language}',
                f'Current code:\n{code}',
                f'Run logs and checks:\n{rendered_results}',
                f'Question from user:\n{user_question}',
            ]
        )

class ContextStrategySelector:
    def __init__(self) -> None:
        self._default = DefaultHintContextStrategy()

    def pick(self) -> HintContextStrategy:
        return self._default


@dataclass(slots=True)
class HintRequestContext:
    user_question: str
    code: str
    has_used_hint: bool


class RequestValidationHandler:
    def __init__(self) -> None:
        self._next: RequestValidationHandler | None = None

    def set_next(self, next_handler: 'RequestValidationHandler') -> 'RequestValidationHandler':
        self._next = next_handler
        return next_handler

    def handle(self, context: HintRequestContext) -> None:
        self._handle(context)
        if self._next is not None:
            self._next.handle(context)

    def _handle(self, context: HintRequestContext) -> None:
        raise NotImplementedError


class QuestionRequiredValidationHandler(RequestValidationHandler):
    def _handle(self, context: HintRequestContext) -> None:
        if not context.user_question.strip():
            raise ValueError('Question is required')


class QuestionLengthValidationHandler(RequestValidationHandler):
    def _handle(self, context: HintRequestContext) -> None:
        if len(context.user_question) > MAX_AI_QUESTION_CHARS:
            raise ValueError(f'Question is too long (max {MAX_AI_QUESTION_CHARS} chars)')


class HintUsageLimitValidationHandler(RequestValidationHandler):
    def _handle(self, context: HintRequestContext) -> None:
        if context.has_used_hint:
            raise ValueError('Подсказка для этой задачи уже использована')


class CodePresenceValidationHandler(RequestValidationHandler):
    def _handle(self, context: HintRequestContext) -> None:
        if not context.code.strip():
            raise ValueError('Сначала нужно написать код для подсказки')


class ResponseFilterHandler:
    def __init__(self) -> None:
        self._next: ResponseFilterHandler | None = None

    def set_next(self, next_handler: 'ResponseFilterHandler') -> 'ResponseFilterHandler':
        self._next = next_handler
        return next_handler

    def handle(self, text: str) -> str:
        next_text = self._handle(text)
        if self._next is not None:
            return self._next.handle(next_text)
        return next_text

    def _handle(self, text: str) -> str:
        raise NotImplementedError


class AntiFullSolutionFilterHandler(ResponseFilterHandler):
    def _handle(self, text: str) -> str:
        cleaned = re.sub(r'```[\s\S]*?```', '[code removed by policy]', text)
        lines = [line for line in cleaned.splitlines() if not line.strip().startswith(('def ', 'class ', 'function '))]
        return '\n'.join(lines)


class ForbiddenPhraseFilterHandler(ResponseFilterHandler):
    def _handle(self, text: str) -> str:
        return text.replace('если хочешь', '').replace('могу еще', '').strip()


class ResponseLengthFilterHandler(ResponseFilterHandler):
    def __init__(self, *, max_words: int) -> None:
        super().__init__()
        self._max_words = max_words

    def _handle(self, text: str) -> str:
        words = text.split()
        if len(words) <= self._max_words:
            return text
        return ' '.join(words[: self._max_words])


ai_hint_service = AiHintService()
