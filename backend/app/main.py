"""FastAPI 入口：装配路由、CORS、静态目录、生命周期（建表+种子+库存对账）、WebSocket。"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .config import get_settings
from .db import Session, init_db
from .models import Product
from .redis_client import close_redis, get_redis_client, sync_all_stock
from .routers import admin, auth, notifications, orders, products
from .ws import manager, ws_authenticate


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    os.makedirs(settings.upload_dir, exist_ok=True)
    await init_db()
    if settings.seed_on_start:
        from .seed import seed
        await seed()
    # 启动对账：以数据库库存为准重写 Redis 闸口，消除重启/漂移造成的不一致
    async with Session() as db:
        all_products = (await db.execute(select(Product))).scalars().all()
        await sync_all_stock(get_redis_client(), all_products)
    yield
    await close_redis()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="TideMarket 潮汐市集", version="1.0.0", lifespan=lifespan)

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(products.router)
    app.include_router(orders.router)
    app.include_router(notifications.router)
    app.include_router(admin.router)

    os.makedirs(settings.upload_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        user_id = await ws_authenticate(ws)
        if user_id is None:
            await ws.close(code=4401)
            return
        await manager.connect(user_id, ws)
        try:
            while True:
                await ws.receive_text()     # 保持连接，兼容心跳/客户端消息
        except WebSocketDisconnect:
            manager.disconnect(user_id, ws)

    @app.get("/api/health")
    async def health():
        return {"ok": True, "service": "tidemarket"}

    return app


app = create_app()
