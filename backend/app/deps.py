"""统一依赖注入：当前登录用户、管理员、通知落库+推送。"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .models import Notification, User
from .redis_client import get_redis_client
from .security import decode_token
from .ws import manager

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录")
    payload = decode_token(cred.credentials)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "登录已过期，请重新登录")
    user = await db.get(User, payload["user_id"])
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "账号不存在")
    return user


async def get_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")
    return user


async def notify(db: AsyncSession, user_id: int, ntype: str, title: str, body: str = "") -> None:
    """通知先落库（离线也能看到），再经 WebSocket 实时推给在线连接。"""
    note = Notification(user_id=user_id, type=ntype, title=title, body=body)
    db.add(note)
    await manager.send_to(user_id, {"type": ntype, "title": title, "body": body})
