# -*- coding: utf-8 -*-
"""Overview dashboard helpers.

Batch 20: Extracted from dashboard.py to keep route handlers thin.
"""

from typing import Dict, List

from models.datas_api.auth import User
from models.datas_api.moral.base import get_moral_db, get_teacher_class_id, has_user_role
from models.datas_api.dashboard_common import (
    is_moral_manager,
    metric,
    safe_count,
)


def build_overview_cards(user: User) -> List[Dict[str, object]]:
    """Build overview cards for dashboard homepage.

    Args:
        user: Current user to determine visible cards.

    Returns:
        List of card dicts with label/value/unit/route.
    """
    with get_moral_db() as db:
        cards = [
            metric("在校学生", safe_count(db, "SELECT COUNT(*) FROM student WHERE status = '在校'"), "人", "/moral/config/student"),
            metric("启用班级", safe_count(db, "SELECT COUNT(*) FROM class WHERE is_active = 1"), "个", "/moral/config/class"),
            metric(
                "教师账号",
                safe_count(db, "SELECT COUNT(*) FROM teacher WHERE COALESCE(identity_type, 'teacher') = 'teacher' AND is_active = 1"),
                "人",
                "/teacher-manage",
            ),
        ]

        if is_moral_manager(user) or has_user_role(user, "cleader"):
            conditions = ["dr.is_deleted = 0"]
            params = []
            if not is_moral_manager(user) and has_user_role(user, "cleader"):
                my_class_id = get_teacher_class_id(user, db)
                if my_class_id:
                    conditions.append("dr.class_id = %s")
                    params.append(my_class_id)
                else:
                    conditions.append("1 = 0")
            cards.append(metric(
                "日常记录",
                safe_count(db, f"SELECT COUNT(*) FROM student_daily_record dr WHERE {' AND '.join(conditions)}", tuple(params)),
                "条",
                "/moral/daily-record",
            ))

        return cards