"""Authentication routes — register, login, current user."""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from auth import AuthError, register_user, authenticate_user, create_access_token
from deps import get_current_user

logger = logging.getLogger("coolkit.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register")
def register(req: RegisterRequest):
    try:
        user = register_user(req.email, req.password, req.name)
    except AuthError as e:
        return JSONResponse(status_code=e.status, content={"status": "error", "message": e.message})
    token = create_access_token(user["id"], user["email"])
    logger.info(f"New user registered: {user['email']} (id={user['id']})")
    return {"status": "ok", "token": token, "user": user}


@router.post("/login")
def login(req: LoginRequest):
    user = authenticate_user(req.email, req.password)
    if not user:
        return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid email or password"})
    token = create_access_token(user["id"], user["email"])
    return {"status": "ok", "token": token, "user": user}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {"status": "ok", "user": user}
