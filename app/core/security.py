"""Безопасность: стойкое хэширование паролей и JWT-токены.

Хэш пароля — scrypt (стандартная библиотека ``hashlib``, рекомендован OWASP):
* для каждого пароля генерируется случайная соль 16 байт;
* параметры n=2**14, r=8, p=1 делают перебор дорогим по памяти и CPU;
* результат хранится в одной строке ``scrypt$n$r$p$<salt_b64>$<hash_b64>``,
  поэтому параметры можно усилить позже, не ломая старые хэши;
* сравнение выполняется за постоянное время (``hmac.compare_digest``).

Модуль не зависит от FastAPI и слоёв приложения.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64
SALT_BYTES = 16
HASH_PREFIX = "scrypt"


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str) -> str:
    """Вернуть стойкий солёный хэш пароля. Каждый вызов даёт новую строку (новая соль)."""
    if not isinstance(password, str) or password == "":
        raise ValueError("Пароль должен быть непустой строкой")
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_DKLEN
    )
    return f"{HASH_PREFIX}${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64e(salt)}${_b64e(digest)}"


def verify_password(password: str, password_hash: str) -> bool:
    """Проверить пароль по хэшу. Любой повреждённый хэш даёт ``False``, а не исключение."""
    try:
        prefix, n, r, p, salt_b64, digest_b64 = password_hash.split("$")
        if prefix != HASH_PREFIX:
            return False
        expected = _b64d(digest_b64)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_b64d(salt_b64),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError, AttributeError):
        return False
    return hmac.compare_digest(actual, expected)


class TokenError(Exception):
    """Токен отсутствует, повреждён, подписан другим ключом или истёк."""


def create_access_token(
    *,
    user_id: int,
    role: str,
    secret_key: str,
    expires_minutes: int,
    algorithm: str = "HS256",
    now: datetime | None = None,
) -> str:
    """Выпустить JWT с полями ``sub`` (id пользователя), ``role``, ``iat`` и ``exp``."""
    issued_at = now or datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(minutes=expires_minutes)).timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_access_token(token: str, *, secret_key: str, algorithm: str = "HS256") -> dict[str, Any]:
    """Проверить подпись и срок действия токена и вернуть его содержимое."""
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
            options={"require": ["sub", "exp", "role"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Срок действия токена истёк") from exc
    except jwt.PyJWTError as exc:
        raise TokenError("Недействительный токен") from exc
    if payload.get("type") != "access":
        raise TokenError("Недействительный тип токена")
    try:
        payload["user_id"] = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise TokenError("Недействительный токен") from exc
    return payload
