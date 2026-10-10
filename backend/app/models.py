"""数据模型。价格/金额一律用 int 存「分」，避免浮点误差。"""
import enum
from datetime import datetime

from sqlalchemy import (
    JSON, DateTime, Enum, ForeignKey, Integer, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class ProductStatus(str, enum.Enum):
    pending = "pending"    # 待审核
    on_sale = "on_sale"    # 在售
    rejected = "rejected"  # 审核拒绝
    off = "off"            # 卖家自己下架


class OrderStatus(str, enum.Enum):
    pending = "pending"    # 待支付
    paid = "paid"          # 已支付
    cancelled = "cancelled"  # 已取消（买家主动 / 超时）


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(128), unique=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.user)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[int] = mapped_column(Integer)          # 分
    category: Mapped[str] = mapped_column(String(16), default="other", index=True)
    images: Mapped[list] = mapped_column(JSON, default=list)
    stock: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus), default=ProductStatus.pending, index=True
    )
    views: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)  # TM+uuid
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    amount: Mapped[int] = mapped_column(Integer)          # 分
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.pending, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class IdempotencyKey(Base):
    """支付回调去重表：同一回调 key 只处理一次。"""
    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(32))         # order.created / order.paid ...
    title: Mapped[str] = mapped_column(String(64))
    body: Mapped[str] = mapped_column(String(255), default="")
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
