# 🌊 潮汐市集 TideMarket

前后端分离的 C2C 闲置交易平台：发布商品 → 管理员审核 → 浏览/搜索 → 下单抢库存 → 模拟支付 → 订单状态流转 → 实时通知，全流程可体验。

后端围绕"**并发场景下库存与订单的一致性**"做了三层防护（Redis 原子预扣 → 数据库乐观锁兜底 → 唯一约束防重复下单），支付回调具备幂等能力，超时未支付订单由后台定时任务自动关闭并回补库存。

![CI](https://github.com/Wyy520-create/TideMarket/actions/workflows/ci.yml/badge.svg)

## 功能截图

以下截图均为真实浏览器交互操作的现场截取（点击、输入、下单、支付、弹窗通知）。图片经 jsDelivr CDN 加速（国内网络可直接加载）：

<!-- 截图链接固定到提交 f2ed5ac；若以后重拍截图，请把链接里的 hash 同步为新提交 -->

| # | 截图 | 说明 |
|---|------|------|
| 01 | ![首页](https://cdn.jsdelivr.net/gh/Wyy520-create/TideMarket@f2ed5aca3f846037fcf295008928a5965b7f362c/docs/screenshots/01-home.jpeg) | 首页商品列表：分页、分类筛选、库存紧张标记 |
| 02 | ![搜索](https://cdn.jsdelivr.net/gh/Wyy520-create/TideMarket@f2ed5aca3f846037fcf295008928a5965b7f362c/docs/screenshots/02-search.jpeg) | 关键词搜索"索尼"命中商品 |
| 03 | ![商品详情](https://cdn.jsdelivr.net/gh/Wyy520-create/TideMarket@f2ed5aca3f846037fcf295008928a5965b7f362c/docs/screenshots/03-detail.jpeg) | 详情页：价格、库存、卖家、浏览次数 |
| 04 | ![登录](https://cdn.jsdelivr.net/gh/Wyy520-create/TideMarket@f2ed5aca3f846037fcf295008928a5965b7f362c/docs/screenshots/04-login.jpeg) | 未登录点击购买被引导至登录页 |
| 05 | ![登录回跳](https://cdn.jsdelivr.net/gh/Wyy520-create/TideMarket@f2ed5aca3f846037fcf295008928a5965b7f362c/docs/screenshots/05-login-back-detail.jpeg) | 登录后自动跳回刚才的商品详情页 |
| 06 | ![待支付订单](https://cdn.jsdelivr.net/gh/Wyy520-create/TideMarket@f2ed5aca3f846037fcf295008928a5965b7f362c/docs/screenshots/06-order-pending.jpeg) | 下单成功生成待支付订单，15 分钟支付倒计时 |
| 07 | ![模拟收银台](https://cdn.jsdelivr.net/gh/Wyy520-create/TideMarket@f2ed5aca3f846037fcf295008928a5965b7f362c/docs/screenshots/07-pay-modal.jpeg) | 模拟收银台弹窗 |
| 08 | ![支付成功](https://cdn.jsdelivr.net/gh/Wyy520-create/TideMarket@f2ed5aca3f846037fcf295008928a5965b7f362c/docs/screenshots/08-order-paid.jpeg) | 订单变为已支付，卖家将实时收到通知 |
| 09 | ![实时通知](https://cdn.jsdelivr.net/gh/Wyy520-create/TideMarket@f2ed5aca3f846037fcf295008928a5965b7f362c/docs/screenshots/09-ws-notify.jpeg) | 卖家页面实时弹出 WebSocket 通知"商品被拍下" |
| 10 | ![通知中心](https://cdn.jsdelivr.net/gh/Wyy520-create/TideMarket@f2ed5aca3f846037fcf295008928a5965b7f362c/docs/screenshots/10-notifications.jpeg) | 通知中心：拍下/支付/取消/超时全记录 |
| 11 | ![发布商品](https://cdn.jsdelivr.net/gh/Wyy520-create/TideMarket@f2ed5aca3f846037fcf295008928a5965b7f362c/docs/screenshots/11-publish.jpeg) | 发布闲置：填写信息 + 真实图片上传 |
| 12 | ![发布成功](https://cdn.jsdelivr.net/gh/Wyy520-create/TideMarket@f2ed5aca3f846037fcf295008928a5965b7f362c/docs/screenshots/12-publish-success.jpeg) | 提交后进入审核队列，通过后自动上架 |
| 13 | ![后台审核](https://cdn.jsdelivr.net/gh/Wyy520-create/TideMarket@f2ed5aca3f846037fcf295008928a5965b7f362c/docs/screenshots/13-admin-review.jpeg) | 管理后台：数据统计 + 审核队列 + 用户角色 |
| 14 | ![审核通过](https://cdn.jsdelivr.net/gh/Wyy520-create/TideMarket@f2ed5aca3f846037fcf295008928a5965b7f362c/docs/screenshots/14-admin-approved.jpeg) | 点击通过后队列清空，卖家收到实时通知 |
| 15 | ![上架可见](https://cdn.jsdelivr.net/gh/Wyy520-create/TideMarket@f2ed5aca3f846037fcf295008928a5965b7f362c/docs/screenshots/15-product-listed.jpeg) | 审核通过的商品立刻可以被搜索到 |

## 技术栈

| 层 | 选型 |
|---|------|
| 后端 | Python 3.12 · FastAPI · SQLAlchemy 2.0（异步）· Pydantic v2 |
| 数据库 | PostgreSQL 16（asyncpg 异步驱动） |
| 缓存 / 队列 | Redis 7（缓存 + 库存原子扣减 + 通知缓存） |
| 异步任务 | arq（每分钟扫描超时订单，自动关单回补库存） |
| 实时通道 | 原生 WebSocket（`/ws`，断线指数退避自动重连） |
| 前端 | Vue 3 · Vite · Pinia · vue-router |
| 部署 | Docker Compose 四容器（前端 nginx / 后端 / Postgres / Redis） |
| CI | GitHub Actions（pytest 接口测试 + 前端构建 + compose 冒烟） |

## 快速开始（Docker 一键启动）

> 只需要电脑装有 Docker，不需要安装 Python / Node / PostgreSQL / Redis。

### 第一步：安装 Docker

- **Windows / Mac**：到 <https://www.docker.com/products/docker-desktop/> 下载 Docker Desktop 并安装（一路下一步即可）。
- **Ubuntu**：执行 `sudo apt install docker.io docker-compose-v2`，安装后把当前用户加入 docker 组：
  `sudo usermod -aG docker $USER`，**重新登录**后生效。

### 第二步：拉取代码并启动

```bash
git clone https://github.com/Wyy520-create/TideMarket.git
cd TideMarket
docker compose up -d --build
```

第一次启动需要构建镜像、下载依赖，耐心等待几分钟。四个容器全部就绪后，打开浏览器访问：

**<http://localhost:3201>**

检查启动状态（可选）：

```bash
docker compose ps          # 四个容器都应为 healthy / running
docker compose logs -f backend   # 查看后端日志，Ctrl+C 退出
```

### 第三步：停止与清理

```bash
docker compose down        # 停止（数据保留，下次 up 直接恢复）
docker compose down -v     # 停止并清空数据（下次启动重新初始化演示数据）
```

## 演示账号

系统启动时自动初始化三个账号和 12 件商品：

| 账号 | 密码 | 角色 | 用途 |
|------|------|------|------|
| `ahai` | `ahai123456` | 普通用户 | 买家（示例商品多为他人所售，可下单） |
| `xiaoyu` | `xiaoyu123456` | 普通用户 | 卖家（名下有相机、台灯等商品） |
| `admin` | `admin123456` | 管理员 | 进入管理后台审核商品、管理角色 |

## 推荐体验动线

1. 用 `ahai` 登录，搜索"索尼"，进入详情页点击**立即购买**下单；
2. 在"我的订单"里点击**去支付**，打开模拟收银台，**确认支付**；
3. 换一个浏览器（或隐身窗口）用 `xiaoyu` 登录——页面会**实时弹出**"商品被拍下 / 订单已支付"通知；
4. 用 `ahai` 进入"发布闲置"，填信息、传图片、**提交审核**；
5. 用 `admin` 打开"管理后台"，在审核队列里点**通过**——卖家会立刻收到上架通知，回到首页即可搜到该商品。

## 本地开发（不使用 Docker 运行应用）

数据库和 Redis 仍建议用 Docker 提供（一条命令），应用代码在本机热更新运行：

```bash
# 1. 只启动数据库与 Redis
docker compose up -d db redis

# 2. 后端（另开终端）
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
arq worker.WorkerSettings &        # 定时任务：超时关单
uvicorn app.main:app --reload --port 8000

# 3. 前端（再开一个终端）
cd frontend
npm install
npm run dev                        # 访问 http://localhost:3201
```

## 运行测试

接口与并发测试基于 pytest，需要数据库（5439）与 Redis（6399）——compose 的 db/redis 默认就是这个端口：

```bash
docker compose up -d db redis
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```

覆盖内容：认证、商品审核流、搜索、**20 并发抢 5 件库存验证不超卖**、同幂等键重复下单、支付回调重放、越权拦截、取消回补、超时关单、通知已读、RBAC 权限、WebSocket 实时推送等（19 个用例）。

## 核心设计

### 三层防超卖

1. **Redis 原子预扣**：下单先执行 `DECR stock:{id}`，结果为负立即 `INCR` 回滚并返回 409，把绝大部分超卖请求挡在数据库之外；
2. **数据库乐观锁兜底**：预扣通过后执行条件更新
   `UPDATE ... SET stock = stock - 1 WHERE id = ? AND stock >= 1`，更新失败说明库存已空，同样回补 Redis；
3. **唯一约束防重复**：订单表 `idempotency_key` 唯一索引 + 用户级去重，双击/重试/刷新只会产生一笔订单。

### 支付幂等

支付接口先查去重表（幂等键为主键）：命中说明该请求已处理过，直接返回原结果；未命中则走订单状态机——只有当前状态为 `pending` 的订单才能被条件更新为 `paid`（`UPDATE ... WHERE status = 'pending'`），并发/重放的回调至多一个成功，其余返回 409。

### 超时关单

下单即写入 15 分钟支付截止时间。arq 定时任务每分钟扫描一次：把超时的 `pending` 订单关闭为 `expired`，库存回补到 Redis 与数据库，并向买家发送"订单超时关闭"通知。

### 实时通知

买家下单/支付/取消、商品审核通过、订单超时等事件都会写入通知表，并通过 WebSocket 推送给在线用户；前端断线后按指数退避自动重连，离线期间的通知可在通知中心补收。

### 缓存策略

商品详情缓存 60 秒（后台审核变更时主动失效）；列表页实时数据不缓存；**库存永远不走缓存读**，Redis 中的库存值即唯一扣减入口，服务重启时与数据库全量对账一次。

## API 一览（节选）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` / `/api/auth/login` | 注册 / 登录（JWT） |
| GET | `/api/products` | 商品列表（分页 / 搜索 / 分类 / 排序） |
| GET | `/api/products/{id}` | 商品详情（浏览数 +1，带缓存） |
| POST | `/api/products` | 发布商品（multipart 多图上传，进入审核） |
| POST | `/api/orders` | 下单（幂等键 + 三层防超卖） |
| POST | `/api/orders/{id}/pay` | 模拟支付（状态机 + 去重表，幂等） |
| POST | `/api/orders/{id}/cancel` | 取消订单（回补库存） |
| GET | `/api/orders/mine?role=buyer|seller` | 我买到 / 我卖出的订单 |
| GET | `/api/notifications` | 通知列表（支持全部已读） |
| GET | `/ws?token=` | WebSocket 实时通知通道 |
| GET | `/api/admin/stats` | 后台统计 |
| GET/PATCH | `/api/admin/products`、`/api/admin/users/{id}/role` | 商品审核、角色管理（RBAC） |
| GET | `/api/health` | 健康检查 |

## 项目结构

```
TideMarket/
├── docker-compose.yml        # 四容器编排：db / redis / backend / frontend
├── .github/workflows/ci.yml  # CI：pytest + 前端构建 + compose 冒烟
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI 入口：lifespan、路由、/ws、静态文件
│   │   ├── models.py         # SQLAlchemy 模型（用户/商品/订单/通知/去重表）
│   │   ├── routers/          # auth / products / orders / notifications / admin
│   │   ├── services/orders.py# 下单/支付/取消/超时：三层防超卖 + 幂等状态机
│   │   ├── ws.py             # WebSocket 连接管理（按用户推送）
│   │   └── seed.py           # 演示数据初始化（幂等）
│   ├── worker.py             # arq worker：每分钟扫描超时订单
│   └── tests/                # pytest 接口、并发、WS 测试
├── frontend/
│   └── src/
│       ├── views/            # 首页/详情/登录/发布/订单/通知/后台 7 个页面
│       ├── components/       # 导航栏、商品卡、Toast
│       ├── store.js          # Pinia：登录态、未读数
│       └── ws.js             # WebSocket 连接与断线重连
└── docs/screenshots/         # 界面截图（本文档引用）
```

## 公网演示（内网穿透）

想让外网访问本机运行的服务，可以用 cpolar（或 ngrok）：

```bash
# 安装后执行，将本机 3201 端口暴露为公网地址
cpolar http 3201
```

终端会打印一个 `https://xxxx.cpolar.io` 形式的公网地址，发给任何人都能直接打开体验。

## 许可

**版权所有 (c) 2026 余阳辉（GitHub：[@Wyy520-create](https://github.com/Wyy520-create)）。保留所有权利。**

本项目采用自定义许可协议发布，核心条款如下：

- 本软件仅供**个人学习与技术交流**使用，不提供任何商业授权；
- 未经著作权人书面许可，**禁止复制、修改、反编译、再发布**本软件的全部或部分，禁止用于任何商业目的；
- 禁止删除或篡改源代码中的版权声明与署名信息；
- 本软件按"现状"提供，**不承担任何明示或默示担保**，使用风险由使用者自负。

完整协议文本见 [LICENSE](LICENSE)。
