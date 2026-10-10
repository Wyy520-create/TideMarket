"""订单核心逻辑：三层防超卖 + 订单状态机 + 支付幂等。

三层防超卖：
  1. Redis DECR 原子预扣 —— 把绝大多数超卖请求挡在数据库之外；
  2. DB 条件 UPDATE（stock >= n）—— 乐观锁兜底，Redis 与 DB 不一致时仍以 DB 为准；
  3. 订单表 idempotency_key 唯一约束 —— 网络重试/双击不会产生重复订单。
任何一步失败都要按相反顺序回滚前面已执行的预扣。
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..deps import notify
from ..models import IdempotencyKey, Order, OrderStatus, Product, ProductStatus, User
from ..redis_client import get_redis_client, stock_key


class SoldOut(HTTPException):
    def __init__(self) -> None:
        super().__init__(status.HTTP_409_CONFLICT, "手慢了，商品已售罄")


def new_order_id() -> str:
    return "TM" + uuid.uuid4().hex[:20].upper()


async def create_order(db: AsyncSession, buyer: User, product_id: int, idem_key: str) -> Order:
    # 幂等：同一提交 key 直接返回已有订单（网络重试 / 双击安全）
    existing = (await db.execute(
        select(Order).where(Order.idempotency_key == idem_key)
    )).scalar_one_or_none()
    if existing:
        return existing

    product = await db.get(Product, product_id)
    if product is None or product.status != ProductStatus.on_sale:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "商品不存在或未上架")
    if product.seller_id == buyer.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能购买自己的商品")

    r = get_redis_client()

    # 第 1 层：Redis 原子预扣
    remain = await r.decr(stock_key(product.id))
    if remain < 0:
        await r.incr(stock_key(product.id))          # 回滚预扣
        raise SoldOut()

    # 第 2 层：DB 乐观锁兜底
    result = await db.execute(
        update(Product)
        .where(Product.id == product.id, Product.stock >= 1)
        .values(stock=Product.stock - 1)
        .returning(Product.stock)
    )
    new_stock = result.scalar_one_or_none()
    if new_stock is None:                            # 库存不足，回补 Redis
        await r.incr(stock_key(product.id))
        raise SoldOut()

    order = Order(
        id=new_order_id(), buyer_id=buyer.id, product_id=product.id,
        quantity=1, amount=product.price, idempotency_key=idem_key,
    )
    db.add(order)
    try:
        await db.commit()
    except Exception:                                # 第 3 层：唯一约束等冲突
        await db.rollback()
        await r.incr(stock_key(product.id))          # 回补
        existing = (await db.execute(
            select(Order).where(Order.idempotency_key == idem_key)
        )).scalar_one_or_none()
        if existing:
            return existing
        raise

    seller = await db.get(User, product.seller_id)
    await notify(db, product.seller_id, "order.created", "商品被拍下",
                 f"买家 {buyer.username} 拍下了「{product.title}」，等待支付")
    await db.commit()
    return order


async def pay_order(db: AsyncSession, user: User, order_id: str, idem_key: str) -> Order:
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "订单不存在")
    if order.buyer_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "只能支付自己的订单")

    # 回调去重表：同一支付流水 key 只入账一次
    db.add(IdempotencyKey(key=idem_key, order_id=order.id))
    try:
        await db.flush()
    except Exception:
        await db.rollback()
        order = await db.get(Order, order_id)
        return order                                 # 已处理过，直接返回当前状态

    # 状态机：仅允许 PENDING -> PAID，条件 UPDATE 保证并发回调只有一个成功
    result = await db.execute(
        update(Order)
        .where(Order.id == order.id, Order.status == OrderStatus.pending)
        .values(status=OrderStatus.paid, paid_at=datetime.now(timezone.utc).replace(tzinfo=None))
        .returning(Order.status)
    )
    new_status = result.scalar_one_or_none()
    if new_status != OrderStatus.paid.value:
        await db.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, "订单状态已变化，请刷新")

    product = await db.get(Product, order.product_id)
    await notify(db, product.seller_id, "order.paid", "订单已支付",
                 f"「{product.title}」已支付，金额 ¥{order.amount / 100:.2f}")
    await db.commit()
    return order


async def cancel_order(db: AsyncSession, user: User, order_id: str) -> Order:
    order = await db.get(Order, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "订单不存在")
    if order.buyer_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "只能取消自己的订单")

    # 条件 UPDATE 承担并发安全：只有仍是 PENDING 的订单能取消
    result = await db.execute(
        update(Order)
        .where(Order.id == order.id, Order.status == OrderStatus.pending)
        .values(status=OrderStatus.cancelled)
        .returning(Order.status)
    )
    new_status = result.scalar_one_or_none()
    if new_status != OrderStatus.cancelled.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "订单状态已变化，无法取消")

    # 回补库存：先 DB 后 Redis，Redis 以 DB 为准由启动对账兜底
    await db.execute(
        update(Product).where(Product.id == order.product_id)
        .values(stock=Product.stock + order.quantity)
    )
    await db.commit()
    await get_redis_client().incr(stock_key(order.product_id), order.quantity)

    product = await db.get(Product, order.product_id)
    await notify(db, product.seller_id, "order.cancelled", "订单已取消",
                 f"「{product.title}」的买家取消了订单，库存已回补")
    await db.commit()
    return order


async def expire_pending_orders(db: AsyncSession) -> int:
    """关闭超时未支付订单并回补库存。由 arq worker 每分钟调用，测试可直接调用。"""
    deadline = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        minutes=get_settings().order_expire_minutes
    )
    rows = (await db.execute(
        select(Order).where(Order.status == OrderStatus.pending, Order.created_at < deadline)
    )).scalars().all()
    closed = 0
    for order in rows:
        result = await db.execute(
            update(Order)
            .where(Order.id == order.id, Order.status == OrderStatus.pending)
            .values(status=OrderStatus.cancelled)
            .returning(Order.status)
        )
        if result.scalar_one_or_none() != OrderStatus.cancelled.value:
            continue
        await db.execute(
            update(Product).where(Product.id == order.product_id)
            .values(stock=Product.stock + order.quantity)
        )
        await get_redis_client().incr(stock_key(order.product_id), order.quantity)
        await notify(db, order.buyer_id, "order.expired", "订单超时关闭",
                     f"订单 {order.id} 超时未支付，已自动关闭并释放库存")
        closed += 1
    await db.commit()
    return closed
