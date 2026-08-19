"""Password hashing (`docs/BACKEND_SPEC.md` §4: "Argon2 ... chosen over
bcrypt for stronger modern defaults and no 72-byte input truncation
footgun"). Plaintext passwords are never logged or persisted anywhere.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash

_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(password_hash: str, plain_password: str) -> bool:
    try:
        return _hasher.verify(password_hash, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False
