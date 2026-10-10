"""异步数据库引擎与会话。演示项目用 create_all 建表，生产环境应换 alembic 迁移。"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings

engine = create_async_engine(get_settings().database_url, pool_pre_ping=True, pool_size=10)
Session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator:
    async with Session() as session:
        yield session


async def init_db() -> None:
    # 先 import models 注册表
    from . import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
