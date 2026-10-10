"""arq 异步任务 worker：每分钟扫描超时未支付订单，关闭并回补库存。

启动方式（在 backend 目录下）：
    arq worker.WorkerSettings
"""
from arq import cron
from arq.connections import RedisSettings

from app.config import get_settings
from app.db import Session
from app.services.orders import expire_pending_orders


async def close_expired_orders(ctx) -> int:
    async with Session() as db:
        return await expire_pending_orders(db)


class WorkerSettings:
    functions: list = []
    cron_jobs = [
        cron(close_expired_orders, minute=set(range(60))),   # 每分钟整点跑一次
    ]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 4
    job_timeout = 60
