import os
import time
import re
import asyncio
import logging
import requests
from sendqueue import send_app_msg, send_image, send_text
from config.config import Config
from config.log import LogConfig
from models.lesson.lesson import Lesson
from models.lesson.generate_qr import create_qr_code
from utils.teacher_db import get_all_teachers
from client import Client

log = LogConfig().get_logger()
logger = logging.getLogger(__name__)


async def zhaosheng_dengji(record=None):
    send_app_msg({'des': '大家齐心协力，争取把更多学生招进来！', 'thumb': 'http://b1.wcr222.top/0e2c4df62a691f11/2026/03/14/fb1bcbac21ab4badbf56f82879111632.png', 'title': '天龙2026年招生信息登记', 'url': 'https://f.wps.cn/ksform/w/write/Dcs4UBd3?logSource=custom_share_card&wechatShareCard=true&secondShareCard=true'}, record.roomid, 6, 'zhaosheng')
    file_template_path = Config().get_config("file_template", "message.yaml")["群活码"]
    template_file = "template/" + file_template_path
    send_image(template_file, record.roomid, 'zhaosheng')


def gen_qrcode(url: str, title: str, subtitle: str = None) -> str:
    """
    生成招生二维码

    Args:
        url: 二维码链接
        title: 主标题
        subtitle: 副标题（可选）

    Returns:
        生成的二维码图片绝对路径
    """
    l = Lesson()

    # 输出路径
    timestamp = int(time.time() * 1000)
    output_path = os.path.join(l.lesson_dir, "temp", f"qr_code{timestamp}.png")

    # Logo 路径
    logo_path = os.path.join(l.lesson_dir, "template", "logo.jpg")

    # 生成二维码
    create_qr_code(
        url=url,
        title=title,
        subtitle=subtitle,
        logo_path=logo_path,
        output_path=output_path,
    )

    return output_path


async def async_gen_qrcode(record):
    """
    微信消息触发生成二维码
    支持 ai_flag=1，AI 智能解析参数

    消息格式：
    生成二维码
    $url: https://example.com
    $title: 招生报名
    $subtitle: 诚邀参与
    """
    content = record.content
    wxid = record.roomid

    # 解析参数
    url_match = re.search(r"\$url[：:]\s*(.+)", content)
    title_match = re.search(r"\$title[：:]\s*(.+)", content)
    subtitle_match = re.search(r"\$subtitle[：:]\s*(.+)", content)

    if not url_match or not title_match:
        send_text("请提供正确的参数格式：\n生成二维码\n$url: 链接\n$title: 标题\n$subtitle: 副标题(可选)", wxid)
        return

    url = url_match.group(1).strip()
    title = title_match.group(1).strip()
    subtitle = subtitle_match.group(1).strip() if subtitle_match else None

    # 在线程池中执行同步的二维码生成
    qr_path = await asyncio.to_thread(gen_qrcode, url, title, subtitle)

    # 转换为相对路径
    l = Lesson()
    pic_path = qr_path[len(l.lesson_dir):].replace("\\", "/")

    # 发送图片
    send_image(pic_path, wxid, "zhaosheng")


def yuanqi_chat(user_message: str, user_id: str = "user") -> str:
    """
    调用腾讯元器 Agent API 进行智能问答

    Args:
        user_message: 用户发送的消息内容
        user_id: 用户标识（用于多轮对话追踪）

    Returns:
        AI 回复的内容字符串
    """
    config = Config()
    try:
        yuanqi_config = config.get_config_all("token.yaml").get("yuanqi", {})
        token = yuanqi_config.get("token")
        assistant_id = yuanqi_config.get("assistant_id", "BEezC6XU8iz2")
        base_url = yuanqi_config.get("base_url", "https://yuanqi.tencent.com/openapi/v1")

        if not token or token == "<your_yuanqi_api_token>":
            logger.error("腾讯元器 API Token 未配置")
            return "智能问答服务暂未配置，请联系管理员"

        url = f"{base_url}/agent/chat/completions"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Source": "openapi"
        }

        payload = {
            "assistant_id": assistant_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_message
                        }
                    ]
                }
            ],
            "stream": False,
            "user_id": user_id
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()

        # 解析返回结果
        choices = result.get("choices", [])
        if choices and len(choices) > 0:
            content = choices[0].get("message", {}).get("content", "")
            if isinstance(content, list) and len(content) > 0:
                # 腾讯元器可能返回 content 为列表格式
                text_content = content[0].get("text", "")
                return text_content.strip() if text_content else ""
            return content.strip() if content else ""

        # 兼容其他返回格式
        data = result.get("data", {})
        if data:
            content = data.get("content", "")
            return content.strip() if content else ""

        error_msg = result.get("message", "未知错误")
        logger.error(f"腾讯元器 API 返回错误: {error_msg}")
        return f"智能问答暂时无法响应: {error_msg}"

    except requests.exceptions.Timeout:
        logger.error("腾讯元器 API 请求超时")
        return "智能问答响应超时，请稍后再试"

    except requests.exceptions.RequestException as e:
        logger.error(f"腾讯元器 API 请求异常: {e}")
        return "智能问答服务暂时不可用"

    except Exception as e:
        logger.error(f"智能问答未知错误: {e}")
        return "智能问答发生错误"


async def smart_qa(record):
    """
    智能问答功能：群聊消息触发 AI 回复

    功能说明：
    1. 消息来源群聊已在 permission 表 white_list 中配置（由 trigger 函数匹配）
    2. 检查发送者是否在排除名单内（配置文件 + 教师表）
    3. 调用腾讯元器 API 获取回复
    4. 根据 test_mode 决定发送目标：
       - test_mode=true: 发送给管理员（用于测试验证）
       - test_mode=false: 发送到群聊并 @ 原消息发送者

    Args:
        record: WxMsg 对象，包含消息信息
    """
    config = Config()

    # 1. 获取配置
    try:
        test_mode = config.get_config("smart_qa_test_mode", "wechat.yaml")
        exclude_members = config.get_config("smart_qa_exclude_members", "wechat.yaml")
        admin_wxid = config.get_config("admin", "wechat.yaml")
    except (KeyError, TypeError):
        test_mode = False
        exclude_members = []
        admin_wxid = ""

    # 2. 获取教师 wxid 列表（默认排除教师）
    teacher_wxids = set()
    try:
        teachers = get_all_teachers()
        for teacher in teachers:
            wxid = teacher.get("wxid", "")
            if wxid and wxid.strip():
                teacher_wxids.add(wxid.strip())
    except Exception as e:
        logger.warning(f"获取教师列表失败: {e}")

    # 3. 合并排除名单
    exclude_set = set(exclude_members) if exclude_members else set()
    exclude_set.update(teacher_wxids)

    # 4. 检查是否为群聊消息
    if not record.is_group:
        logger.debug("智能问答仅支持群聊消息")
        return

    # 5. 检查发送者是否在排除名单内
    if record.sender in exclude_set:
        logger.debug(f"发送者 {record.sender} 在排除名单内，不触发 AI 回复")
        return

    # 6. 检查是否为自己发送的消息（防止自回复）
    if record.is_self:
        logger.debug("不回复自己发送的消息")
        return

    # 7. 检查消息内容是否为空或特殊类型
    content = record.content
    if not content or (isinstance(content, str) and content.startswith("[")):
        logger.debug("消息内容为空或为特殊消息类型，不触发 AI 回复")
        return

    # 8. 构建用户 ID（用于多轮对话追踪）
    user_id = f"{record.sender}_{record.roomid}"

    # 9. 调用腾讯元器 API
    logger.info(f"智能问答触发: 群={record.roomid}, 发送者={record.sender}, 内容={content[:50]}")
    ai_reply = yuanqi_chat(content, user_id=user_id)
    ai_reply = ai_reply.replace("88857277", "")

    # 10. 发送回复
    if not ai_reply:
        logger.warning("智能问答无回复内容")
        return

    if test_mode:
        # 测试模式：发送给管理员，包含来源信息
        test_msg = f"[智能问答测试]\n群聊: {record.roomid}\n发送者: {record.sender}\n原消息: {content[:100]}\n\nAI回复:\n{ai_reply}"
        send_text(test_msg, admin_wxid, producer="smart_qa_test")
        logger.info(f"测试模式: 回复已发送给管理员 {admin_wxid}")
    else:
        # 正常模式：发送到群聊并 @ 发送者
        send_text(ai_reply, record.roomid, aters=record.sender, producer="smart_qa")
        logger.info(f"智能问答回复已发送到群聊 {record.roomid}")


async def get_group_qr(record):
    """
    管理员获取群二维码功能

    消息格式：群二维码52100546629@chatroom
    解析 roomid，调用 Client.group_qr() 获取二维码图片链接，发送给管理员

    Args:
        record: WxMsg 对象，包含消息信息

    流程：
    1. 解析消息提取 roomid
    2. 调用 client.group_qr(roomid) 获取二维码链接
    3. 发送二维码图片给管理员
    """
    config = Config()

    # 1. 获取管理员配置（二次验证）
    try:
        admin_list = config.get_config("admin_list", "wechat.yaml")
    except (KeyError, TypeError):
        admin_list = []

    # 2. 检查发送者权限
    sender = record.sender
    if sender not in admin_list:
        logger.debug(f"非管理员触发群二维码功能: {sender}")
        return

    # 3. 解析消息提取 roomid
    content = record.content
    pattern = r"群二维码(.+@chatroom)"
    match = re.search(pattern, content)

    if not match:
        send_text("格式错误，正确格式：群二维码<群ID>@chatroom\n例如：群二维码52100546629@chatroom", sender, producer="get_group_qr")
        logger.warning(f"群二维码消息格式错误: {content}")
        return

    roomid = match.group(1).strip()
    logger.info(f"群二维码获取请求: sender={sender}, roomid={roomid}")

    # 4. 发送处理提示
    send_text(f"正在获取群 {roomid} 的二维码，请稍候...", sender, producer="get_group_qr")

    # 5. 调用 Client.group_qr() 获取二维码链接
    client = Client()
    try:
        # group_qr 是同步阻塞函数，使用 asyncio.to_thread 包装
        qr_url = await asyncio.to_thread(client.group_qr, roomid)

        # 6. 处理结果
        if qr_url and qr_url.strip():
            # 成功获取二维码链接，发送图片
            logger.info(f"群二维码获取成功: roomid={roomid}, url={qr_url}")
            send_image(qr_url, sender, producer="get_group_qr")
        else:
            # 获取失败
            logger.error(f"群二维码获取失败: roomid={roomid}")
            send_text(f"群二维码获取失败，请检查群 ID 是否正确或群是否存在", sender, producer="get_group_qr")

    except Exception as e:
        logger.error(f"群二维码获取异常: roomid={roomid}, error={e}")
        send_text(f"群二维码获取异常: {str(e)[:100]}", sender, producer="get_group_qr")