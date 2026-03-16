import requests
import json
import logging
import os
from config.config import Config

logger = logging.getLogger(__name__)
config = Config()
feishu_config = config.get_config("feishu", "token.yaml")

APP_ID = feishu_config.get("app_id", "")
APP_SECRET = feishu_config.get("app_secret", "")
USER_ID = feishu_config.get("user_id", "")
API_BASE = "https://open.feishu.cn/open-apis"
class FeishuClient:
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token = None
        self._token_expire = 0
    
    def _get_token(self) -> str:
        import time
        if self._token and time.time() < self._token_expire - 300:
            return self._token
        
        url = f"{API_BASE}/auth/v3/tenant_access_token/internal"
        resp = requests.post(url, json={
            "app_id": self.app_id,
            "app_secret": self.app_secret
        })
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"获取 token 失败: {data}")
        
        self._token = data["tenant_access_token"]
        self._token_expire = data.get("expire", 7200)
        return self._token
    
    def upload_file(self, file_path: str) -> str:
        token = self._get_token()
        url = f"{API_BASE}/im/v1/files"
        
        with open(file_path, "rb") as f:
            files = {"file": f}
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.post(url, files=files, headers=headers)
        
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"上传文件失败: {data}")
        
        return data["data"]["file_key"]
    
    def send_message(self, receive_id: str, msg_type: str, file_key: str) -> str:
        token = self._get_token()
        url = f"{API_BASE}/im/v1/messages"
        
        payload = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": json.dumps({"file_key": file_key})
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        resp = requests.post(url, json=payload, headers=headers)
        data = resp.json()
        if data.get("code") != 0:
            raise Exception(f"发送消息失败: {data}")
        
        return data["data"]["message_id"]
def send_file(client: FeishuClient, file_path: str, user_id: str):
    file_key = client.upload_file(file_path)
    
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        msg_type = "image"
    elif ext in [".mp3", ".wav", ".aac", ".m4a", ".mp4", ".avi", ".mov"]:
        msg_type = "media"
    else:
        msg_type = "file"
    
    message_id = client.send_message(user_id, msg_type, file_key)
    logger.info(f"发送成功! message_id: {message_id}")

if __name__ == "__main__":
    client = FeishuClient(APP_ID, APP_SECRET)
    send_file(client, "temp.xlsx", USER_ID)