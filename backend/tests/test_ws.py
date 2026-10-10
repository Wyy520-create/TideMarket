"""WebSocket 实时通知集成测试：进程内起 uvicorn，websockets 客户端真连真收。"""
import asyncio
import json
import uuid

import pytest
import pytest_asyncio
import uvicorn
import websockets
from httpx import AsyncClient

from app.main import app

AUTH = lambda token: {"Authorization": f"Bearer {token}"}  # noqa: E731


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def live_base():
    # conftest 关了 seed_on_start，这里手动种演示数据（幂等，已有数据则跳过）
    from app.seed import seed
    await seed()

    config = uvicorn.Config(app, host="127.0.0.1", port=8471, log_level="error")
    server = uvicorn.Server(config)
    task = asyncio.get_event_loop().create_task(server.serve())
    for _ in range(200):
        if server.started:
            break
        await asyncio.sleep(0.05)
    yield "http://127.0.0.1:8471"
    server.should_exit = True
    await task


async def _login(base: str, username: str, password: str) -> str:
    async with AsyncClient(base_url=base) as c:
        r = await c.post("/api/auth/login",
                         json={"username": username, "password": password})
        assert r.status_code == 200, r.text
        return r.json()["token"]


async def test_ws_realtime_notification(live_base):
    """卖家保持 WS 在线，买家下单后卖家应实时收到 order.created 推送。"""
    seller_token = await _login(live_base, "xiaoyu", "xiaoyu123456")
    admin_token = await _login(live_base, "admin", "admin123456")
    buyer_token = await _login(live_base, "ahai", "ahai123456")

    async with AsyncClient(base_url=live_base) as c:
        # 现场发布专用商品并审核通过，不依赖种子里商品的剩余库存
        r = await c.post("/api/products", json={
            "title": "WS 实时通知测试专用", "description": "websocket integration test",
            "price": 100, "category": "other", "stock": 1, "images": [],
        }, headers=AUTH(seller_token))
        assert r.status_code == 201, r.text
        pid = r.json()["id"]
        r = await c.post(f"/api/admin/products/{pid}/approve", headers=AUTH(admin_token))
        assert r.status_code == 200, r.text

        ws_url = live_base.replace("http", "ws") + f"/ws?token={seller_token}"
        async with websockets.connect(ws_url, open_timeout=5) as ws:
            await asyncio.sleep(0.3)                # 等连接注册进 ConnectionManager
            r = await c.post("/api/orders", json={
                "product_id": pid,
                "idempotency_key": f"ws-key-{uuid.uuid4().hex}",
            }, headers=AUTH(buyer_token))
            assert r.status_code == 201, r.text

            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            assert msg["type"] == "order.created"
            assert "WS 实时通知测试专用" in msg["body"]


async def test_ws_rejects_bad_token(live_base):
    ws_url = live_base.replace("http", "ws") + "/ws?token=bad-token"
    with pytest.raises(Exception):
        async with websockets.connect(ws_url, open_timeout=5):
            pass
