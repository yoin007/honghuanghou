# -*- coding: utf-8 -*-
"""
IP 广播模块（models/broadcast）单元测试

覆盖：配置读写、指令解析、各分支回复（未授权/无引用/403/成功）。
广播服务器与微信发送全部 mock，不触网。
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import broadcast
from wxmsg import WxMsg


def make_record(content="", sender="wxid_teacher1", quote_msgid=None):
    class FakeMsg:
        pass

    msg = FakeMsg()
    msg.content = content
    msg.sender = sender
    msg.quote_msgid = quote_msgid
    return msg


@pytest.fixture
def sent(monkeypatch):
    """捕获 send_text 的回复内容"""
    messages = []
    monkeypatch.setattr(broadcast, "send_text", lambda text, receiver: messages.append(text))
    return messages


@pytest.fixture
def config_state(monkeypatch):
    """把 broadcast.yaml 读写重定向到内存 dict"""
    state = {"base_url": "http://192.168.20.1:5000", "users": {}}
    monkeypatch.setattr(broadcast, "_read_config", lambda: dict(state))
    monkeypatch.setattr(broadcast, "_write_config", lambda data: state.update(data))
    return state


def fake_response(status=200, payload=None):
    class R:
        status_code = status

        def json(self):
            return payload if payload is not None else {}

    return R()


def patch_teacher_lookup(monkeypatch, wxid="wxid_teacher1"):
    """broadcast_bind/unbind 内部 from utils.teacher_db import，需在 sys.modules 层打补丁"""
    fake_teacher_db = type(
        "M",
        (),
        {"get_teacher_by_name": staticmethod(lambda name: {"name": name, "wxid": wxid})},
    )
    monkeypatch.setitem(sys.modules, "utils.teacher_db", fake_teacher_db)


class TestConfig:
    def test_get_token(self, config_state):
        config_state["users"] = {"wxid_teacher1": {"name": "张三", "token": "tok123"}}
        assert broadcast._get_token("wxid_teacher1") == "tok123"
        assert broadcast._get_token("wxid_unknown") is None

    async def test_bind_writes_config(self, config_state, sent, monkeypatch):
        patch_teacher_lookup(monkeypatch)
        monkeypatch.setattr(broadcast, "_is_admin", lambda wxid: True)
        monkeypatch.setattr(
            broadcast, "_api_get", lambda path, token: fake_response(200, {"ok": True})
        )

        await broadcast.broadcast_bind(make_record("广播授权 张三 tok123", sender="wxid_admin"))
        assert config_state["users"]["wxid_teacher1"]["token"] == "tok123"
        assert any("已授权" in m for m in sent)

    async def test_bind_rejects_invalid_token(self, config_state, sent, monkeypatch):
        patch_teacher_lookup(monkeypatch)
        monkeypatch.setattr(broadcast, "_is_admin", lambda wxid: True)
        monkeypatch.setattr(broadcast, "_api_get", lambda path, token: fake_response(403, {}))

        await broadcast.broadcast_bind(make_record("广播授权 张三 badtok", sender="wxid_admin"))
        assert config_state["users"] == {}
        assert any("校验失败" in m for m in sent)

    async def test_bind_non_admin_ignored(self, config_state, sent, monkeypatch):
        monkeypatch.setattr(broadcast, "_is_admin", lambda wxid: False)

        await broadcast.broadcast_bind(make_record("广播授权 张三 tok", sender="wxid_teacher1"))
        assert config_state["users"] == {}
        assert sent == []


class TestBroadcastTerminals:
    async def test_unauthorized(self, config_state, sent):
        await broadcast.broadcast_terminals(make_record("广播终端"))
        assert any("未开通广播权限" in m for m in sent)

    async def test_lists_terminals(self, config_state, sent, monkeypatch):
        config_state["users"] = {"wxid_teacher1": {"name": "张三", "token": "tok"}}
        monkeypatch.setattr(
            broadcast,
            "_api_get",
            lambda path, token: fake_response(
                200, {"ok": True, "terminals": [{"id": 7, "name": "监听音箱", "online": True}]}
            ),
        )

        await broadcast.broadcast_terminals(make_record("广播终端"))
        assert any("7. 监听音箱" in m for m in sent)

    async def test_403(self, config_state, sent, monkeypatch):
        config_state["users"] = {"wxid_teacher1": {"name": "张三", "token": "tok"}}
        monkeypatch.setattr(broadcast, "_api_get", lambda path, token: fake_response(403, {}))

        await broadcast.broadcast_terminals(make_record("广播终端"))
        assert any("无终端查询权限" in m for m in sent)


class TestBroadcastVoice:
    def _patch_voice(self, monkeypatch):
        """mock 消息库与语音下载，返回收集上传参数的 dict"""
        uploaded = {}

        class FakeDB:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def select(self, msg_id):
                # 消息表结构: (id, wxid, msg_id, type, sender, roomid, content, thumb, ext, ...)
                return (1, "bot", "voice_msg_1", 3, "wxid_teacher1", "", "[语音消息]", "", "http://x/a.mp3", 0, 0, 0, 0)

            def select_latest_by_type(self, sender, msg_type):
                return self.select("voice_msg_1")

        monkeypatch.setitem(sys.modules, "wxmsg", type("M", (), {"MessageDB": FakeDB}))

        def fake_down_voice(msg_id, dst_path=""):
            with open(dst_path, "wb") as f:
                f.write(b"RIFF")
            return dst_path

        monkeypatch.setitem(
            sys.modules, "client", type("C", (), {"down_voice": staticmethod(fake_down_voice)})
        )

        def fake_upload_play(token, wav_path, member_ids=None, name=""):
            uploaded.update(token=token, member_ids=member_ids, name=name)
            return fake_response(200, {"ok": True, "task_id": 1574})

        monkeypatch.setattr(broadcast, "_api_upload_play", fake_upload_play)
        return uploaded

    async def test_unauthorized(self, config_state, sent):
        await broadcast.broadcast_voice(make_record("广播 7", quote_msgid="x"))
        assert any("未开通广播权限" in m for m in sent)

    async def test_no_voice_found(self, config_state, sent, monkeypatch):
        config_state["users"] = {"wxid_teacher1": {"name": "张三", "token": "tok"}}

        class EmptyDB:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def select(self, msg_id):
                return None

            def select_latest_by_type(self, sender, msg_type):
                return None

        monkeypatch.setitem(sys.modules, "wxmsg", type("M", (), {"MessageDB": EmptyDB}))

        await broadcast.broadcast_voice(make_record("广播 7", quote_msgid=None))
        assert any("语音" in m for m in sent)

    async def test_quoted_not_voice(self, config_state, sent, monkeypatch):
        config_state["users"] = {"wxid_teacher1": {"name": "张三", "token": "tok"}}

        class TextDB:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def select(self, msg_id):
                return (1, "bot", msg_id, 1, "wxid_teacher1", "", "你好", "", "", 0, 0, 0, 0)  # type=1 文本

            def select_latest_by_type(self, sender, msg_type):
                return None

        monkeypatch.setitem(sys.modules, "wxmsg", type("M", (), {"MessageDB": TextDB}))

        await broadcast.broadcast_voice(make_record("广播 7 \n [引用消息] 张三: 你好", quote_msgid="text_1"))
        assert any("不是语音消息" in m for m in sent)

    async def test_play_with_ids(self, config_state, sent, monkeypatch):
        config_state["users"] = {"wxid_teacher1": {"name": "张三", "token": "tok"}}
        uploaded = self._patch_voice(monkeypatch)

        record = make_record("广播 2,3,7 \n [引用消息] 张三: [语音消息]", quote_msgid="voice_msg_1")
        await broadcast.broadcast_voice(record)
        assert uploaded["member_ids"] == [2, 3, 7]
        assert uploaded["token"] == "tok"
        assert any("任务ID：1574" in m for m in sent)

    async def test_play_all_when_blank(self, config_state, sent, monkeypatch):
        config_state["users"] = {"wxid_teacher1": {"name": "张三", "token": "tok"}}
        uploaded = self._patch_voice(monkeypatch)

        record = make_record("广播全部 \n [引用消息] 张三: [语音消息]", quote_msgid="voice_msg_1")
        await broadcast.broadcast_voice(record)
        assert uploaded["member_ids"] is None  # 不传 = 全部授权终端
        assert any("全部授权终端" in m for m in sent)

    async def test_play_403(self, config_state, sent, monkeypatch):
        config_state["users"] = {"wxid_teacher1": {"name": "张三", "token": "tok"}}
        self._patch_voice(monkeypatch)
        monkeypatch.setattr(
            broadcast, "_api_upload_play", lambda *a, **k: fake_response(403, {})
        )

        record = make_record("广播 99 \n [引用消息] 张三: [语音消息]", quote_msgid="voice_msg_1")
        await broadcast.broadcast_voice(record)
        assert any("授权范围" in m for m in sent)

    async def test_junk_arg_rejected(self, config_state, sent):
        config_state["users"] = {"wxid_teacher1": {"name": "张三", "token": "tok"}}

        await broadcast.broadcast_voice(make_record("广播 abc", quote_msgid="x"))
        assert any("指令格式" in m for m in sent)


class TestWxMsgQuote:
    def test_quote_msgid_extracted(self):
        body = {
            "wechatid": "bot",
            "friendid": "wxid_teacher1",
            "issend": "false",
            "content": {
                "title": "广播 7",
                "displayName": "张三",
                "content": "[语音消息]",
                "svrid": "voice_msg_1",
            },
            "contenttype": 22,
            "msgsvrid": "quote_msg_1",
            "sender": "wxid_teacher1",
        }
        msg = WxMsg(body)
        assert msg.quote_msgid == "voice_msg_1"
        assert "广播 7" in msg.content

    def test_quote_msgid_default_none(self):
        body = {
            "wechatid": "bot",
            "friendid": "wxid_teacher1",
            "issend": "false",
            "content": "你好",
            "contenttype": 1,
            "msgsvrid": "msg_1",
            "sender": "wxid_teacher1",
        }
        msg = WxMsg(body)
        assert msg.quote_msgid is None
