"""演示数据：1 个管理员 + 2 个普通用户 + 12 件在售商品（含生成的占位图）。

幂等：按用户名/商品表逐条判断，缺失才补，重复启动或先有次级数据都不会重复写入。
账号密码仅供本地/演示环境，生产部署请通过环境变量关闭 seed 并修改口令。
"""
from pathlib import Path

from sqlalchemy import func, select

from .config import get_settings
from .db import Session
from .models import Product, ProductStatus, User, UserRole
from .security import hash_password

PALETTES = [
    ("#6366f1", "#a855f7"), ("#0ea5e9", "#22d3ee"), ("#f59e0b", "#ef4444"),
    ("#10b981", "#84cc16"), ("#ec4899", "#8b5cf6"), ("#f97316", "#facc15"),
]

PRODUCTS = [
    {"title": "索尼 A6000 微单相机（9 成新）", "description": "套机含 16-50mm 镜头，快门不到 5000 次，箱说配件齐全，顺丰包邮。",
     "price": 218000, "category": "digital", "stock": 1, "emoji": "📷"},
    {"title": "《深入理解计算机系统》CSAPP", "description": "原书第 3 版，九成新，内页无笔记无划线，适合自学。",
     "price": 4500, "category": "book", "stock": 3, "emoji": "📚"},
    {"title": "优衣库轻型羽绒服 L 码", "description": "去年冬天购入，仅出门旅游穿过两次，已干洗，几乎全新。",
     "price": 12900, "category": "clothes", "stock": 2, "emoji": "🧥"},
    {"title": "罗技 MX Master 3S 无线鼠标", "description": "办公神器，电磁滚轮，自定义侧键，包装配件齐全，保修期内。",
     "price": 39900, "category": "digital", "stock": 1, "emoji": "🖱️"},
    {"title": "小米智能台灯 1S", "description": "支持米家 App 调色温亮度，护眼无频闪，搬家转让。",
     "price": 7900, "category": "life", "stock": 2, "emoji": "💡"},
    {"title": "《人类简史》精装版", "description": "尤瓦尔·赫拉利代表作，豆瓣评分 9.1，书脊完好。",
     "price": 2500, "category": "book", "stock": 4, "emoji": "📖"},
    {"title": "耐克 Air Force 1 纯白 42 码", "description": "专柜购入，上脚不超过五次，鞋盒在，支持验货。",
     "price": 32000, "category": "clothes", "stock": 1, "emoji": "👟"},
    {"title": "IKBC 机械键盘 87 键青轴", "description": "手感清脆，全键无冲，PBT 键帽不打油，功能正常。",
     "price": 16900, "category": "digital", "stock": 2, "emoji": "⌨️"},
    {"title": "宜家 LACK 拉克边桌", "description": "55x55 白色小方桌，自用一年，无磕碰，仅限自提。",
     "price": 4900, "category": "life", "stock": 1, "emoji": "🪑"},
    {"title": "《算法导论》英文版第 3 版", "description": "CLRS 原版影印，图书馆级品相，计算机考研/面试必备。",
     "price": 8800, "category": "book", "stock": 2, "emoji": "📕"},
    {"title": "Kindle Paperwhite 5", "description": "6.8 英寸 300ppi，冷暖光可调，8G 版，带原装保护套。",
     "price": 55000, "category": "digital", "stock": 1, "emoji": "📱"},
    {"title": "星巴克保温杯 500ml", "description": "经典人鱼款，保温 6 小时，杯盖密封完好，闲置出。",
     "price": 6500, "category": "life", "stock": 3, "emoji": "☕"},
]


def _write_svg(path: Path, emoji: str, label: str, c1: str, c2: str) -> None:
    """生成一张渐变底 + emoji 的占位图，避免演示数据出现裂图。"""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/>'
        '</linearGradient></defs>'
        '<rect width="640" height="480" fill="url(#g)"/>'
        f'<text x="320" y="225" font-size="130" text-anchor="middle">{emoji}</text>'
        f'<text x="320" y="420" font-size="26" fill="#ffffff" text-anchor="middle">{label}</text>'
        '</svg>'
    )
    path.write_text(svg, encoding="utf-8")


async def seed_users(db) -> dict:
    """按用户名 upsert 演示账号，返回 {username: User}。"""
    existing = {u.username: u for u in (await db.execute(select(User))).scalars()}
    specs = [
        ("admin", "admin123456", UserRole.admin),
        ("xiaoyu", "xiaoyu123456", UserRole.user),
        ("ahai", "ahai123456", UserRole.user),
    ]
    users: dict = {}
    for name, pwd, role in specs:
        if name in existing:
            users[name] = existing[name]
        else:
            u = User(username=name, email=f"{name}@tidemarket.local",
                     password_hash=hash_password(pwd), role=role)
            db.add(u)
            users[name] = u
    await db.flush()
    return users


async def seed() -> None:
    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    async with Session() as db:
        users = await seed_users(db)
        product_count = (await db.execute(
            select(func.count()).select_from(Product))).scalar_one()
        if product_count == 0:
            for i, raw in enumerate(PRODUCTS):
                item = dict(raw)
                emoji = item.pop("emoji")
                c1, c2 = PALETTES[i % len(PALETTES)]
                name = f"seed-{i + 1}.svg"
                _write_svg(upload_dir / name, emoji, item["title"], c1, c2)
                owner = users["xiaoyu"] if i % 2 == 0 else users["ahai"]
                db.add(Product(
                    seller_id=owner.id, status=ProductStatus.on_sale,
                    images=[f"/uploads/{name}"], views=(i * 37) % 100, **item,
                ))
        await db.commit()
