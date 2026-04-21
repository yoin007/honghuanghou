# -*- coding: utf-8 -*-
"""
违纪累进规则处理模块

提供累进处罚的判断、触发和通知功能
"""

import logging
import json
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any

from .base import get_moral_db, log_operation
from sendqueue import send_text

logger = logging.getLogger(__name__)


# =============================================================================
# 数据结构定义
# =============================================================================

class EscalationResult:
    """累进判断结果"""
    triggered: bool = False
    action: str = None          # warning/criticism/demerit/serious_demerit
    description: str = None     # 处罚描述
    threshold: int = None       # 当前触发的阈值
    current_count: int = 0      # 当前累计次数
    previous_count: int = 0     # 上次记录后累计次数
    score_penalty: int = 0      # 额外扣分
    notify_roles: List[str] = [] # 需通知的角色
    punishment_id: int = None   # 自动创建的处分ID（如有）
    warning_log_id: int = None  # 预警日志ID
    message: str = None         # 通知消息内容


# =============================================================================
# 核心函数
# =============================================================================

def check_and_trigger_escalation(
    db,
    student_id: str,
    event_id: int,
    record_id: int,
    record_date,  # 可以是 date 或 datetime
    semester_id: int
) -> EscalationResult:
    """
    检查并触发累进处罚

    Args:
        db: 数据库连接
        student_id: 学生ID
        event_id: 违纪事件类型ID
        record_id: 当前记录ID
        record_date: 记录时间（可以是date或datetime）
        semester_id: 学期ID

    Returns:
        EscalationResult: 累进判断结果
    """
    result = EscalationResult()

    # 提取日期部分用于统计（累进规则按天计算）
    if isinstance(record_date, datetime):
        record_date_only = record_date.date()
        record_date_str = record_date.strftime('%Y-%m-%d %H:%M')
    else:
        record_date_only = record_date
        record_date_str = str(record_date)

    # 1. 查询累进规则
    rule = db.query_one(
        """SELECT * FROM violation_escalation_rule
        WHERE event_id = %s""",
        (event_id,)
    )

    if not rule:
        logger.debug(f"事件 {event_id} 无累进规则配置")
        return result

    # 2. 解析规则JSON
    try:
        escalation_rules = json.loads(rule['escalation_rules'])
    except json.JSONDecodeError as e:
        logger.error(f"累进规则JSON解析失败: {e}")
        return result

    time_window_days = rule.get('time_window_days', 90)
    rules_list = escalation_rules.get('rules', [])

    if not rules_list:
        return result

    # 3. 计算时间窗口内的累计次数（按日期统计，忽略时间部分）
    window_start = record_date_only - timedelta(days=time_window_days)

    count_result = db.query_one(
        """SELECT COUNT(*) as total_count
        FROM student_daily_record
        WHERE student_id = %s AND event_id = %s
        AND strftime('%Y-%m-%d', record_date) >= %s
        AND strftime('%Y-%m-%d', record_date) <= %s
        AND is_deleted = 0""",
        (student_id, event_id, window_start.strftime('%Y-%m-%d'), record_date_only.strftime('%Y-%m-%d'))
    )

    current_count = count_result['total_count'] if count_result else 1
    previous_count = current_count - 1  # 扣除当前这条记录

    result.current_count = current_count
    result.previous_count = previous_count

    # 4. 查找已触发过的最高阈值（避免重复触发）
    previous_triggered_threshold = 0

    existing_warnings = db.query_all(
        """SELECT wl.message, wl.warning_level
        FROM warning_log wl
        WHERE wl.student_id = %s
        AND wl.warning_level LIKE 'escalation_%'
        AND wl.semester_id = %s
        ORDER BY wl.created_at DESC""",
        (student_id, semester_id)
    )

    # 从已有记录中提取触发阈值
    for existing in existing_warnings or []:
        msg = existing.get('message', '')
        # 解析消息中的阈值信息
        if '累计' in msg:
            try:
                # 格式: "累计X次"
                parts = msg.split('累计')
                if len(parts) > 1:
                    threshold_str = parts[1].split('次')[0]
                    prev_threshold = int(threshold_str.strip())
                    if prev_threshold > previous_triggered_threshold:
                        previous_triggered_threshold = prev_threshold
            except:
                pass

    # 5. 判断是否触发新等级
    triggered_rule = None

    for rule_item in sorted(rules_list, key=lambda x: x['threshold']):
        threshold = rule_item['threshold']

        # 如果当前次数达到阈值，且之前未触发过此等级
        if current_count >= threshold and threshold > previous_triggered_threshold:
            triggered_rule = rule_item
            break

    if not triggered_rule:
        logger.debug(f"学生 {student_id} 事件 {event_id} 累计 {current_count} 次，未触发新等级")
        return result

    # 6. 执行累进处罚
    result.triggered = True
    result.action = triggered_rule.get('action', 'warning')
    result.description = triggered_rule.get('description', '警告')
    result.threshold = triggered_rule['threshold']
    result.score_penalty = triggered_rule.get('score_penalty', 0)
    result.notify_roles = triggered_rule.get('notify_roles', ['cleader'])

    # 生成通知消息
    student_info = db.query_one(
        """SELECT s.name, s.roomid, c.leader_wxid, c.leader_name, c.class_name
        FROM student s
        LEFT JOIN class c ON s.class_id = c.class_id
        WHERE s.student_id = %s""",
        (student_id,)
    )

    student_name = student_info.get('name', student_id) if student_info else student_id

    event_info = db.query_one(
        "SELECT event_name FROM daily_event_type WHERE event_id = %s",
        (event_id,)
    )
    event_name = event_info['event_name'] if event_info else f"事件{event_id}"

    result.message = (
        f"【累进处罚通知】\n"
        f"学生：{student_name}（{student_id}）\n"
        f"事件：{event_name}\n"
        f"时间窗口内累计：{current_count}次\n"
        f"触发处罚：{result.description}\n"
        f"触发条件：累计{result.threshold}次\n"
        f"记录时间：{record_date_str}"
    )

    # 7. 记录预警日志
    warning_config = db.query_one(
        """SELECT id FROM warning_config
        WHERE trigger_type = %s""",
        (f'escalation_{result.action}',)
    )

    if warning_config:
        db.execute(
            """INSERT INTO warning_log
            (student_id, rule_id, semester_id, warning_level, message)
            VALUES (%s, %s, %s, %s, %s)""",
            (student_id, warning_config['id'], semester_id, f'escalation_{result.action}', result.message)
        )
        result.warning_log_id = db.lastrowid()
    else:
        # 如果没有对应的warning_config，直接插入
        db.execute(
            """INSERT INTO warning_log
            (student_id, rule_id, semester_id, warning_level, message)
            VALUES (%s, %s, %s, %s, %s)""",
            (student_id, rule['rule_id'], semester_id, f'escalation_{result.action}', result.message)
        )
        result.warning_log_id = db.lastrowid()

    # 8. 自动创建处分记录（如果配置）
    if triggered_rule.get('auto_create_punishment', False):
        punishment_level = triggered_rule.get('punishment_level', 2)
        punishment_id = create_escalation_punishment(
            db, student_id, event_id, semester_id, record_date_only,
            result.description, result.score_penalty, punishment_level,
            record_id
        )
        result.punishment_id = punishment_id

    # 9. 发送通知
    send_escalation_notification(db, student_id, result, student_info)

    logger.info(f"学生 {student_id} 触发累进处罚: {result.description}")

    return result


def create_escalation_punishment(
    db,
    student_id: str,
    event_id: int,
    semester_id: int,
    punishment_date: date,
    punishment_reason: str,
    score_deduct: int,
    punishment_level: int,
    source_record_id: int
) -> int:
    """
    自动创建累进处分记录

    Args:
        db: 数据库连接
        student_id: 学生ID
        event_id: 违纪事件ID
        semester_id: 学期ID
        punishment_date: 处分日期
        punishment_reason: 处分原因
        score_deduct: 扣分
        punishment_level: 处分等级
        source_record_id: 触发源记录ID

    Returns:
        int: 处分记录ID
    """
    # 获取学生班级信息
    student_info = db.query_one(
        """SELECT s.class_id, s.grade_id
        FROM student s
        WHERE s.student_id = %s""",
        (student_id,)
    )

    if not student_info:
        logger.error(f"无法获取学生 {student_id} 的班级信息")
        return None

    # 处分等级文本
    level_map = {1: '一级', 2: '二级', 3: '三级', 4: '四级'}
    level_text = level_map.get(punishment_level, '二级')

    # 创建处分记录
    full_reason = f"[累进处罚] {punishment_reason}，触发源记录ID: {source_record_id}"

    db.execute(
        """INSERT INTO punishment_record
        (student_id, event_id, semester_id, punishment_date, class_id, grade_id,
         score_deduct, level, reason, recorder, is_revoked)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)""",
        (
            student_id,
            event_id,
            semester_id,
            punishment_date,
            student_info['class_id'],
            student_info['grade_id'],
            score_deduct,
            level_text,
            full_reason,
            'system_escalation'  # 系统自动创建
        )
    )

    punishment_id = db.lastrowid()

    # 记录操作日志
    log_operation(
        db, 'system_escalation', 'system', 'INSERT', 'punishment_record',
        punishment_id, semester_id,
        new_data={'student_id': student_id, 'reason': full_reason, 'source_record_id': source_record_id}
    )

    return punishment_id


def send_escalation_notification(
    db,
    student_id: str,
    result: EscalationResult,
    student_info: dict = None
) -> None:
    """
    发送累进处罚通知

    Args:
        db: 数据库连接
        student_id: 学生ID
        result: 累进判断结果
        student_info: 学生信息（可选，避免重复查询）
    """
    if not result.triggered or not result.message:
        return

    # 获取学生信息
    if not student_info:
        student_info = db.query_one(
            """SELECT s.name, s.roomid, c.leader_wxid, c.leader_name, c.class_name
            FROM student s
            LEFT JOIN class c ON s.class_id = c.class_id
            WHERE s.student_id = %s""",
            (student_id,)
        )

    if not student_info:
        return

    # 根据通知角色发送消息
    for role in result.notify_roles:
        recipient = None

        if role == 'cleader':
            # 通知班主任
            leader_name = student_info.get('leader_name', '')

            # 优先使用 leader_wxid（如果已配置）
            recipient = student_info.get('leader_wxid')

            # 如果 leader_wxid 为空，通过 contacts 表查找班主任 wxid
            if not recipient and leader_name:
                try:
                    import sqlite3
                    import os

                    # 连接 member.db 查询 contacts 表
                    member_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "databases", "member.db")

                    conn = sqlite3.connect(member_db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    cursor.execute(
                        """SELECT wxid FROM contacts
                        WHERE remark LIKE ? OR nick_name LIKE ?
                        LIMIT 1""",
                        (f'%{leader_name}%', f'%{leader_name}%')
                    )
                    row = cursor.fetchone()
                    conn.close()

                    if row:
                        recipient = row['wxid']
                        logger.info(f"通过 contacts 表找到班主任 {leader_name} 的 wxid: {recipient}")
                except Exception as e:
                    logger.warning(f"查询班主任 wxid 失败: {e}")

            if recipient:
                try:
                    send_text(result.message, recipient, producer="escalation")
                    logger.info(f"已通知班主任 {leader_name}: {recipient}")
                except Exception as e:
                    logger.error(f"发送班主任通知失败: {e}")
            else:
                logger.warning(f"班主任 {leader_name} 未配置 wxid，无法发送通知")

        elif role == 'xuefa':
            # 通知学发部（从配置获取）
            xuefa_config = db.query_one(
                "SELECT config_value FROM moral_config WHERE config_key = 'xuefa_notify_wxid'"
            )
            if xuefa_config:
                recipient = xuefa_config['config_value']
                try:
                    send_text(result.message, recipient, producer="escalation")
                    logger.info(f"已通知学发部: {recipient}")
                except Exception as e:
                    logger.error(f"发送学发部通知失败: {e}")


def get_student_escalation_history(
    db,
    student_id: str,
    semester_id: int
) -> List[Dict[str, Any]]:
    """
    获取学生累进处罚历史

    Args:
        db: 数据库连接
        student_id: 学生ID
        semester_id: 学期ID

    Returns:
        List: 累进处罚历史记录
    """
    history = db.query_all(
        """SELECT wl.*, wc.rule_name, wc.trigger_type
        FROM warning_log wl
        LEFT JOIN warning_config wc ON wl.rule_id = wc.id
        WHERE wl.student_id = %s
        AND wl.warning_level LIKE 'escalation_%'
        AND wl.semester_id = %s
        ORDER BY wl.created_at DESC""",
        (student_id, semester_id)
    )

    return history or []


def get_student_event_count_in_window(
    db,
    student_id: str,
    event_id: int,
    current_date: date,
    time_window_days: int = 90
) -> int:
    """
    获取学生在时间窗口内某事件的累计次数

    Args:
        db: 数据库连接
        student_id: 学生ID
        event_id: 事件ID
        current_date: 当前日期
        time_window_days: 时间窗口天数

    Returns:
        int: 累计次数
    """
    window_start = current_date - timedelta(days=time_window_days)

    result = db.query_one(
        """SELECT COUNT(*) as count
        FROM student_daily_record
        WHERE student_id = %s AND event_id = %s
        AND strftime('%Y-%m-%d', record_date) >= %s
        AND strftime('%Y-%m-%d', record_date) <= %s
        AND is_deleted = 0""",
        (student_id, event_id, window_start.strftime('%Y-%m-%d'), current_date.strftime('%Y-%m-%d'))
    )

    return result['count'] if result else 0


def get_next_threshold_info(
    db,
    student_id: str,
    event_id: int,
    current_date: date
) -> Dict[str, Any]:
    """
    获取学生某事件的累计进度和下一阈值信息

    Args:
        db: 数据库连接
        student_id: 学生ID
        event_id: 事件ID
        current_date: 当前日期

    Returns:
        Dict: 包含当前次数、下一阈值、距离等信息
    """
    # 查询累进规则
    rule = db.query_one(
        """SELECT * FROM violation_escalation_rule
        WHERE event_id = %s""",
        (event_id,)
    )

    if not rule:
        return {'has_rule': False}

    time_window_days = rule.get('time_window_days', 90)

    try:
        escalation_rules = json.loads(rule['escalation_rules'])
        rules_list = escalation_rules.get('rules', [])
    except:
        return {'has_rule': False, 'parse_error': True}

    # 获取当前累计次数
    current_count = get_student_event_count_in_window(
        db, student_id, event_id, current_date, time_window_days
    )

    # 查找下一阈值
    next_threshold = None
    next_action = None

    for rule_item in sorted(rules_list, key=lambda x: x['threshold']):
        if rule_item['threshold'] > current_count:
            next_threshold = rule_item['threshold']
            next_action = rule_item.get('description', '')
            break

    return {
        'has_rule': True,
        'time_window_days': time_window_days,
        'current_count': current_count,
        'next_threshold': next_threshold,
        'next_action': next_action,
        'remaining': (next_threshold - current_count) if next_threshold else None,
        'progress_percent': (current_count / next_threshold * 100) if next_threshold else 100
    }