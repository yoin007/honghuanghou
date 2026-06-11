# _*_ coding: utf-8 _*_
# @Time: 2025/06/03 19:21
# @Author: Tech_T

from config.config import Config
from sendqueue import send_text, send_image
from models.manage.member import Member
from models.api import ju_pai
import json
import requests
import asyncio
from client import Client
from collections import defaultdict


async def forward_msg(msg):
    urls = Config().get_config("forward_url", "message.yaml")
    if not urls or len(urls) == 0:
        return
    payload = json.dumps(msg)
    headers = {"User-Agent": "tech_t", "Content-Type": "application/json"}
    for url in urls:
        try:
            response = await asyncio.to_thread(
                requests.request, "POST", url, headers=headers, data=payload
            )
            if response:
                return response
        except Exception:
            pass
        await asyncio.sleep(1)


async def command_manul(record):
    """
    命令帮助
    :param record: 命令记录
    :return: 命令帮助
    """
    content = record.content.replace("？", "?").replace("?", "")
    if content == "指令":
        command = "command_manul"
    elif content == "网络":
        command = "network_manul"
    else:
        return
    command_list = Config().get_config(command)
    tips = "当前指令列表：\n"
    print(command)
    cnt = 1
    for key in command_list:
        tips += str(cnt) + ". " + key + "\n"
        cnt += 1
    send_text(tips, record.roomid)


async def welcome_msg(record):
    """
    欢迎消息
    """
    roomid = record.roomid
    msgs = Config().get_config("welcome_msg", "message.yaml")
    try:
        msg = msgs[roomid]
        send_text(msg, roomid)
    except:
        pass


async def say_hi_qun(record: any):
    """
    新人入群欢迎，小黄人举牌
    """
    alias = ""
    member = record.ext["members"][0]
    with Member() as m:
        remarks = m.wxid_remark(member)
        if remarks:
            alias = remarks[1]
    if not alias:
        if "加入了群聊" in record.content:
            s_list = record.content.split('"')
            alias = s_list[-2]
        if "通过扫描" in record.content:
            s_list = record.content.split('"')
            alias = s_list[1]
    if alias:
        img = ju_pai(alias)
        if img:
            pic_path = img[len(Config().get_cross_platform_path("lesson_dir", "lesson.yaml")) :].replace("\\", "/")
            send_image(pic_path, record.roomid, "manage")
            return True


async def invite_chatroom_member(record: any):
    """
    邀请入群
    """
    text = record.content.replace("#", "").replace(" ", "")
    invite_rooms = Config().get_config("invite_rooms", "message.yaml")
    chatrooms = Config().get_config("qrcode_git", "message.yaml")
    try:
        if "可乐" in record.content or "招生群" in record.content:
            roomid = chatrooms[invite_rooms[text]]
        else:
            roomid = invite_rooms[text]
        c = Client()
        c.group_manage(roomid, record.sender, 2)
        return True
    except:
        return False


# 模块名称映射（英文 -> 中文）
MODULE_NAMES = {
    "inout": "请假管理",
    "lesson": "教学管理",
    "network": "网络管理",
    "manage": "系统管理",
    "daily": "日常管理",
    "application": "应用管理",
    "parking": "停车管理",
    "api": "API接口",
    "basic": "基础功能",
    "member": "会员管理",
    "notes": "笔记管理",
    "task": "任务管理",
    "zhaosheng": "招生管理",
    "zhipu": "智谱AI",
}


async def view_rules(record):
    """
    查看规则列表和详情
    - 规则：显示所有规则列表
    - 规则 AI：只显示 AI 规则
    - 规则 模块：显示所有模块列表
    - 规则 模块名：按模块筛选
    - 规则-id：显示单条规则详情
    """
    content = record.content.strip()

    # 规则命令
    content = content.replace("规则", "").strip()

    # 规则 模块：显示模块列表
    if content == "模块":
        _send_modules_list(record.roomid)
        return

    with Member() as m:
        # 获取所有激活的规则
        m.__cursor__.execute("""
            SELECT id, func, func_name, module, pattern, keywords,
                   ai_flag, level, example, notes
            FROM permission
            WHERE activate = 1
            ORDER BY module, id
        """)
        rules = m.__cursor__.fetchall()

    if not rules:
        send_text("暂无规则", record.roomid)
        return

    # 解析命令
    if content == "":
        # 规则：显示所有规则
        _send_rules_list(record.roomid, rules, ai_only=False)
    elif content.upper() == "AI":
        # 规则 AI：只显示 AI 规则
        _send_rules_list(record.roomid, rules, ai_only=True)
    elif content.startswith("-") and content[1:].isdigit():
        # 规则-id：显示详情
        rule_id = int(content[1:])
        _send_rule_detail(record.roomid, rules, rule_id)
    else:
        # 规则 模块名：按模块筛选
        _send_rules_list(record.roomid, rules, module=content)


def _send_rules_list(roomid, rules, ai_only=False, module=None):
    """发送规则列表"""
    # 按模块分组
    grouped = defaultdict(list)
    for rule in rules:
        rule_id, func, func_name, mod, _, _, ai_flag, _, _, _ = rule
        if ai_only and ai_flag != 1:
            continue
        if module and mod != module:
            continue
        grouped[mod].append((rule_id, func, func_name, ai_flag))

    # 构建输出
    if ai_only:
        header = "🤖 AI 规则列表"
    else:
        header = "📋 规则列表"

    total = sum(len(v) for v in grouped.values())
    if total == 0:
        if ai_only:
            send_text("暂无 AI 规则", roomid)
        elif module:
            send_text(f"未找到模块 '{module}' 的规则", roomid)
        else:
            send_text("暂无规则", roomid)
        return

    lines = [f"{header} (共 {total} 条)\n"]

    for mod in sorted(grouped.keys()):
        mod_rules = grouped[mod]
        mod_name = MODULE_NAMES.get(mod, mod)
        lines.append(f"【{mod}】{mod_name}")
        for rule_id, func, func_name, ai_flag in mod_rules:
            ai_mark = "🤖" if ai_flag == 1 else "  "
            lines.append(f"  {ai_mark} [{rule_id}] {func} | {func_name}")
        lines.append("")

    lines.append("💡 输入 \"规则-id\" 查看详情")
    if not ai_only:
        lines.append("💡 输入 \"规则 AI\" 查看 AI 规则")

    send_text("\n".join(lines), roomid)


def _send_rule_detail(roomid, rules, rule_id):
    """发送规则详情"""
    for rule in rules:
        r_id, func, func_name_cn, module, pattern, keywords, ai_flag, level, example, notes = rule
        if r_id == rule_id:
            ai_text = "✅" if ai_flag == 1 else "❌"
            kw_text = keywords if keywords else "(无)"
            ex_text = example if example else "(无)"
            notes_text = notes if notes else "(无)"
            mod_name = MODULE_NAMES.get(module, module)

            lines = [
                f"📌 规则详情: [{r_id}] {func}",
                "",
                f"功能名称：{func_name_cn}",
                f"所属模块：{module} ({mod_name})",
                f"权限等级：{level}",
                f"AI 支持：{ai_text}",
                "",
                f"匹配模式：{pattern}",
                f"关键词：{kw_text}",
                "",
                f"使用示例：",
                ex_text,
                "",
                f"备注：{notes_text}"
            ]
            send_text("\n".join(lines), roomid)
            return

    send_text(f"未找到规则: {rule_id}", roomid)


def _send_modules_list(roomid):
    """发送模块列表"""
    with Member() as m:
        # 获取所有激活规则的模块统计
        m.__cursor__.execute("""
            SELECT module, COUNT(*) as count, SUM(CASE WHEN ai_flag = 1 THEN 1 ELSE 0 END) as ai_count
            FROM permission
            WHERE activate = 1
            GROUP BY module
            ORDER BY module
        """)
        modules = m.__cursor__.fetchall()

    if not modules:
        send_text("暂无模块", roomid)
        return

    total_rules = 0
    total_ai = 0
    lines = ["📦 模块列表\n"]

    for mod, count, ai_count in modules:
        mod_name = MODULE_NAMES.get(mod, mod)
        ai_text = f" (AI: {ai_count})" if ai_count > 0 else ""
        lines.append(f"【{mod}】{mod_name} - {count} 条规则{ai_text}")
        total_rules += count
        total_ai += ai_count

    lines.append(f"\n共 {len(modules)} 个模块，{total_rules} 条规则，{total_ai} 条 AI 规则")
    lines.append("\n💡 输入 \"规则 模块名\" 查看指定模块的规则")

    send_text("\n".join(lines), roomid)


async def complete_pending_record_wx(msg):
    """
    微信端完善待完善记录

    消息格式：
    待完善记录：123
    学生1：张三
    学生2：李四
    任课教师：王老师
    时间：2026-06-10 08:00
    事件类型：迟到
    备注：...

    正则匹配记录ID和学生姓名，验证后完善记录
    """
    import re
    import json
    from sendqueue import send_text
    from models.datas_api.moral.base import get_moral_db
    from models.datas_api.moral.pending_record import _ensure_pending_record_table
    from models.datas_api.moral.pending_record import API_PENDING_COMPLETE_WX

    content = msg.content.strip()
    roomid = msg.roomid

    # 解析记录ID
    match_id = re.search(r'待完善记录[：:]\s*(\d+)', content)
    if not match_id:
        send_text("格式错误：未找到记录ID", roomid)
        return

    record_id = int(match_id.group(1))

    # 解析学生姓名
    student_names = []
    for m in re.finditer(r'学生\d+[：:]\s*(.+)', content):
        name = m.group(1).strip()
        if name:
            student_names.append(name)

    if not student_names:
        send_text(f"未找到学生姓名，请按格式填写：\n待完善记录：{record_id}\n学生1：姓名\n学生2：姓名", roomid)
        return

    # 调用后端 API 逻辑完善记录
    try:
        with get_moral_db() as db:
            _ensure_pending_record_table(db)

            pending = db.query_one("SELECT * FROM pending_daily_record WHERE id = ?", (record_id,))
            if not pending:
                send_text(f"记录 {record_id} 不存在", roomid)
                return
            if pending["is_completed"]:
                send_text(f"记录 {record_id} 已完善", roomid)
                return

            class_id = pending["class_id"]
            class_students = db.query_all(
                "SELECT student_id, name FROM student WHERE class_id = ? AND status = '在校'",
                (class_id,)
            )
            name_to_id = {s["name"]: s["student_id"] for s in class_students}

            student_ids = []
            not_found = []
            for name in student_names:
                if name in name_to_id:
                    student_ids.append(name_to_id[name])
                else:
                    matched = [nid for n, nid in name_to_id.items() if name in n]
                    if len(matched) == 1:
                        student_ids.append(matched[0])
                    else:
                        not_found.append(name)

            if not_found:
                send_text(f"以下学生在班级中未找到: {', '.join(not_found)}，请检查姓名是否正确", roomid)
                return

            if len(student_ids) != pending["student_count"]:
                send_text(f"学生数不匹配，需要 {pending['student_count']} 名，已匹配 {len(student_ids)} 名", roomid)
                return

        # 通过内部 API 调用完善
        from models.datas_api.moral.pending_record import PendingRecordCompleteWx
        import requests as http_requests

        # 直接调用后端逻辑
        from models.datas_api.moral.evaluation import calculate_evaluation
        from models.datas_api.moral.escalation import check_and_trigger_escalation
        from models.datas_api.moral.base import get_student_class_snapshot, log_operation
        from datetime import datetime, timezone, timedelta

        GMT8 = timezone(timedelta(hours=8))

        with get_moral_db() as db:
            event = db.query_one("SELECT * FROM daily_event_type WHERE event_id = ?", (pending["event_id"],))
            if not event:
                send_text("事件类型不存在", roomid)
                return

            semester_id = pending["semester_id"]
            grade_id = pending["grade_id"]
            record_date = pending["record_date"]

            combined_remark = ""
            if pending["teacher_name"]:
                combined_remark += f"任课教师：{pending['teacher_name']}"
            if pending["remark"]:
                if combined_remark:
                    combined_remark += "；"
                combined_remark += pending["remark"]

            current_time = datetime.now(GMT8).replace(tzinfo=None)
            created_count = 0
            for sid in student_ids:
                student_info = get_student_class_snapshot(db, sid)
                if not student_info:
                    continue
                db.execute(
                    """INSERT INTO student_daily_record
                    (student_id, event_id, semester_id, record_date, class_id, grade_id, score, remark, recorder)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (sid, pending["event_id"], semester_id, record_date,
                     class_id, grade_id, event["score"], combined_remark,
                     pending.get("recorder") or "wx_complete")
                )
                new_record_id = db.lastrowid()
                created_count += 1

                if event["event_type"] == 2:
                    try:
                        rd = datetime.strptime(record_date, "%Y-%m-%d %H:%M")
                    except:
                        rd = current_time
                    check_and_trigger_escalation(
                        db=db, student_id=sid, event_id=pending["event_id"],
                        record_id=new_record_id, record_date=rd, semester_id=semester_id
                    )
                calculate_evaluation(db, sid, semester_id, class_id, grade_id)

            db.execute(
                """UPDATE pending_daily_record SET is_completed = 1, student_ids = ?, updated_at = datetime('now', 'localtime')
                WHERE id = ?""",
                (json.dumps(student_ids, ensure_ascii=False), record_id)
            )

        send_text(f"记录 {record_id} 已完善，创建了 {created_count} 条日常表现记录", roomid)

    except Exception as e:
        send_text(f"完善记录失败: {str(e)[:100]}", roomid)
        import logging
