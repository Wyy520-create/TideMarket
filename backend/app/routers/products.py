"""商品：发布（进审核）、分页浏览/搜索/筛选、详情、图片上传。

列表/详情只展示 on_sale 商品；库存实时读 Redis（详情其余字段走 60s 缓存）。
"""
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db import get_db
from ..deps import get_current_user
from ..models import Product, ProductStatus, User
from ..redis_client import (cache_detail, get_redis_client, invalidate_detail,
                            read_detail, read_stock)
from ..schemas import ProductIn, ProductOut, ProductPage

router = APIRouter(prefix="/api", tags=["products"])

CATEGORIES = {"digital", "book", "clothes", "life", "other"}
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _to_out(p: Product, stock: int, seller_name: str) -> ProductOut:
    out = ProductOut.model_validate(p)
    out.stock = stock
    out.seller_name = seller_name
    return out


@router.post("/upload", status_code=201)
async def upload(file: UploadFile, user: User = Depends(get_current_user)):
    """单图上传，返回可访问的 /uploads/xxx 相对路径（发布商品时引用）。"""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "仅支持 png/jpg/jpeg/webp/gif")
    data = await file.read()
    limit = get_settings().max_upload_mb * 1024 * 1024
    if len(data) > limit:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "图片超过大小限制")
    name = f"{uuid.uuid4().hex}{ext}"
    os.makedirs(get_settings().upload_dir, exist_ok=True)
    with open(os.path.join(get_settings().upload_dir, name), "wb") as f:
        f.write(data)
    return {"url": f"/uploads/{name}"}


@router.post("/products", response_model=ProductOut, status_code=201)
async def create_product(body: ProductIn, user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    if body.category not in CATEGORIES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "未知分类")
    product = Product(seller_id=user.id, title=body.title, description=body.description,
                      price=body.price, category=body.category, stock=body.stock,
                      images=body.images[:4])
    db.add(product)
    await db.commit()
    return _to_out(product, product.stock, user.username)


@router.get("/products", response_model=ProductPage)
async def list_products(
    q: str = "", category: str = "",
    sort: str = Query(default="new", pattern="^(new|price_asc|price_desc)$"),
    page: int = Query(default=1, ge=1), page_size: int = Query(default=12, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    cond = Product.status == ProductStatus.on_sale
    if category:
        cond = cond & (Product.category == category)
    if q:
        like = f"%{q}%"
        cond = cond & (Product.title.ilike(like) | Product.description.ilike(like))
    total = (await db.execute(select(func.count()).select_from(Product).where(cond))).scalar_one()
    order = {"new": Product.created_at.desc(),
             "price_asc": Product.price.asc(),
             "price_desc": Product.price.desc()}[sort]
    rows = (await db.execute(
        select(Product, User.username)
        .join(User, User.id == Product.seller_id)
        .where(cond).order_by(order)
        .offset((page - 1) * page_size).limit(page_size)
    )).all()
    r = get_redis_client()
    items = [_to_out(p, (await read_stock(r, p.id)) or p.stock, name) for p, name in rows]
    return ProductPage(total=total, page=page, page_size=page_size, items=items)


@router.get("/products/{pid}", response_model=ProductOut)
async def product_detail(pid: int, db: AsyncSession = Depends(get_db)):
    r = get_redis_client()
    cached = await read_detail(r, pid)
    seller_name = None
    if cached:
        p = Product(**cached)  # 仅用于取字段，不 attach session
        stock = (await read_stock(r, pid)) or p.stock
    else:
        row = (await db.execute(
            select(Product, User.username)
            .join(User, User.id == Product.seller_id)
            .where(Product.id == pid)
        )).first()
        if row is None or row[0].status != ProductStatus.on_sale:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "商品不存在或未上架")
        p, seller_name = row
        await db.execute(
            Product.__table__.update().where(Product.id == pid).values(views=Product.views + 1)
        )
        await db.commit()
        stock = (await read_stock(r, pid)) or p.stock
        # 缓存前把 datetime 转成 ISO 字符串，JSON 才能序列化
        data = {c.name: getattr(p, c.name) for c in Product.__table__.columns}
        data["created_at"] = p.created_at.isoformat()
        await cache_detail(r, pid, data)
    if seller_name is None:
        seller_name = (await db.get(User, p.seller_id)).username
    return _to_out(p, stock, seller_name)
