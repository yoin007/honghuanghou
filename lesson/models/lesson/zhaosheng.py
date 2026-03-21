import os
import time
import re
import asyncio
from sendqueue import send_app_msg, send_image, send_text
from config.config import Config
from models.lesson.lesson import Lesson
from models.lesson.generate_qr import create_qr_code_v2


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
    create_qr_code_v2(
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