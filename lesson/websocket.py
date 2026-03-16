# _*_ coding: utf-8 _*_
# WebSocket Manager for real-time messaging

from typing import Dict, List
from fastapi import WebSocket
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 活跃连接列表
        self.active_connections: List[WebSocket] = []
        # 用户ID到连接的映射
        self.user_connections: Dict[str, WebSocket] = {}
        # 房间到连接的映射
        self.room_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str = None, room: str = None):
        """接受 WebSocket 连接"""
        await websocket.accept()
        self.active_connections.append(websocket)

        if user_id:
            self.user_connections[user_id] = websocket

        if room:
            if room not in self.room_connections:
                self.room_connections[room] = []
            self.room_connections[room].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str = None, room: str = None):
        """断开 WebSocket 连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        if user_id and user_id in self.user_connections:
            del self.user_connections[user_id]

        if room and room in self.room_connections:
            if websocket in self.room_connections[room]:
                self.room_connections[room].remove(websocket)
            if not self.room_connections[room]:
                del self.room_connections[room]

    async def send_personal_message(self, message: dict, user_id: str):
        """发送个人消息"""
        if user_id in self.user_connections:
            websocket = self.user_connections[user_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending personal message: {e}")
                await self.disconnect(websocket, user_id)

    async def broadcast(self, message: dict, room: str = None):
        """广播消息"""
        if room:
            # 发送给指定房间的所有连接
            if room in self.room_connections:
                disconnected = []
                for connection in self.room_connections[room]:
                    try:
                        await connection.send_json(message)
                    except Exception as e:
                        logger.error(f"Error broadcasting to room: {e}")
                        disconnected.append(connection)
                # 清理断开的连接
                for conn in disconnected:
                    await self.disconnect(conn, room=room)
        else:
            # 发送给所有连接
            disconnected = []
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting: {e}")
                    disconnected.append(connection)
            for conn in disconnected:
                await self.disconnect(conn)

    async def send_json(self, websocket: WebSocket, message: dict):
        """发送 JSON 消息"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending JSON: {e}")

    def get_connection_count(self) -> int:
        """获取活跃连接数"""
        return len(self.active_connections)

    def get_user_count(self) -> int:
        """获取用户数"""
        return len(self.user_connections)


# 创建全局 WebSocket 管理器实例
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点"""
    user_id = None
    room = None

    # 获取用户ID和房间（从查询参数）
    try:
        # 等待客户端发送第一条消息来识别身份
        first_message = await asyncio.wait_for(websocket.receive_text(), timeout=30)
        data = json.loads(first_message)
        user_id = data.get("user_id")
        room = data.get("room")
    except asyncio.TimeoutError:
        await websocket.close(code=4001, reason="Timeout waiting for identity")
        return
    except Exception as e:
        logger.error(f"Error receiving first message: {e}")
        await websocket.close(code=4002, reason="Invalid first message")
        return

    # 连接
    await manager.connect(websocket, user_id, room)

    try:
        # 发送连接成功消息
        await manager.send_json(websocket, {
            "type": "system",
            "content": "Connected successfully",
            "user_id": user_id,
            "room": room
        })

        # 持续接收消息
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # 处理消息类型
            msg_type = message.get("type", "chat")

            if msg_type == "ping":
                # 心跳检测
                await manager.send_json(websocket, {"type": "pong"})
            elif msg_type == "chat":
                # 聊天消息
                await manager.broadcast({
                    "type": "chat",
                    "user_id": user_id,
                    "room": room,
                    "content": message.get("content", ""),
                    "timestamp": message.get("timestamp")
                }, room=room)
            elif msg_type == "broadcast":
                # 广播消息
                await manager.broadcast({
                    "type": "broadcast",
                    "user_id": user_id,
                    "content": message.get("content", ""),
                    "timestamp": message.get("timestamp")
                })

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, user_id, room)


# 便捷函数
async def notify_homework_update(class_code: str, homework_data: dict):
    """通知作业更新"""
    await manager.broadcast({
        "type": "homework_update",
        "class_code": class_code,
        "data": homework_data,
        "timestamp": datetime.now().isoformat()
    }, room=f"class_{class_code}")


async def notify_schedule_update(class_code: str, schedule_data: dict):
    """通知课表更新"""
    await manager.broadcast({
        "type": "schedule_update",
        "class_code": class_code,
        "data": schedule_data,
        "timestamp": datetime.now().isoformat()
    }, room=f"class_{class_code}")


from datetime import datetime
