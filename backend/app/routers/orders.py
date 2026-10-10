"""订单：下单（幂等+三层防超卖）、我的订单、详情、模拟支付（幂等）、取消。"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import get_current_user
from ..models import Order, Product, User
from ..schemas import OrderIn, OrderOut
from ..services import orders as svc

router = APIRouter(prefix="/api/orders", tags=["orders"])


async def _to_out(db: AsyncSession, o: Order) -> OrderOut:
    out = OrderOut.model_validate(o)
    product = await db.get(Product, o.product_id)
    out.product_title = product.title if product else "（已删除）"
    out.product_image = (product.images[0] if product and product.images else None)
    out.seller_id = product.seller_id if product else None
    return out


@router.post("", response_model=OrderOut, status_code=201)
async def create_order(body: OrderIn, user: User = Depends(get_current_user),
                       db: AsyncSession = Depends(get_db)):
    order = await svc.create_order(db, user, body.product_id, body.idempotency_key)
    return await _to_out(db, order)


@router.get("/mine", response_model=list[OrderOut])
async def my_orders(role: str = Query(default="buyer", pattern="^(buyer|seller)$"),
                    user: User = Depends(get_current_user),
                    db: AsyncSession = Depends(get_db)):
    if role == "buyer":
        rows = (await db.execute(
            select(Order).where(Order.buyer_id == user.id).order_by(Order.created_at.desc())
        )).scalars().all()
    else:
        rows = (await db.execute(
            select(Order).join(Product, Product.id == Order.product_id)
            .where(Product.seller_id == user.id).order_by(Order.created_at.desc())
        )).scalars().all()
    return [await _to_out(db, o) for o in rows]


@router.get("/{oid}", response_model=OrderOut)
async def order_detail(oid: str, user: User = Depends(get_current_user),
                       db: AsyncSession = Depends(get_db)):
    order = await db.get(Order, oid)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "订单不存在")
    product = await db.get(Product, order.product_id)
    is_seller = product is not None and product.seller_id == user.id
    if order.buyer_id != user.id and not is_seller and user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "无权查看该订单")
    return await _to_out(db, order)


@router.post("/{oid}/pay", response_model=OrderOut)
async def pay(oid: str, key: str = Query(min_length=8, max_length=64),
              user: User = Depends(get_current_user),
              db: AsyncSession = Depends(get_db)):
    order = await svc.pay_order(db, user, oid, key)
    return await _to_out(db, order)


@router.post("/{oid}/cancel", response_model=OrderOut)
async def cancel(oid: str, user: User = Depends(get_current_user),
                 db: AsyncSession = Depends(get_db)):
    order = await svc.cancel_order(db, user, oid)
    return await _to_out(db, order)
