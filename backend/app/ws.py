"""WebSocket 连接管理：user_id -> {websocket}，支持多端同时在线。"""
from fastapi import WebSocket

from .security import decode_token


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[int, set[WebSocket]] = {}

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._rooms.setdefault(user_id, set()).add(ws)

    def disconnect(self, user_id: int, ws: WebSocket) -> None:
        room = self._rooms.get(user_id)
        if room and ws in room:
            room.discard(ws)
            if not room:
                self._rooms.pop(user_id, None)

    async def send_to(self, user_id: int, message: dict) -> None:
        """给某用户所有在线连接推送；连接已断开则静默清理。"""
        room = self._rooms.get(user_id)
        if not room:
            return
        dead = []
        for ws in room:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            room.discard(ws)


manager = ConnectionManager()


async def ws_authenticate(ws: WebSocket) -> int | None:
    """从查询参数取 token 鉴权；返回 user_id 或 None。"""
    token = ws.query_params.get("token", "")
    if not token:
        return None
    payload = decode_token(token)
    return payload["user_id"] if payload else None
