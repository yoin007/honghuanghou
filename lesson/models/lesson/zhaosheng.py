from sendqueue import send_app_msg, send_image
from config.config import Config
async def zhaosheng_dengji(record=None):
    send_app_msg({'des': '大家齐心协力，争取把更多学生招进来！', 'thumb': 'http://b1.wcr222.top/0e2c4df62a691f11/2026/03/14/fb1bcbac21ab4badbf56f82879111632.png', 'title': '天龙2026年招生信息登记', 'url': 'https://f.wps.cn/ksform/w/write/Dcs4UBd3?logSource=custom_share_card&wechatShareCard=true&secondShareCard=true'}, record.roomid, 6, 'zhaosheng')
    file_template_path = Config().get_config("file_template", "message.yaml")["群活码"]
    template_file = "template/" + file_template_path
    send_image(template_file, record.roomid, 'zhaosheng')