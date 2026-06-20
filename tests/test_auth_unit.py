import pytest
from jose import JWTError

from app.auth import create_access_token, decode_token


def test_token_roundtrip():
    token = create_access_token("user-abc")
    assert decode_token(token) == "user-abc"


def test_invalid_token_raises():
    with pytest.raises(JWTError):
        decode_token("not.a.token")
