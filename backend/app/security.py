"""Password hashing helpers.

We use werkzeug's wrappers around scrypt because it's already a hard
dependency (Flask depends on werkzeug) and scrypt is a sensible default
for password storage. The method string is set explicitly so an upgrade
of werkzeug doesn't silently switch us to a weaker algorithm.
"""
from werkzeug.security import check_password_hash, generate_password_hash


# scrypt parameters: N=32768 (work factor), r=8 (block size), p=1 (parallel).
# These are werkzeug's current defaults for "scrypt" but pinning them
# explicitly protects against future changes weakening our hashes.
_HASH_METHOD = "scrypt:32768:8:1"
_SALT_LENGTH = 16


def hash_password(password: str) -> str:
    return generate_password_hash(
        str(password),
        method=_HASH_METHOD,
        salt_length=_SALT_LENGTH,
    )


def verify_password(password: str, hashed: str) -> bool:
    # check_password_hash internally uses hmac.compare_digest for the
    # digest comparison, so this is already constant-time per-bytes.
    if not hashed:
        return False
    return check_password_hash(hashed, str(password))
