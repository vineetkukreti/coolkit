"""Authentication core — password hashing, JWT tokens, user registration/login.

Pure logic, no FastAPI. Uses the shared auth DB (db.init_auth_db) for the users
table; never touches per-user data DBs.
"""

import os
import re
import sqlite3
import logging
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from db import init_auth_db

logger = logging.getLogger("careerkit.auth")

# ─── Config ──────────────────────────────────────────────────────────────────

_JWT_SECRET = os.getenv("JWT_SECRET")
if not _JWT_SECRET:
    _JWT_SECRET = "dev-insecure-secret-change-me-0123456789abcdef"
    logger.warning("JWT_SECRET not set — using an insecure dev secret. Set JWT_SECRET in config/.env for production.")

_JWT_ALGO = "HS256"
_TOKEN_TTL_DAYS = 7

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthError(Exception):
    """Raised for auth failures. `status` maps to an HTTP status code."""
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


# ─── Passwords ───────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ─── Tokens ──────────────────────────────────────────────────────────────────

def create_access_token(user_id: int, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + timedelta(days=_TOKEN_TTL_DAYS),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGO)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGO])
    except jwt.PyJWTError:
        return None


# ─── User store (shared auth DB) ─────────────────────────────────────────────

def _public_user(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "email": row["email"], "name": row["name"], "created_at": row["created_at"]}


def register_user(email: str, password: str, name: str = "") -> dict:
    """Create a user. Returns the public user dict. Raises AuthError on bad input
    or duplicate email."""
    email = (email or "").strip().lower()
    if not _EMAIL_RE.match(email):
        raise AuthError("Invalid email address", status=400)
    if not password or len(password) < 6:
        raise AuthError("Password must be at least 6 characters", status=400)

    conn = init_auth_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
            (email, hash_password(password), (name or "").strip()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _public_user(row)
    except sqlite3.IntegrityError:
        raise AuthError("An account with this email already exists", status=409)
    finally:
        conn.close()


def authenticate_user(email: str, password: str) -> dict | None:
    """Return the public user dict if credentials are valid, else None."""
    email = (email or "").strip().lower()
    conn = init_auth_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row and verify_password(password, row["password_hash"]):
            return _public_user(row)
        return None
    finally:
        conn.close()


def get_user_by_id(user_id) -> dict | None:
    conn = init_auth_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _public_user(row) if row else None
    finally:
        conn.close()
