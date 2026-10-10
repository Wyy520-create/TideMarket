"""请求/响应的 Pydantic 模型。响应统一用 Out 后缀，金额单位「分」。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- 用户 ----------
class RegisterIn(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    email: EmailStr
    password: str = Field(min_length=6, max_length=64)


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str


class TokenOut(BaseModel):
    token: str
    user: UserOut


# ---------- 商品 ----------
class ProductIn(BaseModel):
    title: str = Field(min_length=2, max_length=64)
    description: str = Field(default="", max_length=2000)
    price: int = Field(gt=0, le=10_000_000)   # 分，>0
    category: str = Field(default="other", max_length=16)
    stock: int = Field(default=1, ge=1, le=999)
    images: list[str] = Field(default_factory=list, max_length=4)


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    seller_id: int
    seller_name: str = ""
    title: str
    description: str
    price: int
    category: str
    images: list
    stock: int
    status: str
    views: int
    created_at: datetime


class ProductPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ProductOut]


# ---------- 订单 ----------
class OrderIn(BaseModel):
    product_id: int
    idempotency_key: str = Field(min_length=8, max_length=64)


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    buyer_id: int
    product_id: int
    product_title: str = ""
    product_image: str | None = None
    seller_id: int | None = None
    quantity: int
    amount: int
    status: str
    created_at: datetime
    paid_at: datetime | None = None


class PayIn(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=64)


# ---------- 通知 ----------
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    title: str
    body: str
    is_read: bool
    created_at: datetime


# ---------- 管理后台 ----------
class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str
    product_count: int = 0
    order_count: int = 0
    created_at: datetime


class RoleIn(BaseModel):
    role: str = Field(pattern="^(user|admin)$")
