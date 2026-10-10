"""pytest 公共配置：准备独立测试库 + 常用 HTTP/数据助手。

默认连接本机 compose 起的 Postgres(5439) / Redis(6399)，可用环境变量覆盖：
    TM_DATABASE_URL / TM_REDIS_URL
测试库名为 tidemarket_test，session 结束后整库 drop，互不污染。
整个 session 共享同一个事件循环（见 pytest.ini），避免 asyncpg/redis 客户端跨 loop。
"""
import os
import tempfile
import uuid

import pytest

# 必须在导入 app 之前设置环境变量（app.db 在 import 时就创建 engine）
os.environ.setdefault(
    "TM_DATABASE_URL",
    "postgresql+asyncpg://tide:tide@localhost:5439/tidemarket_test",
)
os.environ.setdefault("TM_REDIS_URL", "redis://localhost:6399/1")
os.environ["TM_UPLOAD_DIR"] = tempfile.mkdtemp(prefix="tm-uploads-")
os.environ["TM_SEED_ON_START"] = "false"

import asyncpg  # noqa: E402
import pytest_asyncio  # noqa: E402

from app.db import Base, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


async def _ensure_database() -> None:
    conn = await asyncpg.connect(
        "postgresql://tide:tide@localhost:5439/postgres")
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'tidemarket_test'")
        if not exists:
            await conn.execute("CREATE DATABASE tidemarket_test")
    finally:
        await conn.close()


async def _prepare_database() -> None:
    await _ensure_database()
    await init_db()
    await engine.dispose()                 # 让测试在自己的 loop 里重建连接


async def _teardown_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def prepare_database():
    await _prepare_database()
    yield
    await _teardown_database()


@pytest.fixture()
def http_client():
    from httpx import ASGITransport, AsyncClient
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


@pytest_asyncio.fixture(autouse=True)
async def _flush_redis():
    """每个测试前清空 Redis，避免上一个用例的库存/缓存造成串扰。"""
    from app.redis_client import get_redis_client
    await get_redis_client().flushdb()


# ---------------- 业务助手 ----------------
def uniq(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def register_user(client, prefix: str = "u") -> dict:
    """注册新用户，返回 {"token", "user"}。"""
    username = uniq(prefix)
    r = await client.post("/api/auth/register", json={
        "username": username,
        "email": f"{username}@qq.com",
        "password": "pass123456",
    })
    assert r.status_code == 201, r.text
    data = r.json()
    return {"token": data["token"], "user": data["user"]}


async def make_admin(client) -> dict:
    """注册一个用户并在 DB 里直接提权为 admin（ASGI 模式不跑 seed，没有现成管理员）。"""
    data = await register_user(client, "adm")
    from app.db import Session
    from app.models import User, UserRole
    async with Session() as db:
        u = await db.get(User, data["user"]["id"])
        u.role = UserRole.admin
        await db.commit()
    data["user"]["role"] = "admin"
    return data


async def publish_product(client, seller_token: str, admin_token: str,
                          stock: int = 1, price: int = 9900, **kw) -> dict:
    """卖家发布 + 管理员审核通过，返回上架后的商品（Redis 库存闸口已初始化）。"""
    body = {
        "title": kw.get("title", uniq("商品")),
        "description": kw.get("description", "pytest 上架的测试商品"),
        "price": price,
        "category": kw.get("category", "digital"),
        "stock": stock,
        "images": kw.get("images", []),
    }
    r = await client.post("/api/products", json=body, headers=auth(seller_token))
    assert r.status_code == 201, r.text
    p = r.json()
    r = await client.post(f"/api/admin/products/{p['id']}/approve",
                          headers=auth(admin_token))
    assert r.status_code == 200, r.text
    return r.json()


async def create_order(client, buyer_token: str, product_id: int,
                       key: str | None = None) -> dict:
    r = await client.post("/api/orders", json={
        "product_id": product_id,
        "idempotency_key": key or uniq("key"),
    }, headers=auth(buyer_token))
    return {"status": r.status_code, "data": r.json() if r.content else {}}
