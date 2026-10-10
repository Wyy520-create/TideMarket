"""管理后台：商品审核（通过/拒绝）、平台统计、用户列表与角色调整。

全部端点要求管理员角色（RBAC）：普通用户访问一律 403。
审核通过时初始化 Redis 库存闸口，商品才进入可被抢购的状态。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import get_admin, notify
from ..models import Order, OrderStatus, Product, ProductStatus, User, UserRole
from ..redis_client import (get_redis_client, invalidate_detail, read_stock,
                            stock_key)
from ..schemas import AdminUserOut, ProductOut, RoleIn

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _to_out(p: Product, stock: int, seller_name: str) -> ProductOut:
    out = ProductOut.model_validate(p)
    out.stock = stock
    out.seller_name = seller_name
    return out


async def _stock_of(r, p: Product) -> int:
    s = await read_stock(r, p.id)
    return p.stock if s is None else s


@router.get("/stats")
async def platform_stats(admin: User = Depends(get_admin),
                         db: AsyncSession = Depends(get_db)):
    """仪表盘统计：用户/商品/待审核/订单/已支付订单数量。"""
    async def _count(model, cond=None) -> int:
        q = select(func.count()).select_from(model)
        if cond is not None:
            q = q.where(cond)
        return (await db.execute(q)).scalar_one()

    return {
        "users": await _count(User),
        "products": await _count(Product),
        "pending_products": await _count(Product, Product.status == ProductStatus.pending),
        "orders": await _count(Order),
        "paid_orders": await _count(Order, Order.status == OrderStatus.paid),
    }


@router.get("/products", response_model=list[ProductOut])
async def review_queue(pending_only: bool = Query(default=True),
                       admin: User = Depends(get_admin),
                       db: AsyncSession = Depends(get_db)):
    """审核队列：默认只看待审核商品，传 pending_only=false 看全部。"""
    cond = Product.status == ProductStatus.pending if pending_only else True
    rows = (await db.execute(
        select(Product, User.username)
        .join(User, User.id == Product.seller_id)
        .where(cond)
        .order_by(Product.created_at.asc())
    )).all()
    r = get_redis_client()
    return [_to_out(p, await _stock_of(r, p), name) for p, name in rows]


@router.post("/products/{pid}/approve", response_model=ProductOut)
async def approve_product(pid: int, admin: User = Depends(get_admin),
                          db: AsyncSession = Depends(get_db)):
    """审核通过：pending -> on_sale，并以 DB 库存初始化 Redis 闸口。"""
    product = await db.get(Product, pid)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "商品不存在")
    result = await db.execute(
        update(Product)
        .where(Product.id == pid, Product.status == ProductStatus.pending)
        .values(status=ProductStatus.on_sale)
        .returning(Product.status)
    )
    if result.scalar_one_or_none() != ProductStatus.on_sale.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "该商品不在待审核状态")
    product.status = ProductStatus.on_sale          # 同步内存对象供响应序列化

    r = get_redis_client()
    await r.set(stock_key(pid), product.stock)      # 初始化库存闸口
    await invalidate_detail(r, pid)                 # 清详情缓存
    seller = await db.get(User, product.seller_id)
    await notify(db, product.seller_id, "product.approved", "商品审核通过",
                 f"「{product.title}」已通过审核并上架")
    await db.commit()
    return _to_out(product, product.stock, seller.username)


@router.post("/products/{pid}/reject", response_model=ProductOut)
async def reject_product(pid: int, admin: User = Depends(get_admin),
                         db: AsyncSession = Depends(get_db)):
    """审核拒绝：pending -> rejected，通知卖家。"""
    product = await db.get(Product, pid)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "商品不存在")
    result = await db.execute(
        update(Product)
        .where(Product.id == pid, Product.status == ProductStatus.pending)
        .values(status=ProductStatus.rejected)
        .returning(Product.status)
    )
    if result.scalar_one_or_none() != ProductStatus.rejected.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "该商品不在待审核状态")
    product.status = ProductStatus.rejected

    seller = await db.get(User, product.seller_id)
    await notify(db, product.seller_id, "product.rejected", "商品审核未通过",
                 f"「{product.title}」未通过审核，请修改后重新发布")
    await db.commit()
    return _to_out(product, product.stock, seller.username)


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(admin: User = Depends(get_admin),
                     db: AsyncSession = Depends(get_db)):
    users = (await db.execute(select(User).order_by(User.id.asc()))).scalars().all()
    out = []
    for u in users:
        dto = AdminUserOut.model_validate(u)
        dto.product_count = (await db.execute(
            select(func.count()).select_from(Product).where(Product.seller_id == u.id)
        )).scalar_one()
        dto.order_count = (await db.execute(
            select(func.count()).select_from(Order).where(Order.buyer_id == u.id)
        )).scalar_one()
        out.append(dto)
    return out


@router.patch("/users/{uid}/role", response_model=AdminUserOut)
async def change_role(uid: int, body: RoleIn, admin: User = Depends(get_admin),
                      db: AsyncSession = Depends(get_db)):
    if uid == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能修改自己的角色")
    user = await db.get(User, uid)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    user.role = UserRole(body.role)
    await db.commit()
    return AdminUserOut.model_validate(user)
