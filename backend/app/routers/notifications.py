"""通知：最近 50 条列表 + 全部已读。通知统一由 deps.notify 落库并推送。"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import get_current_user
from ..models import Notification, User
from ..schemas import NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def list_notifications(user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )).scalars().all()
    return rows


@router.post("/read_all")
async def read_all(user: User = Depends(get_current_user),
                   db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await db.commit()
    return {"ok": True}
