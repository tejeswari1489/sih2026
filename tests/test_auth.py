import pytest
from backend.services.auth_service import hash_password, verify_password, create_access_token, decode_token

def test_password_hashing():
    raw = "doctorSecret123"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("wrongPassword", hashed) is False

def test_jwt_token_generation_and_decode():
    data = {"sub": "staff-123", "role": "doctor", "username": "dr.sharma"}
    token = create_access_token(data)
    assert isinstance(token, str)
    assert len(token) > 20

    decoded = decode_token(token)
    assert decoded["sub"] == "staff-123"
    assert decoded["role"] == "doctor"
    assert decoded["username"] == "dr.sharma"
    assert "exp" in decoded
