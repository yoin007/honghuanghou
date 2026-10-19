# -*- coding: utf-8 -*-
"""IP 广播集成：微信指令触发广播服务器(IPNBS)播放语音。

token 和终端授权范围由广播服务器侧控制（api_users.json），
本模块只维护「老师 wxid → token」映射（config/broadcast.yaml）。

指令：
    广播终端               查询自己授权范围内的终端
    广播 7 / 广播 2,3,7    引用语音消息，在指定终端播放
    广播全部               引用语音消息，在全部授权终端播放
    广播授权 老师名 token  （仅管理员）绑定老师与广播 token
    广播解绑 老师名        （仅管理员）解绑
"""
import logging
import os
import re
import shutil
import tempfile
from datetime import datetime, timedelta

import requests
import yaml
from config.config import Config
from sendqueue import send_text

logger = logging.getLogger(__name__)

_CONFIG_FILE = "broadcast.yaml"


# ---------------------------------------------------------------------------
# 配置读写
# ---------------------------------------------------------------------------

def _read_config():
    try:
        return Config().get_config_all(_CONFIG_FILE) or {}
    except Exception as e:
        logger.error(f"读取广播配置失败: {e}")
        return {}


def _write_config(data):
    path = os.path.join(Config().root_path, _CONFIG_FILE)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True)


def _get_users():
    return _read_config().get("users") or {}


def _get_token(wxid):
    user = _get_users().get(wxid)
    return user.get("token") if user else None


def _is_admin(wxid):
    admins = Config().get_config("admin_list", "wechat.yaml") or []
    return wxid in admins


# ---------------------------------------------------------------------------
# 广播服务器 API
# ---------------------------------------------------------------------------

def _base_url():
    return _read_config().get("base_url", "").rstrip("/")


def _api_get(path, token):
    return requests.get(
        f"{_base_url()}{path}",
        headers={"X-Auth-Token": token},
        timeout=10,
    )


def _api_upload_play(token, wav_path, member_ids=None, name="微信广播"):
    # 定时精度为分钟，往后推 1 分钟确保任务能立即触发
    play_at = datetime.now() + timedelta(minutes=1)
    data = {
        "token": token,
        "date": play_at.strftime("%Y-%m-%d"),
        "time": play_at.strftime("%H:%M"),
        "name": name,
        "force": "false",
    }
    if member_ids:
        data["member_ids"] = ",".join(str(i) for i in member_ids)
    with open(wav_path, "rb") as f:
        return requests.post(
            f"{_base_url()}/api/v1/upload_play",
            headers={"X-Auth-Token": token},
            data=data,
            files={"file": ("broadcast.wav", f, "audio/wav")},
            timeout=30,
        )


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _find_quoted_voice(record):
    """定位被引用的语音消息，返回 (msg_row, 错误提示)"""
    # 延迟导入避免循环依赖（与 client.py 中 down_voice 同一模式）
    from wxmsg import MessageDB

    if getattr(record, "quote_msgid", None):
        with MessageDB() as db:
            row = db.select(record.quote_msgid)
        if row and row[3] == 3:
            return row, ""
        return None, "引用的消息不是语音消息，请引用一条语音消息"

    # 兜底：引用报文未携带被引用消息 id 时，取该发送者最近一条语音消息
    with MessageDB() as db:
        row = db.select_latest_by_type(record.sender, 3)
    if row:
        return row, ""
    return None, "未找到可播放的语音消息，请先发送一条语音，再引用它发送「广播 7」"


def _reply_unauthorized(record):
    send_text("你还未开通广播权限，请联系管理员发送「广播授权 你的名字 token」", record.sender)


# ---------------------------------------------------------------------------
# 指令处理（被 main.py trigger 反射调用，record 为 WxMsg）
# ---------------------------------------------------------------------------

async def broadcast_terminals(record):
    """广播终端：查询自己授权范围内的终端"""
    token = _get_token(record.sender)
    if not token:
        _reply_unauthorized(record)
        return
    try:
        r = _api_get("/api/v1/terminals", token)
    except requests.RequestException:
        send_text("广播服务器连接失败，请稍后再试", record.sender)
        return
    if r.status_code == 403:
        send_text("你的 token 无终端查询权限，请联系广播管理员核对授权", record.sender)
        return
    if r.status_code != 200:
        send_text(f"查询终端失败（HTTP {r.status_code}）", record.sender)
        return
    data = r.json()
    if not data.get("ok"):
        send_text(f"查询终端失败：{data.get('msg', '未知错误')}", record.sender)
        return
    lines = ["📢 你的授权终端："]
    for t in data.get("terminals", []):
        status = "🟢" if t.get("online") else "⚪"
        lines.append(f"{status} {t['id']}. {t['name']}")
    lines.append("发送「广播 编号」并引用语音消息即可播放，如：广播 7")
    send_text("\n".join(lines), record.sender)


async def broadcast_voice(record):
    """广播 [编号]：引用语音消息在终端播放。无编号/全部 = 全部授权终端"""
    token = _get_token(record.sender)
    if not token:
        _reply_unauthorized(record)
        return

    # 指令在引用消息标题行，如 "广播 7 \n [引用消息] ..."
    first_line = (record.content or "").split("\n")[0]
    arg = re.sub(r"^广播", "", first_line).strip()
    if arg and "全部" not in arg:
        if not re.fullmatch(r"[0-9,\s，、]+", arg):
            send_text("指令格式：引用语音消息后发送「广播 7」或「广播全部」", record.sender)
            return
        member_ids = [int(x) for x in re.split(r"[,，、\s]+", arg) if x]
        if not member_ids:
            member_ids = None
    else:
        member_ids = None  # 不传 member_ids = 全部授权终端

    row, err = _find_quoted_voice(record)
    if not row:
        send_text(err, record.sender)
        return

    from client import down_voice

    tmpdir = tempfile.mkdtemp(prefix="broadcast_")
    wav_path = os.path.join(tmpdir, "voice.wav")
    try:
        wav_path = down_voice(row[2], wav_path)  # row[2] 为 msg_id
        if not wav_path:
            send_text("语音下载失败，请重新发送语音消息后再试", record.sender)
            return
        user_name = _get_users().get(record.sender, {}).get("name", "老师")
        try:
            r = _api_upload_play(token, wav_path, member_ids, name=f"{user_name}微信广播")
        except requests.RequestException:
            send_text("广播服务器连接失败，请稍后再试", record.sender)
            return
        if r.status_code == 403:
            send_text("所选终端不在你的授权范围，发送「广播终端」查看可用终端", record.sender)
            return
        try:
            data = r.json()
        except ValueError:
            data = {}
        if r.status_code == 200 and data.get("ok"):
            target = "、".join(map(str, member_ids)) if member_ids else "全部授权终端"
            send_text(
                f"✅ 广播任务已创建（终端：{target}），任务ID：{data.get('task_id')}，约1分钟后播放",
                record.sender,
            )
        else:
            send_text(f"广播创建失败：{data.get('msg') or f'HTTP {r.status_code}'}", record.sender)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


async def broadcast_bind(record):
    """广播授权 老师名 token（仅管理员）：绑定老师与广播 token"""
    if not _is_admin(record.sender):
        return
    first_line = (record.content or "").split("\n")[0].strip()
    m = re.match(r"^广播授权\s+(\S+)\s+(\S+)", first_line)
    if not m:
        send_text("指令格式：广播授权 老师名 token", record.sender)
        return
    name, token = m.group(1), m.group(2)

    from utils.teacher_db import get_teacher_by_name

    teacher = get_teacher_by_name(name)
    if not teacher or not teacher.get("wxid"):
        send_text(f"未找到教师「{name}」或其微信ID未登记，请先在教师管理中绑定微信", record.sender)
        return

    # 校验 token 在广播服务器侧有效
    try:
        r = _api_get("/api/v1/terminals", token)
    except requests.RequestException:
        send_text("广播服务器连接失败，无法校验 token，请稍后再试", record.sender)
        return
    if r.status_code in (401, 403):
        send_text("token 校验失败：广播服务器拒绝该 token，请核对后重试", record.sender)
        return

    cfg = _read_config()
    users = cfg.get("users") or {}
    users[teacher["wxid"]] = {"name": name, "token": token}
    cfg["users"] = users
    _write_config(cfg)
    send_text(f"✅ 已授权 {name} 使用广播", record.sender)


async def broadcast_unbind(record):
    """广播解绑 老师名（仅管理员）：移除老师的广播授权"""
    if not _is_admin(record.sender):
        return
    first_line = (record.content or "").split("\n")[0].strip()
    m = re.match(r"^广播解绑\s+(\S+)", first_line)
    if not m:
        send_text("指令格式：广播解绑 老师名", record.sender)
        return
    name = m.group(1)

    from utils.teacher_db import get_teacher_by_name

    teacher = get_teacher_by_name(name)
    if not teacher or not teacher.get("wxid"):
        send_text(f"未找到教师「{name}」", record.sender)
        return

    cfg = _read_config()
    users = cfg.get("users") or {}
    if teacher["wxid"] not in users:
        send_text(f"{name} 未绑定广播 token", record.sender)
        return
    del users[teacher["wxid"]]
    cfg["users"] = users
    _write_config(cfg)
    send_text(f"✅ 已解除 {name} 的广播授权", record.sender)
