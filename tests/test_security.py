"""Модульные тесты core/security: хэширование и JWT."""

from __future__ import annotations

import pytest

from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_has_parameters_salt_and_digest():
    h = hash_password("Secret123!")
    prefix, n, r, p, salt, digest = h.split("$")
    assert prefix == "scrypt" and int(n) >= 2**14 and int(r) == 8 and int(p) == 1
    assert salt and digest


def test_verify_password_true_and_false():
    h = hash_password("Secret123!")
    assert verify_password("Secret123!", h)
    assert not verify_password("secret123!", h)
    assert not verify_password("", h)


@pytest.mark.parametrize("broken", ["", "plain", "bcrypt$1$2$3$4$5", "scrypt$x$8$1$aa$bb", "scrypt$16384$8$1"])
def test_verify_password_with_broken_hash_returns_false(broken):
    assert verify_password("Secret123!", broken) is False


def test_hash_password_rejects_empty():
    with pytest.raises(ValueError):
        hash_password("")


def test_token_roundtrip():
    token = create_access_token(user_id=7, role="admin", secret_key="k" * 40, expires_minutes=1)
    payload = decode_access_token(token, secret_key="k" * 40)
    assert payload["user_id"] == 7 and payload["role"] == "admin"


def test_token_with_wrong_key_is_rejected():
    token = create_access_token(user_id=7, role="admin", secret_key="k" * 40, expires_minutes=1)
    with pytest.raises(TokenError):
        decode_access_token(token, secret_key="z" * 40)
