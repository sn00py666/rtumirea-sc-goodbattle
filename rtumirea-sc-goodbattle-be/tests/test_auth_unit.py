from __future__ import annotations

import pytest
from jose import JWTError

import app.auth as auth


def test_hash_password_returns_hash():
    plain = 'qwerty123'
    hashed = auth.hash_password(plain)

    assert hashed != plain
    assert isinstance(hashed, str)
    assert len(hashed) > 20


def test_verify_password_true_for_matching_password():
    plain = 'secret-pass'
    hashed = auth.hash_password(plain)
    assert auth.verify_password(plain, hashed) is True


@pytest.mark.parametrize('wrong_password', ['secret', 'SECRET', 'secret-pass ', '123456'])
def test_verify_password_false_for_non_matching_password(wrong_password: str):
    hashed = auth.hash_password('secret-pass')
    assert auth.verify_password(wrong_password, hashed) is False


def test_create_and_decode_access_token_roundtrip(monkeypatch):
    monkeypatch.setattr(auth, 'SECRET_KEY', 'unit-test-secret')
    monkeypatch.setattr(auth, 'JWT_ALGORITHM', 'HS256')
    monkeypatch.setattr(auth, 'TOKEN_EXPIRATION_DAYS', 3)

    payload = {'user_id': 'u-1', 'role': 'participant'}
    token = auth.create_access_token(payload)
    decoded = auth.decode_access_token(token)

    assert decoded['user_id'] == 'u-1'
    assert decoded['role'] == 'participant'
    assert 'exp' in decoded


def test_create_access_token_mutates_payload_with_exp(monkeypatch):
    monkeypatch.setattr(auth, 'SECRET_KEY', 'unit-test-secret')
    monkeypatch.setattr(auth, 'JWT_ALGORITHM', 'HS256')
    monkeypatch.setattr(auth, 'TOKEN_EXPIRATION_DAYS', 1)

    payload = {'user_id': 'u-2'}
    auth.create_access_token(payload)

    assert 'exp' in payload


def test_decode_access_token_raises_for_invalid_token(monkeypatch):
    monkeypatch.setattr(auth, 'SECRET_KEY', 'unit-test-secret')
    monkeypatch.setattr(auth, 'JWT_ALGORITHM', 'HS256')

    with pytest.raises(JWTError):
        auth.decode_access_token('not-a-jwt-token')


def test_decode_access_token_raises_for_expired_token(monkeypatch):
    monkeypatch.setattr(auth, 'SECRET_KEY', 'unit-test-secret')
    monkeypatch.setattr(auth, 'JWT_ALGORITHM', 'HS256')
    monkeypatch.setattr(auth, 'TOKEN_EXPIRATION_DAYS', -1)

    token = auth.create_access_token({'user_id': 'u-expired'})
    with pytest.raises(JWTError):
        auth.decode_access_token(token)

