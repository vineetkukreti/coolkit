"""FastAPI auth dependencies."""

from fastapi import Request, HTTPException

from auth import decode_token, get_user_by_id


def get_bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return None


def get_current_user(request: Request) -> dict:
    """Resolve the authenticated user from the Bearer token, or raise 401.

    The auth middleware already sets db.current_user_id for the request; this
    dependency is for routes that need the user object itself (e.g. /auth/me).
    """
    token = get_bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = get_user_by_id(payload.get("sub"))
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return user
