from __future__ import annotations

import asyncio
import string

import pytest

import app.routes.rooms as rooms_module


@pytest.mark.parametrize('length', [1, 4, 8, 16, 32])
def test_generate_join_code_length_and_charset(length: int):
    code = rooms_module.generate_join_code(length=length)

    allowed = set(string.ascii_uppercase + string.digits)
    assert len(code) == length
    assert set(code).issubset(allowed)


def test_generate_join_code_default_length():
    code = rooms_module.generate_join_code()
    assert len(code) == 8


def test_generate_unique_join_code_retries_on_collision(monkeypatch):
    class FakeResult:
        def __init__(self, value):
            self._value = value

        def first(self):
            return self._value

    class FakeSession:
        def __init__(self):
            self.call_count = 0

        async def exec(self, _query):  # noqa: ARG002
            self.call_count += 1
            if self.call_count == 1:
                return FakeResult(object())
            return FakeResult(None)

    sequence = iter(['AAAA1111', 'BBBB2222'])
    monkeypatch.setattr(rooms_module, 'generate_join_code', lambda: next(sequence))

    session = FakeSession()
    code = asyncio.run(rooms_module.generate_unique_join_code(session))

    assert code == 'BBBB2222'
    assert session.call_count == 2

