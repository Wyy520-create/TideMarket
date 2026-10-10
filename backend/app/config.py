"""集中配置：全部用 TM_ 前缀环境变量覆盖，默认值仅供本地开发。"""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://tide:tide@localhost:5432/tidemarket"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "tidemarket-dev-secret"
    token_expire_minutes: int = 60 * 24 * 7      # 登录 token 有效期
    order_expire_minutes: int = 15               # 订单支付超时时间
    upload_dir: str = "/data/uploads"            # 商品图片存储目录
    max_upload_mb: int = 2                       # 单图大小上限
    cors_origins: str = "*"                      # 逗号分隔；* 表示不限制
    seed_on_start: bool = True                   # 首次启动写入演示数据

    class Config:
        env_prefix = "TM_"


@lru_cache
def get_settings() -> Settings:
    return Settings()
