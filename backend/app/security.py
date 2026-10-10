"""密码哈希与 JWT。直接用 bcrypt 库，绕开 passlib 与新版本 bcrypt 的兼容问题。"""
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from .config import get_settings

ALGO = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_access_token(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=get_settings().token_expire_minutes
    )
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, get_settings().secret_key, algorithm=ALGO)


def decode_token(token: str) -> dict | None:
    """解析失败（过期/伪造/缺字段）一律返回 None，由调用方决定 401 文案。"""
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=[ALGO])
        return {"user_id": int(payload["sub"]), "role": payload.get("role", "user")}
    except (JWTError, KeyError, ValueError):
        return None
