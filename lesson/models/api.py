# _*_ coding: utf-8 _*_
# @Time     : 2025/5/28 19:57
# @Author   : Tech_T

from openai import OpenAI
from config.config import Config
from models.datas_api.moral.ai_model_config import get_current_model
import datetime
import os
import time
import requests
from sendqueue import send_text


class ZPAI:
    def __init__(self):
        self.api_key = Config().get_config("deepseek_key", "token.yaml")
        self.base_url = "https://api.deepseek.com"

    def ai_remind_text(self, text):
        # 调用Z-PAI的API，实现提醒功能
        now = datetime.datetime.now().strftime("%H:%M:%S")
        today = datetime.datetime.now().strftime("%Y%m%d")
        week_day = int(datetime.datetime.now().weekday()) + 1
        propmt = f"{text}\n把上面这句话按照下面的指定格式的字符串返回给我，请只返回格式化的字符串，不要其他内容。\n指定格式:定时-提醒日期和时间-提醒内容\n提醒日期和时间的格式为:YYYYMMDD HH:MM:SS\n当前日期是{today},当前时间是{now}，本周的第{str(week_day)}天，请以当前日期和当前时间正确计算提醒日期和时间，尤其是关于星期(周几)的计算(每周从周1开始，一周7天)"

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)

        response = client.chat.completions.create(
            model=get_current_model('remind_ai'),
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": propmt},
            ],
            max_tokens=1024,
            temperature=0.7,
            stream=False,
        )

        text = str(response.choices[0].message.content)
        return text


def one_day_English():
    # 原来是每日一句英语，但是api失效，更改为下面的每日一句
    url = "https://api.ahfi.cn/api/bsnts?type=text"
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.6045.160 Safari/537.36 "
    }
    # 发送GET请求
    response = requests.get(url, headers).text
    return response


def countdown_day(month, day):
    """
    日期倒计时函数
    :param target_date:
    :return:
    """
    # 获取当前日期
    today = datetime.datetime.now()

    # 设置高考日期为每年的6月7日
    college_entrance_exam_date = datetime.datetime(today.year, month, day)

    # 如果当前日期已经超过了今年的高考日期，则计算明年的高考日期
    if today > college_entrance_exam_date:
        college_entrance_exam_date = college_entrance_exam_date.replace(
            year=today.year + 1
        )

    # 计算倒计时天数
    delta = college_entrance_exam_date - today
    days_to_go = delta.days
    return days_to_go


def gk_countdown():
    """
    高考倒计时，每天一句英语
    同时发布到各班级公告，署名：数字天龙
    :return:
    """
    today = datetime.datetime.now()
    tips = one_day_English()

    gk_days = countdown_day(6, 7)
    zk_days = countdown_day(6, 13)
    
    # 判断高考年份：如果当前日期已过6月7日，则显示明年
    gk_year = today.year if today.month < 6 or (today.month == 6 and today.day <= 7) else today.year + 1
    if gk_days > 0:
        gk_tips = f"距离{str(gk_year)}年高考还有{gk_days}天!"
    elif gk_days == 0:
        gk_tips = f"今日高考，祝考试顺利，金榜题名！"
    
    # 判断中考年份：如果当前日期已过6月13日，则显示明年
    zk_year = today.year if today.month < 6 or (today.month == 6 and today.day <= 13) else today.year + 1
    if zk_days > 0:
        zk_tips = f"距离{str(zk_year)}年中考还有{zk_days}天!"
    elif zk_days == 0:
        zk_tips = f"今日中考，祝考试顺利，金榜题名！"

    msg = f"{tips}"
    msg = msg + "\n" + gk_tips + "\n" + zk_tips

    # 发送微信消息
    for r in Config().get_config("gk_remind", "lesson.yaml"):
        send_text(msg, r)
        time.sleep(1)

    # 发布到各班级公告
    from models.lesson.homework import Homework
    from models.datas_api.moral.base import get_moral_db
    from config.log import LogConfig

    log = LogConfig().get_logger()
    title = "📅 高考倒计时提醒"
    author = "数字天龙"
    content = msg + f"\n\n— {author}\n{datetime.datetime.now().strftime('%Y-%m-%d')}"

    try:
        with get_moral_db() as db:
            classes = db.query_all(
                """SELECT class_code FROM class WHERE is_active = 1"""
            )
            class_codes = [c['class_code'] for c in classes]

        with Homework() as hw:
            for class_code in class_codes:
                try:
                    hw.add_announcement(class_code, title, author, content, None)
                except Exception as e:
                    log.error(f"发布公告失败（{class_code}）：{e}")

        log.info(f"已发布高考倒计时公告到 {len(class_codes)} 个班级")
    except Exception as e:
        log.error(f"发布班级公告失败: {e}")


def ju_pai(words):
    timestamp = int(time.time())
    static_dir = Config().get_cross_platform_path("lesson_dir", "lesson.yaml")
    pic = os.path.join(static_dir, "temp", f"{timestamp}.png")
    headers = {
        "authority": "api.ahfi.cn",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.6045.160 Safari/537.36 ",
    }
    from urllib.parse import quote

    encoded_words = quote(f"欢迎{words}入群!")
    req = requests.get(
        f"https://api.ahfi.cn/api/xrjupai?msg={encoded_words}",
        headers=headers,
        verify=False,
    )
    with open(pic, "wb") as f:
        f.write(req.content)
    if req.status_code == 200:
        return pic
    else:
        return None

def bailian_req(question):
    try:
        client = OpenAI(
            api_key=Config().get_config("bailian_token", "token.yaml"),
            base_url="https://coding.dashscope.aliyuncs.com/v1",
        )
        completion = client.chat.completions.create(
            model=get_current_model('bailian_general'), 
            messages=[
                {"role": "system", "content": "你是一个有帮助的助手，需要提供精准、高效且富有洞察力的回应，随时准备协助用户处理各种任务与问题。"},
                {'role': 'user', 'content': question}
            ],
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"请求出错: {e}"


def ai_remind_text(text):
    """
    调用 bailian 模型，返回模型的回答
    :param question:
    :return:
    """
    now = datetime.datetime.now().strftime("%H:%M:%S")
    today = datetime.datetime.now().strftime("%Y%m%d")
    week_day = int(datetime.datetime.now().weekday()) + 1
    propmt = f"{text}\n把上面这句话按照下面的指定格式的字符串返回给我，请只返回格式化的字符串，不要其他内容。\n指定格式:定时-提醒日期和时间-提醒内容\n提醒日期和时间的格式为:YYYYMMDD HH:MM:SS\n当前日期是{today},当前时间是{now}，本周的第{str(week_day)}天，请以当前日期和当前时间正确计算提醒日期和时间，尤其是关于星期(周几)的计算(每周从周1开始，一周7天)"
    return bailian_req(propmt)