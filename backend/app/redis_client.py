"""Redis 访问层：库存闸口 + 详情缓存。client 懒连接，首次使用时才握手。"""
import json
from collections.abc import AsyncGenerator

import redis.asyncio as redis

from .config import get_settings

_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(get_settings().redis_url, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def get_redis() -> AsyncGenerator:
    yield get_redis_client()


def stock_key(product_id: int) -> str:
    return f"product:{product_id}:stock"


def detail_key(product_id: int) -> str:
    return f"product:{product_id}:detail"


async def read_stock(r: redis.Redis, product_id: int) -> int | None:
    """读 Redis 库存；未初始化（key 不存在）返回 None，由调用方回源数据库。"""
    v = await r.get(stock_key(product_id))
    return int(v) if v is not None else None


async def sync_all_stock(r: redis.Redis, products: list) -> None:
    """启动时对账：以数据库库存为准重写 Redis，消除重启/漂移造成的不一致。"""
    pipe = r.pipeline()
    for p in products:
        pipe.set(stock_key(p.id), p.stock)
    if products:
        await pipe.execute()


async def cache_detail(r: redis.Redis, product_id: int, data: dict, ttl: int = 60) -> None:
    await r.set(detail_key(product_id), json.dumps(data, ensure_ascii=False), ex=ttl)


async def read_detail(r: redis.Redis, product_id: int) -> dict | None:
    raw = await r.get(detail_key(product_id))
    return json.loads(raw) if raw else None


async def invalidate_detail(r: redis.Redis, product_id: int) -> None:
    await r.delete(detail_key(product_id))
