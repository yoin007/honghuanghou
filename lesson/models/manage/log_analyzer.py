import re
import os
from collections import Counter, defaultdict
from datetime import datetime
from models.api import bailian_req
from models.application.application import lesson_dir
from models.manage.member import Member
from sendqueue import send_text, send_file
from config.config import Config
from models.lesson.lesson import Lesson

admin = Config().get_config("admin", "wechat.yaml")

DB_PATH = 'databases/member.db'

MESSAGE_TYPE_MAP = {
    0: '未知内容',
    1: '文本内容',
    2: '图片消息',
    3: '语音消息',
    4: '视频消息',
    5: '系统消息',
    6: '链接消息',
    7: '扩展的链接消息（小程序分享等），内容为xml格式，暂未使用',
    8: '文件发送',
    9: '名片',
    10: '位置信息',
    11: '红包',
    12: '转账',
    13: '小程序',
    14: '',
    15: '群管理消息',
    16: '领取红包消息',
    17: '群聊系统消息',
    18: '公众号文章',
    19: '语音通话',
    20: '视频通话',
    21: '服务通知',
    22: '引用通知',
    23: '接龙',
    24: '视频号消息',
    25: '群直播消息',
    26: '拍一拍',
    27: '分享音乐',
    28: '视频号直播',
    29: '客服号名片',
    30: '企业微信名片',
    99: '不支持的消息',
    -1: '',
}

def analyze_log(log_path):
    with open(log_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 统计收发消息总数
    received_count = len(re.findall(r'📥 收到消息', content))
    sent_count = len(re.findall(r'📤 发送消息', content))

    # 2. 统计错误日志
    error_pattern = r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}\]\s+\[.*?\]\s+\[ERROR\].*$'
    errors = [m.group(0) for m in re.finditer(error_pattern, content, re.MULTILINE)]
    unique_errors = Counter()
    error_details = []
    for err in errors:
        lines = err.strip().split('\n')
        msg = lines[0] if lines else "Unknown Error"
        unique_errors[msg] += 1
        error_details.append({
            "message": msg,
            "detail": err.strip()
        })

    # 3. 提取所有消息的详细信息
    all_messages = []
    message_blocks = re.split(r'={50,}', content)
    for block in message_blocks:
        if '📥 收到消息' not in block and '📤 发送消息' not in block:
            continue

        try:
            timestamp_str = re.search(r'(📥|📤) .*? \| (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', block).group(2)
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            
            group_match = re.search(r'📱 来源: 群聊 (.*?) \[(.*?)\]\]', block)
            if not group_match:
                continue

            group_name = group_match.group(1).strip()
            group_id = group_match.group(2).strip()

            sender_id = (re.search(r'👤 发送者: (.*)', block) or re.search(r'👤 联系人: (.*)', block)).group(1).strip()
            msg_type = int(re.search(r'📋 类型: (\d+)', block).group(1))
            content_match = re.search(r'📝 内容:\n----\n(.*?)\n----(?=\n⚙️|\n|$)', block, re.DOTALL)
            content_text = content_match.group(1).strip() if content_match else ""

            all_messages.append({
                "timestamp": timestamp,
                "group_id": group_id,
                "group_name": group_name,
                "sender_id": sender_id or "SYSTEM/BOT",
                "type": msg_type,
                "content": content_text
            })
        except (AttributeError, ValueError, IndexError) as e:
            # 跳过格式不完整的消息块
            # print(f"Skipping malformed block: {e}")
            pass

    return {
        "received": received_count,
        "sent": sent_count,
        "unique_errors": unique_errors,
        "error_details": error_details,
        "all_messages": all_messages
    }

def get_solutions_for_errors(unique_errors, error_details):
    solutions = {}
    print(f"正在分析 {len(unique_errors)} 类错误日志...")
    detail_map = {}
    for item in error_details:
        message = item.get("message")
        if message and message not in detail_map:
            detail_map[message] = item.get("detail", message)
    for err_msg, count in unique_errors.items():
        prompt = f"我的机器人日志中出现了以下错误（共出现 {count} 次），请帮我分析原因并给出解决方案：\n\n{detail_map.get(err_msg, err_msg)}"
        print(f"请求大模型分析错误: {err_msg}")
        try:
            # solution = bailian_req(prompt)
            solution = f"test"
        except Exception as e:
            solution = f"获取解决方案失败: {str(e)}"
        solutions[err_msg] = solution
    return solutions

def analyze_group_stats(all_messages):
    group_stats = defaultdict(lambda: {
        "total_msgs": 0,
        "senders": Counter(),
        "types": Counter(),
        "hourly": Counter(),
        "content_corpus": ""
    })

    for msg in all_messages:
        gid = msg['group_id']
        stats = group_stats[gid]
        stats["group_name"] = msg['group_name']
        stats["total_msgs"] += 1
        stats["senders"][msg['sender_id']] += 1
        stats["types"][MESSAGE_TYPE_MAP.get(msg['type'], '其他')] += 1
        stats["hourly"][msg['timestamp'].hour] += 1
        if msg['type'] in {1, 6, 18}:
            stats["content_corpus"] += msg['content'] + "\n"
            
    # 排序
    sorted_groups = sorted(group_stats.items(), key=lambda item: item[1]['total_msgs'], reverse=True)
    return sorted_groups

def analyze_inactive_members(group_id, active_senders):
    if not group_id:
        return None
        
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT member_wx_id, name FROM chatroom_member WHERE chat_room_id = ? AND is_deleted = 0", (group_id,))
        all_members = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        
        if not all_members:
            return f"数据库中未找到群 {group_id} 的成员信息"

        active_ids = set(active_senders.keys())
        inactive_ids = set(all_members.keys()) - active_ids
        
        return {
            "total": len(all_members),
            "active_count": len(active_ids),
            "inactive_count": len(inactive_ids),
            "silence_rate": (len(inactive_ids) / len(all_members) * 100) if all_members else 0,
            "inactive_list": [{"id": uid, "name": all_members[uid]} for uid in inactive_ids]
        }
    except ImportError:
        return "当前环境缺少 sqlite3 支持，无法分析潜水成员。"
    except Exception as e:
        return f"分析潜水成员出错: {str(e)}"

def filter_corpus(corpus, max_lines=200, max_chars=6000, min_len=6):
    lines = [line.strip() for line in corpus.splitlines() if line.strip()]
    filtered = []
    seen = set()
    current_chars = 0
    for line in lines:
        lowered = line.lower()
        if lowered in seen:
            continue
        if len(line) < min_len:
            continue
        if re.search(r'https?://|wxapp.tc.qq.com|wx\.qlogo\.cn', line):
            continue
        if re.fullmatch(r'[\W_]+', line):
            continue
        if re.fullmatch(r'\[.*\]', line):
            continue
        if current_chars + len(line) + 1 > max_chars:
            break
        filtered.append(line)
        seen.add(lowered)
        current_chars += len(line) + 1
        if len(filtered) >= max_lines:
            break
    return "\n".join(filtered)

def extract_highlights(filtered_corpus, max_items=10):
    if not filtered_corpus.strip():
        return []
    prompt = (
        "请从以下群聊记录中提取群聊精华，要求："
        "1) 输出要点列表，最多{max_items}条；"
        "2) 每条不超过200字；"
        "3) 只保留有价值的信息，不要客套话；"
        "4) 直接输出要点列表，每条以-开头。\n\n"
        "{content}"
    ).format(max_items=max_items, content=filtered_corpus)
    try:
        result = bailian_req(prompt)
    except Exception as e:
        return [f"分析失败: {e}"]
    lines = []
    for line in result.splitlines():
        line = line.strip()
        if not line:
            continue
        if not line.startswith("-"):
            line = f"- {line}"
        lines.append(line)
    return lines[:max_items]

def perform_nlp_analysis(corpus):
    filtered = filter_corpus(corpus)
    if not filtered.strip():
        return {"summary": "无文本内容可分析。", "highlights": []}
    results = {}
    results["highlights"] = extract_highlights(filtered)
    return results

def generate_report(stats, sorted_groups, target_group_ids=None, nlp_results_map=None):
    m = Member()
    report = ["# 🤖 机器人运行日志分析报告", f"**日期**: {datetime.now().strftime('%Y-%m-%d')}"]

    # 1. 流量统计
    report.append("\n## 1. 消息流量统计")
    report.append(f"- 📥 收到消息总数: `{stats['received']}`")
    report.append(f"- 📤 发送消息总数: `{stats['sent']}`")

    # 2. 错误日志汇总（只统计，不查找解决方案）
    report.append("\n## 2. 错误日志汇总")
    if not stats['unique_errors']:
        report.append("✅ 未发现错误日志。")
    else:
        total_errors = sum(stats['unique_errors'].values())
        report.append(f"- **错误种类**: `{len(stats['unique_errors'])}`")
        report.append(f"- **错误总数**: `{total_errors}`")
        report.append("\n**错误详情**:")
        for err_msg, count in list(stats['unique_errors'].items())[:10]:
            report.append(f"- `{err_msg}` (出现 {count} 次)")

    # 3. 群聊活跃度排名
    report.append("\n## 3. 群聊消息活跃度排名")
    table = ["| 排名 | 群名 | 消息数 | 发言者数 | 活跃度 |", "|:---:|:---|:---:|:---:|:---:|"]
    for i, (gid, g_stats) in enumerate(sorted_groups, 1):
        active_users = len(g_stats['senders'])
        total_msgs = g_stats['total_msgs']
        stars = '⭐' * min(5, (total_msgs // 20) + (active_users // 5))
        table.append(f"| {i} | {g_stats['group_name']} (`{gid}`) | {total_msgs} | {active_users} | {stars or '⭐'} |")
    report.extend(table)

    # 4. 目标群聊深度分析
    if target_group_ids:
        group_map = dict(sorted_groups)
        report.append("\n## 4. 目标群聊深度分析")
        for target_group_id in target_group_ids:
            target_stats = group_map.get(target_group_id)
            if not target_stats:
                continue
            
            group_nlp = (nlp_results_map or {}).get(target_group_id, {})
            group_report = generate_single_group_report(target_stats, group_nlp, target_group_id)
            report.append(f"\n{group_report}")

    return "\n".join(report)

def generate_single_group_report(group_stats, nlp_results=None, group_id=None):
    m = Member()
    if not group_id:
        group_id = group_stats.get('group_id', '未知')
    report = ["# 🤖 群聊统计报告", f"**群ID**: {group_stats.get('group_name', '未知')} (`{group_id}`)", f"**日期**: {datetime.now().strftime('%Y-%m-%d')}"]
    
    report.append("\n## 1. 消息概览")
    report.append(f"- **消息总数**: `{group_stats['total_msgs']}`")
    report.append(f"- **发言人数**: `{len(group_stats['senders'])}`")
    
    report.append("\n## 2. 发言排行 (Top 5)")
    sorted_senders = sorted(group_stats['senders'].items(), key=lambda x: x[1], reverse=True)[:5]
    table = ["| 排名 | 用户 | 消息数 |", "|:---:|:---|:---:|"]
    for i, (sender, count) in enumerate(sorted_senders, 1):
        if sender == "SYSTEM/BOT":
            display_name = "SYSTEM/BOT"
        else:
            name = m.query_member_name(group_id, sender)
            display_name = name if name else sender
        table.append(f"| {i} | {display_name} | {count} |")
    report.extend(table)
    
    report.append("\n## 3. 消息类型分布")
    types_dist = ", ".join([f"{t}: {c}" for t, c in group_stats['types'].items()])
    report.append(f"- {types_dist}")
    
    report.append("\n## 4. 活跃时段分析")
    hourly_dist = ", ".join([f"{h}点({c}条)" for h, c in sorted(group_stats['hourly'].items())])
    report.append(f"- {hourly_dist}")
    
    if nlp_results:
        highlights = nlp_results.get("highlights", [])
        if highlights:
            report.append("\n## 5. 群聊精华")
            report.extend(highlights)
        
        sentiment = nlp_results.get("sentiment", {})
        if sentiment:
            report.append("\n## 6. 情感分析")
            report.append(f"- 积极: {sentiment.get('positive', 0)}, 消极: {sentiment.get('negative', 0)}, 中性: {sentiment.get('neutral', 0)}")
    
    return "\n".join(report)

def generate_error_report(stats, solutions):
    report = ["# 🤖 错误日志分析报告", f"**日期**: {datetime.now().strftime('%Y-%m-%d')}"]
    
    report.append("\n## 错误汇总")
    total_errors = sum(stats['unique_errors'].values())
    report.append(f"- **错误种类**: `{len(stats['unique_errors'])}`")
    report.append(f"- **错误总数**: `{total_errors}`")
    
    report.append("\n## 详细错误列表")
    error_details_list = stats.get('error_details', [])
    for err_msg, count in stats['unique_errors'].items():
        report.append(f"### ❌ {err_msg} (出现 {count} 次)")
        
        matching_details = [d['detail'] for d in error_details_list if d.get('message') == err_msg][:5]
        if matching_details:
            report.append("**最近错误记录**:")
            for detail in matching_details:
                report.append(f"- `{detail}`")
        
        report.append(f"\n**大模型分析建议**:\n{solutions.get(err_msg, '暂无建议')}")
        report.append("\n---")
    
    return "\n".join(report)

def analyze_log_file(today=None):
    if not today:
        today = datetime.now().strftime("%Y%m%d")
    LOG_FILE = f'logs/bot_{today}.log'
    print("🚀 开始分析日志文件...")
    stats = analyze_log(LOG_FILE)
    lesson = Lesson()
    lesson_dir = lesson.lesson_dir
    
    # 分析群聊统计数据
    sorted_groups = analyze_group_stats(stats['all_messages'])
    
    target_group_ids = Config().get_config("log_analysis_groups", "message.yaml")
    if not target_group_ids:
        send_text("⚠️ 配置文件中未指定目标群聊ID，将分析所有群聊。", admin)
    nlp_results_map = {}
    group_map = dict(sorted_groups)
    for gid in target_group_ids:
        target_group_stats = group_map.get(gid)
        if target_group_stats:
            nlp_results_map[gid] = perform_nlp_analysis(target_group_stats['content_corpus'])

    # 生成汇总报告
    report_content = generate_report(stats, sorted_groups, target_group_ids, nlp_results_map)
    
    report_dir = os.path.join(lesson_dir, "reports")
    os.makedirs(report_dir, exist_ok=True)
    report_filename = f"{report_dir}/analysis_report_{datetime.now().strftime('%Y%m%d')}.md" 
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(report_content)
    static_url= Config().get_config("static_url", "wechat.yaml")
    send_text(static_url + report_filename[len(lesson_dir):].replace("\\", "/"), admin)
    
