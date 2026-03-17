# _*_ coding: utf-8 _*_
# @Time : 2024/09/23 11:27
# @Author : Tech_T
# @python: 3.10.14

import uvicorn
import os
import json
import numpy as np
from fastapi import FastAPI, Request, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import models
import re
from wxmsg import WxMsg, MessageDB
from config.log import LogConfig
from config.config import Config
from models.manage.member import Member
import asyncio
from contextlib import asynccontextmanager
import random
from sendqueue import QueueDB, send_text
from models.task import task_start
from models.manage.manage import forward_msg
from models import datas_api
from models.lesson.lound import router as loud_router
from websocket import websocket_endpoint, manager
from utils.database import init_db_optimization
from utils.monitor import init_monitor

log = LogConfig().get_logger()
config = Config()
timer_random = config.get_config("queue_timer_random", "wechat.yaml")


class NumpyJSONResponse(JSONResponse):
    """处理 numpy 类型的 JSON 响应"""

    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=self._numpy_encoder
        ).encode("utf-8")

    @staticmethod
    def _numpy_encoder(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _consume_queue_once():
    with QueueDB() as q:
        q.__consume__()


async def consume_queue():
    while True:
        await asyncio.to_thread(_consume_queue_once)
        await asyncio.sleep(random.randint(*timer_random))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库优化
    init_db_optimization()
    # 启动时初始化监控
    init_monitor()

    # 启动时启动队列消费任务
    tasks = [
        asyncio.create_task(task_start()),  # 删除多余的逗号
        asyncio.create_task(consume_queue()),
    ]

    try:
        yield
    finally:
        # 关闭时取消所有任务
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(lifespan=lifespan, default_response_class=NumpyJSONResponse)

# 配置CORS - 从环境变量读取允许的域名
# 用逗号分隔多个域名，如: http://localhost:3333,https://example.com
cors_origins = os.getenv("CORS_ORIGINS", "")
if cors_origins:
    allowed_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
else:
    # 开发环境默认允许的源
    allowed_origins = ["http://localhost:3333", "https://localhost:3334", "http://localhost:14600", "http://172.31.24.235:3333"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# HTTPS 强制重定向（生产环境）
@app.middleware("http")
async def https_redirect(request, call_next):
    # 检查是否需要强制 HTTPS
    force_https = os.getenv("FORCE_HTTPS", "false").lower() == "true"

    if force_https and request.url.scheme == "http":
        # 获取原始主机名
        host = request.headers.get("host", "")
        # 构建 HTTPS URL
        https_url = f"https://{host}{request.url.path}"
        if request.url.query:
            https_url += f"?{request.url.query}"
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=https_url, status_code=301)

    response = await call_next(request)
    return response


# 全局异常处理中间件
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    log.error(f"Unhandled exception: {exc}", exc_info=True)
    return NumpyJSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)[:100]}
    )


# 注册路由
app.include_router(datas_api.router, prefix="/api")
app.include_router(loud_router, prefix="/api")

# WebSocket 端点
@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    await websocket_endpoint(websocket)

# WebSocket 连接状态查询
@app.get("/api/ws/status")
async def ws_status():
    return {
        "active_connections": manager.get_connection_count(),
        "user_count": manager.get_user_count()
    }


# @app.get("/api/")
# async def root():
#     return {"message": "Welcome to Class Data Display System API"}


# 添加健康检查端点
@app.get("/api/health")
async def health_check():
    from utils.monitor import get_system_status
    status = get_system_status()
    return status


# 配置静态文件目录
# 确保static目录存在
static_dir = config.get_config("lesson_dir", "lesson.yaml")
# 挂载静态文件目录
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.post("/")
async def root(request: Request):
    body = await request.json()
    log.debug(f"Received request body: {body}")
    msg = WxMsg(body)
    with MessageDB() as db:
        db.insert(msg.__to_dict__())
    log.info(msg.__str__())

    if not msg.is_self:
        asyncio.create_task(forward_msg(body))
        reply, func, msg = trigger(msg)
        if reply:
            if len(msg.content) < 50:
                aters = msg.sender if msg.is_group else ""
                reply = reply.replace('\n', '\n')
                send_text(reply, msg.roomid, aters)

        if func:
            trigger_func = getattr(models, func)
            if trigger_func:
                log.info(f"触发函数 {func}")
                asyncio.create_task(trigger_func(msg))
            else:
                log.warning(f"未找到函数 {func}, 请检查配置")

    return {"message": "success"}


def trigger(msg):
    # TODO: 1. 触发事件 注意 对特定标签的 member 进行AI_content 生成
    # TODO: 2. 违禁词检测

    with Member() as m:
        rules = m.permission_info()
        if rules:
            head = msg.content[:4].replace("！","!")
            if head == "!!!!":
                content = msg.content[4:]
                ai_pattern = ai_content(content, rules)
                msg.content = ai_pattern
            for rule in rules:
                acitvate = rule[3]  # 是否禁用
                if acitvate == 0:
                    continue
                msg_type = rule[6] if rule[6] else "all"
                pattern = rule[7] if rule[7] else ""
                keywords = rule[8].split("/") if rule[8] else []
                reply = rule[11] if rule[11] else ""
                row = {
                    "func": rule[1] if rule[1] else "",
                    "blacklist": rule[4].split("/") if rule[4] else [],
                    "whitelist": rule[5].split("/") if rule[5] else [],
                    "type": msg_type,
                    "pattern": pattern,
                    "keywords": keywords,
                    "ai_flag": rule[9],
                    "need_at": rule[10] if rule[10] else 0,
                    "reply": reply,
                }
                if msg_type != "all" and str(msg_type) != str(msg.type):
                    continue
                if row["need_at"] and not msg.is_at:
                    continue
                if msg.roomid in row["blacklist"]:
                    continue
                if row["whitelist"] != ["all"] and msg.roomid not in row["whitelist"]:
                    continue
                if row["whitelist"] != ["all"] and msg.roomid in row["whitelist"]:
                    if not re.search(row["pattern"], msg.content, re.DOTALL):
                        continue
                    return row["reply"], row["func"], msg
                if row["whitelist"] == ["all"]:
                    if not re.search(row["pattern"], msg.content, re.DOTALL):
                        continue
                    return row["reply"], row["func"], msg
    return None, None, msg


def ai_content(content, rules):
    return content

if __name__ == "__main__":
    try:
        uvicorn.run("main:app", host="0.0.0.0", port=14600, reload=True)  # dev
    except KeyboardInterrupt:
        log.info("Shutting down gracefully...")
