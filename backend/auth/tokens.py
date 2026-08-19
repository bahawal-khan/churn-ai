"""Password-reset token generation (`docs/BACKEND_SPEC.md` §4,
`docs/DATABASE_SPEC.md` §2.4). The raw token is returned to the caller
exactly once (to send to the user); only its hash is ever persisted.

SHA-256 (not Argon2) is used for the at-rest hash here: the raw token is
already a high-entropy random value (not a low-entropy user-chosen
password), so a slow password-hashing KDF buys no additional resistance to
guessing and would only slow down the lookup-by-hash the reset endpoint
does on every request.
"""

from __future__ import annotations

import hashlib
import secrets

TOKEN_BYTES = 32


def generate_reset_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_reset_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
