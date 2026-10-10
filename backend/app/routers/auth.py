"""认证：注册 / 登录 / 当前用户。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    taken = (await db.execute(
        select(User).where((User.username == body.username) | (User.email == body.email))
    )).scalar_one_or_none()
    if taken:
        raise HTTPException(status.HTTP_409_CONFLICT, "用户名或邮箱已被注册")
    user = User(username=body.username, email=body.email,
                password_hash=hash_password(body.password))
    db.add(user)
    await db.commit()
    return TokenOut(token=create_access_token(user.id, user.role.value),
                    user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(
        select(User).where(User.username == body.username)
    )).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")
    return TokenOut(token=create_access_token(user.id, user.role.value),
                    user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
