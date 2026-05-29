from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict

import bcrypt
from jose import jwt

SECRET_KEY = os.getenv('SECRET_KEY')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM')
TOKEN_EXPIRATION_DAYS = int(os.getenv('TOKEN_EXPIRATION_DAYS'))


def hash_password(plain_password: str) -> str:
    hashed = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        password_hash.encode('utf-8')
    )


def create_access_token(token_payload: Dict[str, Any]) -> str:
    token_payload['exp'] = datetime.now() + timedelta(days=TOKEN_EXPIRATION_DAYS)
    return jwt.encode(token_payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(access_token: str) -> Dict[str, Any]:
    decoded_payload = jwt.decode(access_token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    return decoded_payload
