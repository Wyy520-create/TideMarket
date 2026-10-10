"""接口测试：认证、商品、下单（并发防超卖）、支付幂等、取消、超时关单、通知、RBAC。"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.db import Session
from app.models import Order
from app.services.orders import expire_pending_orders

from conftest import (auth, create_order, make_admin, publish_product,
                      register_user, uniq)


# ---------------- 认证 ----------------
async def test_register_login_me(http_client):
    c = http_client
    u = await register_user(c, "alice")
    me = await c.get("/api/auth/me", headers=auth(u["token"]))
    assert me.status_code == 200
    assert me.json()["username"] == u["user"]["username"]

    r = await c.post("/api/auth/login", json={
        "username": u["user"]["username"], "password": "pass123456"})
    assert r.status_code == 200 and r.json()["token"]


async def test_duplicate_register_409(http_client):
    c = http_client
    u = await register_user(c, "bob")
    r = await c.post("/api/auth/register", json={
        "username": u["user"]["username"],
        "email": "other-duplicate@163.com",
        "password": "pass123456",
    })
    assert r.status_code == 409


async def test_wrong_password_401(http_client):
    c = http_client
    u = await register_user(c, "carl")
    r = await c.post("/api/auth/login", json={
        "username": u["user"]["username"], "password": "wrong-password"})
    assert r.status_code == 401


# ---------------- 商品 ----------------
async def test_product_pending_then_approved(http_client):
    c = http_client
    seller = await register_user(c, "seller")
    admin = await make_admin(c)

    r = await c.post("/api/products", json={
        "title": uniq("机械键盘"), "description": "青轴热插拔",
        "price": 12300, "category": "digital", "stock": 2, "images": [],
    }, headers=auth(seller["token"]))
    assert r.status_code == 201
    p = r.json()
    assert p["status"] == "pending"                 # 发布后默认待审核

    listed = await c.get("/api/products")
    assert all(i["id"] != p["id"] for i in listed.json()["items"])

    approved = await c.post(f"/api/admin/products/{p['id']}/approve",
                            headers=auth(admin["token"]))
    assert approved.status_code == 200
    assert approved.json()["status"] == "on_sale"

    detail = await c.get(f"/api/products/{p['id']}")
    assert detail.status_code == 200
    assert detail.json()["stock"] == 2


async def test_product_search_filter(http_client):
    c = http_client
    admin = await make_admin(c)
    seller = await register_user(c, "s2")
    await publish_product(c, seller["token"], admin["token"],
                          title="独一无二的量子茶壶", price=8800)
    r = await c.get("/api/products", params={"q": "量子茶壶"})
    assert any("量子茶壶" in i["title"] for i in r.json()["items"])
    r = await c.get("/api/products", params={"q": "量子茶壶", "sort": "price_asc"})
    assert r.status_code == 200


# ---------------- 下单 / 并发防超卖（核心） ----------------
async def test_buy_own_product_400(http_client):
    c = http_client
    admin = await make_admin(c)
    seller = await register_user(c, "own")
    p = await publish_product(c, seller["token"], admin["token"])
    r = await create_order(c, seller["token"], p["id"])
    assert r["status"] == 400


async def test_concurrent_orders_no_oversell(http_client):
    """20 个并发买家抢 5 件库存：必须恰好 5 单成功、15 单 409，最终库存为 0。"""
    c = http_client
    admin = await make_admin(c)
    seller = await register_user(c, "hot")
    p = await publish_product(c, seller["token"], admin["token"], stock=5)

    buyers = [await register_user(c, f"b{i}") for i in range(20)]
    results = await asyncio.gather(*[
        create_order(c, b["token"], p["id"]) for b in buyers
    ])
    ok = [r for r in results if r["status"] == 201]
    fail = [r for r in results if r["status"] == 409]
    assert len(ok) == 5, f"成功 {len(ok)} 单，期望 5"
    assert len(fail) == 15
    assert len({r["data"]["id"] for r in ok}) == 5    # 订单互不相同

    detail = await c.get(f"/api/products/{p['id']}")
    assert detail.json()["stock"] == 0


async def test_idempotent_order_same_key(http_client):
    """同一幂等 key 重复提交：不产生新订单，库存只扣一次。"""
    c = http_client
    admin = await make_admin(c)
    seller = await register_user(c, "idem")
    p = await publish_product(c, seller["token"], admin["token"], stock=3)
    buyer = await register_user(c, "ib")

    key = uniq("same-key")
    r1 = await create_order(c, buyer["token"], p["id"], key=key)
    r2 = await create_order(c, buyer["token"], p["id"], key=key)
    assert r1["status"] == 201 and r2["status"] == 201
    assert r1["data"]["id"] == r2["data"]["id"]

    detail = await c.get(f"/api/products/{p['id']}")
    assert detail.json()["stock"] == 2


# ---------------- 支付幂等 / 状态机 ----------------
async def test_pay_and_replay_same_callback(http_client):
    """同一支付回调 key 重放：第二次幂等返回，不产生冲突。"""
    c = http_client
    admin = await make_admin(c)
    seller = await register_user(c, "pay")
    p = await publish_product(c, seller["token"], admin["token"])
    buyer = await register_user(c, "pb")
    order = (await create_order(c, buyer["token"], p["id"]))["data"]

    key = uniq("pay-cb")
    r1 = await c.post(f"/api/orders/{order['id']}/pay",
                      params={"key": key}, headers=auth(buyer["token"]))
    assert r1.status_code == 200 and r1.json()["status"] == "paid"

    r2 = await c.post(f"/api/orders/{order['id']}/pay",
                      params={"key": key}, headers=auth(buyer["token"]))
    assert r2.status_code == 200 and r2.json()["status"] == "paid"

    r3 = await c.post(f"/api/orders/{order['id']}/pay",
                      params={"key": uniq("other")}, headers=auth(buyer["token"]))
    assert r3.status_code == 409                    # 新 key 但状态机已流转


async def test_pay_others_order_403(http_client):
    c = http_client
    admin = await make_admin(c)
    seller = await register_user(c, "po")
    p = await publish_product(c, seller["token"], admin["token"])
    buyer = await register_user(c, "pob")
    stranger = await register_user(c, "str")
    order = (await create_order(c, buyer["token"], p["id"]))["data"]
    r = await c.post(f"/api/orders/{order['id']}/pay",
                     params={"key": uniq("k")}, headers=auth(stranger["token"]))
    assert r.status_code == 403


# ---------------- 取消与超时回补 ----------------
async def test_cancel_restores_stock(http_client):
    c = http_client
    admin = await make_admin(c)
    seller = await register_user(c, "cxl")
    p = await publish_product(c, seller["token"], admin["token"], stock=2)
    buyer = await register_user(c, "cb")
    order = (await create_order(c, buyer["token"], p["id"]))["data"]

    r = await c.post(f"/api/orders/{order['id']}/cancel", headers=auth(buyer["token"]))
    assert r.status_code == 200 and r.json()["status"] == "cancelled"

    detail = await c.get(f"/api/products/{p['id']}")
    assert detail.json()["stock"] == 2              # 库存回补

    again = await c.post(f"/api/orders/{order['id']}/cancel",
                         headers=auth(buyer["token"]))
    assert again.status_code == 409                 # 已取消不能再取消


async def test_expire_pending_orders_restores_stock(http_client):
    """模拟超时：把下单时间回拨 20 分钟，定时任务关单并回补库存。"""
    c = http_client
    admin = await make_admin(c)
    seller = await register_user(c, "exp")
    p = await publish_product(c, seller["token"], admin["token"], stock=1)
    buyer = await register_user(c, "eb")
    order = (await create_order(c, buyer["token"], p["id"]))["data"]

    async with Session() as db:
        row = await db.get(Order, order["id"])
        row.created_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=20)
        await db.commit()
        closed = await expire_pending_orders(db)
        assert closed >= 1
        await db.commit()

    mine = await c.get("/api/orders/mine", headers=auth(buyer["token"]))
    target = [o for o in mine.json() if o["id"] == order["id"]][0]
    assert target["status"] == "cancelled"

    detail = await c.get(f"/api/products/{p['id']}")
    assert detail.json()["stock"] == 1


# ---------------- 通知 ----------------
async def test_notification_created_and_read_all(http_client):
    c = http_client
    admin = await make_admin(c)
    seller = await register_user(c, "ntf")
    p = await publish_product(c, seller["token"], admin["token"])
    buyer = await register_user(c, "nb")
    await create_order(c, buyer["token"], p["id"])

    notes = await c.get("/api/notifications", headers=auth(seller["token"]))
    assert notes.status_code == 200
    items = notes.json()
    assert any(n["type"] == "order.created" for n in items)

    r = await c.post("/api/notifications/read_all", headers=auth(seller["token"]))
    assert r.status_code == 200
    notes = await c.get("/api/notifications", headers=auth(seller["token"]))
    assert all(n["is_read"] for n in notes.json())


# ---------------- RBAC ----------------
async def test_admin_endpoints_forbidden_for_normal_user(http_client):
    c = http_client
    u = await register_user(c, "norm")
    for method, url in [
        ("GET", "/api/admin/stats"),
        ("GET", "/api/admin/products"),
        ("GET", "/api/admin/users"),
    ]:
        r = await getattr(c, method.lower())(url, headers=auth(u["token"]))
        assert r.status_code == 403, f"{url} 应返回 403，实际 {r.status_code}"


async def test_admin_change_role_effective(http_client):
    c = http_client
    admin = await make_admin(c)
    u = await register_user(c, "promote")
    r = await c.patch(f"/api/admin/users/{u['user']['id']}/role",
                      json={"role": "admin"}, headers=auth(admin["token"]))
    assert r.status_code == 200 and r.json()["role"] == "admin"

    stats = await c.get("/api/admin/stats", headers=auth(u["token"]))
    assert stats.status_code == 200


async def test_unauthorized_401(http_client):
    r = await http_client.get("/api/orders/mine")
    assert r.status_code == 401


@pytest.mark.parametrize("uid", [str(uuid.uuid4())])
async def test_health(http_client, uid):
    r = await http_client.get("/api/health")
    assert r.json()["ok"] is True
