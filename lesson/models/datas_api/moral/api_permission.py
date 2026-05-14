# -*- coding: utf-8 -*-
"""
API权限管理模块

提供API权限配置的增删改查功能
"""

import logging
import json
import re
import hashlib
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    get_current_user,
    get_current_user_optional,
    log_operation,
    is_admin_user,
    get_user_role_level,
    get_user_roles,
)
from models.datas_api.auth import User
from config.config import Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-permissions", tags=["API权限管理"])

EXPECTED_PUBLIC_API_PATHS = {
    "/api/token",
}


# =============================================================================
# Pydantic 模型
# =============================================================================

class ApiPermissionCreate(BaseModel):
    """创建API权限配置"""
    api_path: str = Field(..., description="API路径")
    api_name: str = Field(..., description="API名称")
    api_group: str = Field(..., description="API分组")
    allowed_roles: List[str] = Field(..., description="允许访问的角色列表")
    min_level: int = Field(default=0, description="最低等级要求")
    module_id: Optional[int] = Field(None, description="所属模块ID")
    http_method: str = Field(default="*", description="HTTP方法")
    match_type: str = Field(default="exact", description="匹配方式：exact/prefix/pattern")
    policy_mode: str = Field(default="role_and_level", description="鉴权策略")
    inherit_from_module: int = Field(default=0, description="是否继承模块权限")
    is_public: int = Field(default=0, description="是否无需鉴权")
    enforce_backend: int = Field(default=1, description="是否用于后端鉴权")
    resource_type: str = Field(default="", description="业务资源类型")
    action_type: str = Field(default="", description="动作类型")
    data_scope_rules: Optional[Dict[str, List[str]]] = Field(default_factory=dict, description="角色数据范围规则")
    target_scope_rules: Optional[Dict[str, List[str]]] = Field(default_factory=dict, description="角色目标对象范围规则")
    operation_scope_rules: Optional[Dict[str, List[str]]] = Field(default_factory=dict, description="角色动作范围规则")
    description: Optional[str] = Field(None, description="描述")


class ApiPermissionUpdate(BaseModel):
    """更新API权限配置"""
    api_name: Optional[str] = Field(None, description="API名称")
    api_group: Optional[str] = Field(None, description="API分组")
    allowed_roles: Optional[List[str]] = Field(None, description="允许访问的角色列表")
    min_level: Optional[int] = Field(None, description="最低等级要求")
    module_id: Optional[int] = Field(None, description="所属模块ID")
    http_method: Optional[str] = Field(None, description="HTTP方法")
    match_type: Optional[str] = Field(None, description="匹配方式：exact/prefix/pattern")
    policy_mode: Optional[str] = Field(None, description="鉴权策略")
    inherit_from_module: Optional[int] = Field(None, description="是否继承模块权限")
    is_public: Optional[int] = Field(None, description="是否无需鉴权")
    enforce_backend: Optional[int] = Field(None, description="是否用于后端鉴权")
    resource_type: Optional[str] = Field(None, description="业务资源类型")
    action_type: Optional[str] = Field(None, description="动作类型")
    data_scope_rules: Optional[Dict[str, List[str]]] = Field(None, description="角色数据范围规则")
    target_scope_rules: Optional[Dict[str, List[str]]] = Field(None, description="角色目标对象范围规则")
    operation_scope_rules: Optional[Dict[str, List[str]]] = Field(None, description="角色动作范围规则")
    description: Optional[str] = Field(None, description="描述")
    is_active: Optional[int] = Field(None, description="是否启用")


class ApiPermissionModuleCreate(BaseModel):
    """创建API权限模块"""
    module_key: str = Field(..., description="模块标识")
    module_name: str = Field(..., description="模块名称")
    parent_id: Optional[int] = Field(None, description="父模块ID")
    allowed_roles: List[str] = Field(default_factory=list, description="模块默认允许角色")
    min_level: int = Field(default=0, description="模块默认最低等级")
    policy_mode: str = Field(default="role_and_level", description="模块默认鉴权策略")
    description: Optional[str] = Field(None, description="描述")
    sort_order: int = Field(default=0, description="排序")


class ApiPermissionModuleUpdate(BaseModel):
    """更新API权限模块"""
    module_key: Optional[str] = Field(None, description="模块标识")
    module_name: Optional[str] = Field(None, description="模块名称")
    parent_id: Optional[int] = Field(None, description="父模块ID")
    allowed_roles: Optional[List[str]] = Field(None, description="模块默认允许角色")
    min_level: Optional[int] = Field(None, description="模块默认最低等级")
    policy_mode: Optional[str] = Field(None, description="模块默认鉴权策略")
    description: Optional[str] = Field(None, description="描述")
    sort_order: Optional[int] = Field(None, description="排序")
    is_active: Optional[int] = Field(None, description="是否启用")


class ApiPermissionTemplateApply(BaseModel):
    """批量套用权限模板"""
    config_ids: List[int] = Field(..., description="API配置ID列表")
    template_key: str = Field(..., description="模板标识")


class ApiPermissionAuditRequest(BaseModel):
    """权限配置巡检请求"""
    config_ids: List[int] = Field(default_factory=list, description="仅巡检这些API；为空时巡检全部")


# =============================================================================
# 默认API权限配置
# =============================================================================

DEFAULT_API_PERMISSIONS = [
    # 日常表现记录
    {"api_path": "/api/moral/daily-records", "api_name": "获取日常记录列表", "api_group": "日常表现", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10},
    {"api_path": "/api/moral/daily-records/types", "api_name": "获取事件类型", "api_group": "日常表现", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10},
    {"api_path": "/api/moral/daily-records/create", "api_name": "创建日常记录", "api_group": "日常表现", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10},
    {"api_path": "/api/moral/daily-records/batch", "api_name": "批量创建记录", "api_group": "日常表现", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/daily-records/update", "api_name": "更新日常记录", "api_group": "日常表现", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10},
    {"api_path": "/api/moral/daily-records/delete", "api_name": "删除日常记录", "api_group": "日常表现", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10},
    {"api_path": "/api/moral/daily-records/statistics/student/{student_id}", "api_name": "学生日常表现统计", "api_group": "日常表现", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10, "match_type": "pattern"},

    # 点滴记录
    {"api_path": "/api/moral/moment-records", "api_name": "获取点滴记录", "api_group": "点滴记录", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10},
    {"api_path": "/api/moral/moment-records/create", "api_name": "创建点滴记录", "api_group": "点滴记录", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10},
    {"api_path": "/api/moral/moment-records/update", "api_name": "更新点滴记录", "api_group": "点滴记录", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10},
    {"api_path": "/api/moral/moment-records/delete", "api_name": "删除点滴记录", "api_group": "点滴记录", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10},

    # 校级事件
    {"api_path": "/api/moral/school-records", "api_name": "获取校级事件", "api_group": "校级事件", "allowed_roles": ["admin", "xuefa"], "min_level": 20},
    {"api_path": "/api/moral/school-records/types", "api_name": "校级事件类型管理", "api_group": "校级事件", "allowed_roles": ["admin", "xuefa"], "min_level": 20},
    {"api_path": "/api/moral/school-records/create", "api_name": "创建校级事件", "api_group": "校级事件", "allowed_roles": ["admin", "xuefa"], "min_level": 20},
    {"api_path": "/api/moral/school-records/update", "api_name": "更新校级事件", "api_group": "校级事件", "allowed_roles": ["admin", "xuefa"], "min_level": 20},
    {"api_path": "/api/moral/school-records/delete", "api_name": "删除校级事件", "api_group": "校级事件", "allowed_roles": ["admin", "xuefa"], "min_level": 20},

    # 处分管理
    {"api_path": "/api/moral/punishments", "api_name": "获取处分记录", "api_group": "处分管理", "allowed_roles": ["admin", "xuefa"], "min_level": 20},
    {"api_path": "/api/moral/punishments/create", "api_name": "创建处分", "api_group": "处分管理", "allowed_roles": ["admin", "xuefa"], "min_level": 20},
    {"api_path": "/api/moral/punishments/update", "api_name": "更新处分", "api_group": "处分管理", "allowed_roles": ["admin", "xuefa"], "min_level": 20},
    {"api_path": "/api/moral/punishments/revoke", "api_name": "撤销处分", "api_group": "处分管理", "allowed_roles": ["admin", "xuefa"], "min_level": 20},
    {"api_path": "/api/moral/punishments/review", "api_name": "处分复核", "api_group": "处分管理", "allowed_roles": ["admin", "xuefa"], "min_level": 20},
    {"api_path": "/api/moral/punishments/expiring", "api_name": "即将到期处分列表", "api_group": "处分管理", "allowed_roles": ["admin", "xuefa", "g_leader", "cleader"], "min_level": 20, "http_method": "GET", "resource_type": "punishment_record", "action_type": "view"},
    {"api_path": "/api/moral/punishment-periods", "api_name": "处分期限配置列表", "api_group": "处分管理", "allowed_roles": ["admin", "xuefa"], "min_level": 20, "http_method": "GET", "resource_type": "punishment_period", "action_type": "view"},
    {"api_path": "/api/moral/punishment-periods/update", "api_name": "更新处分期限配置", "api_group": "处分管理", "allowed_roles": ["admin", "xuefa"], "min_level": 20, "http_method": "PUT", "resource_type": "punishment_period", "action_type": "update"},
    {"api_path": "/api/moral/punishment-revoke-applications", "api_name": "处分撤销申请列表", "api_group": "处分管理", "allowed_roles": ["admin", "xuefa", "g_leader", "cleader"], "min_level": 20, "http_method": "GET", "resource_type": "punishment_revoke_application", "action_type": "view"},
    {"api_path": "/api/moral/punishment-revoke-applications/create", "api_name": "提交处分撤销申请", "api_group": "处分管理", "allowed_roles": ["admin", "cleader"], "min_level": 20, "http_method": "POST", "resource_type": "punishment_revoke_application", "action_type": "create"},
    {"api_path": "/api/moral/punishment-revoke-applications/approve", "api_name": "审批通过处分撤销申请", "api_group": "处分管理", "allowed_roles": ["admin", "xuefa"], "min_level": 20, "http_method": "POST", "resource_type": "punishment_revoke_application", "action_type": "review"},
    {"api_path": "/api/moral/punishment-revoke-applications/reject", "api_name": "审批拒绝处分撤销申请", "api_group": "处分管理", "allowed_roles": ["admin", "xuefa"], "min_level": 20, "http_method": "POST", "resource_type": "punishment_revoke_application", "action_type": "review"},

    # 集体事件
    {"api_path": "/api/moral/collective-events", "api_name": "集体事件管理", "api_group": "集体事件", "allowed_roles": ["admin", "xuefa"], "min_level": 20},
    {"api_path": "/api/moral/collective-events/create", "api_name": "创建集体事件", "api_group": "集体事件", "allowed_roles": ["admin", "xuefa"], "min_level": 20},
    {"api_path": "/api/moral/collective-events/update", "api_name": "更新集体事件", "api_group": "集体事件", "allowed_roles": ["admin", "xuefa"], "min_level": 20},
    {"api_path": "/api/moral/collective-events/delete", "api_name": "删除集体事件", "api_group": "集体事件", "allowed_roles": ["admin", "xuefa"], "min_level": 20},
    {"api_path": "/api/moral/collective-events/distributions/update", "api_name": "调整集体事件分配", "api_group": "集体事件", "allowed_roles": ["admin", "xuefa"], "min_level": 20},

    # 德育任务
    {"api_path": "/api/moral/tasks", "api_name": "获取德育任务", "api_group": "德育任务", "allowed_roles": ["admin", "xuefa"], "min_level": 20},
    {"api_path": "/api/moral/tasks/create", "api_name": "创建德育任务", "api_group": "德育任务", "allowed_roles": ["admin", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/tasks/update", "api_name": "更新德育任务", "api_group": "德育任务", "allowed_roles": ["admin", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/tasks/delete", "api_name": "删除德育任务", "api_group": "德育任务", "allowed_roles": ["admin", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/tasks/finish", "api_name": "记录任务完成", "api_group": "德育任务", "allowed_roles": ["admin", "xuefa"], "min_level": 20},

    # 事件类型管理
    {"api_path": "/api/moral/event-types", "api_name": "创建事件类型", "api_group": "事件类型", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/event-types/update", "api_name": "更新事件类型", "api_group": "事件类型", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/event-types/import", "api_name": "批量导入事件类型", "api_group": "事件类型", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},

    # 学生管理
    # 数据驾驶舱
    {"api_path": "/api/dashboard/overview", "api_name": "当前用户数据驾驶舱总览", "api_group": "数据驾驶舱", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10},
    {"api_path": "/api/dashboard/moral/summary", "api_name": "德育驾驶舱总览", "api_group": "数据驾驶舱", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 20},
    {"api_path": "/api/dashboard/teaching/summary", "api_name": "教务驾驶舱总览", "api_group": "数据驾驶舱", "allowed_roles": ["admin", "jiaowu"], "min_level": 50},
    {"api_path": "/api/dashboard/class/summary", "api_name": "班级驾驶舱总览", "api_group": "数据驾驶舱", "allowed_roles": ["admin", "jiaowu", "xuefa", "cleader"], "min_level": 20},
    {"api_path": "/api/dashboard/grade/list", "api_name": "年级驾驶舱年级列表", "api_group": "数据驾驶舱", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader"], "min_level": 20},
    {"api_path": "/api/dashboard/grade/summary", "api_name": "年级驾驶舱总览", "api_group": "数据驾驶舱", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader"], "min_level": 20},
    {"api_path": "/api/dashboard/teacher/workbench", "api_name": "教师个人工作台", "api_group": "数据驾驶舱", "allowed_roles": ["admin", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10},
    {"api_path": "/api/dashboard/invigilation/summary", "api_name": "监考驾驶舱总览", "api_group": "数据驾驶舱", "allowed_roles": ["admin", "jiaowu"], "min_level": 50},
    {"api_path": "/api/dashboard/system/summary", "api_name": "系统运维驾驶舱总览", "api_group": "数据驾驶舱", "allowed_roles": ["admin"], "min_level": 100},
    {"api_path": "/api/dashboard/score-trend/student/{student_id}", "api_name": "学生个人得分趋势", "api_group": "数据驾驶舱", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 20, "match_type": "pattern"},
    {"api_path": "/api/dashboard/score-trend/class/{class_id}", "api_name": "班级平均得分趋势", "api_group": "数据驾驶舱", "allowed_roles": ["admin", "jiaowu", "xuefa", "cleader"], "min_level": 20, "match_type": "pattern"},
    {"api_path": "/api/dashboard/score-trend/grade/{grade_id}", "api_name": "年级平均得分趋势", "api_group": "数据驾驶舱", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader"], "min_level": 20, "match_type": "pattern"},
    {"api_path": "/api/dashboard/teacher-record-trend", "api_name": "教师德育记录趋势", "api_group": "数据驾驶舱", "allowed_roles": ["admin", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10},

    # 教师待办
    {"api_path": "/api/teacher/todos", "api_name": "查询教师待办", "api_group": "教师待办", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10, "http_method": "GET", "resource_type": "teacher_todo", "action_type": "view"},
    {"api_path": "/api/teacher/todos/create", "api_name": "创建教师待办", "api_group": "教师待办", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10, "http_method": "POST", "resource_type": "teacher_todo", "action_type": "create"},
    {"api_path": "/api/teacher/todos/{series_id}", "api_name": "编辑删除教师待办", "api_group": "教师待办", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10, "match_type": "pattern", "resource_type": "teacher_todo", "action_type": "update"},
    {"api_path": "/api/teacher/todos/occurrences/{occurrence_id}/complete", "api_name": "完成教师待办实例", "api_group": "教师待办", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10, "http_method": "POST", "match_type": "pattern", "resource_type": "teacher_todo", "action_type": "operate"},
    {"api_path": "/api/teacher/todos/occurrences/{occurrence_id}/reopen", "api_name": "恢复教师待办实例", "api_group": "教师待办", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10, "http_method": "POST", "match_type": "pattern", "resource_type": "teacher_todo", "action_type": "operate"},
    {"api_path": "/api/teacher/todos/upcoming", "api_name": "教师近期待办", "api_group": "教师待办", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10, "http_method": "GET", "resource_type": "teacher_todo", "action_type": "view"},
    # 教师协作群组
    {"api_path": "/api/teacher/todos/groups", "api_name": "查询协作群组", "api_group": "教师待办", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10, "http_method": "GET", "resource_type": "teacher_todo_group", "action_type": "view"},
    {"api_path": "/api/teacher/todos/groups", "api_name": "创建协作群组", "api_group": "教师待办", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10, "http_method": "POST", "resource_type": "teacher_todo_group", "action_type": "create"},
    {"api_path": "/api/teacher/todos/groups/{group_id}", "api_name": "更新删除协作群组", "api_group": "教师待办", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10, "match_type": "pattern", "resource_type": "teacher_todo_group", "action_type": "update"},
    {"api_path": "/api/teacher/todos/groups/{group_id}/members", "api_name": "添加群组成员", "api_group": "教师待办", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10, "http_method": "POST", "match_type": "pattern", "resource_type": "teacher_todo_group", "action_type": "operate"},
    {"api_path": "/api/teacher/todos/groups/{group_id}/members/{teacher_id}", "api_name": "移除群组成员", "api_group": "教师待办", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10, "match_type": "pattern", "resource_type": "teacher_todo_group", "action_type": "operate"},

    # 学生管理
    {"api_path": "/api/moral/admin/students", "api_name": "获取学生列表", "api_group": "学生管理", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 30},
    {"api_path": "/api/moral/admin/students/create", "api_name": "创建学生", "api_group": "学生管理", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/admin/students/update", "api_name": "更新学生信息", "api_group": "学生管理", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 30},
    {"api_path": "/api/moral/admin/students/batch", "api_name": "批量导入学生", "api_group": "学生管理", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/admin/teachers", "api_name": "获取教师选择列表", "api_group": "基础配置", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50, "action_type": "operate"},
    {"api_path": "/api/moral/admin/grades", "api_name": "获取级号列表", "api_group": "基础配置", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10, "action_type": "operate"},
    {"api_path": "/api/moral/admin/grades/create", "api_name": "创建级号", "api_group": "基础配置", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50, "action_type": "operate"},
    {"api_path": "/api/moral/admin/grades/{grade_id}", "api_name": "更新级号", "api_group": "基础配置", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50, "match_type": "pattern"},
    {"api_path": "/api/moral/admin/grades/promote/preview", "api_name": "预览年级升迁", "api_group": "基础配置", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50, "action_type": "operate"},
    {"api_path": "/api/moral/admin/grades/promote/execute", "api_name": "执行年级升迁", "api_group": "基础配置", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50, "action_type": "operate"},
    {"api_path": "/api/moral/admin/grades/archived", "api_name": "获取归档年级", "api_group": "基础配置", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50, "action_type": "operate"},
    {"api_path": "/api/moral/admin/classes", "api_name": "获取班级列表", "api_group": "基础配置", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10, "action_type": "operate"},
    {"api_path": "/api/moral/admin/classes/create", "api_name": "创建班级", "api_group": "基础配置", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50, "action_type": "operate"},
    {"api_path": "/api/moral/admin/classes/{class_id}", "api_name": "更新班级", "api_group": "基础配置", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50, "match_type": "pattern"},
    {"api_path": "/api/moral/admin/school-years", "api_name": "获取学年列表", "api_group": "基础配置", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10, "action_type": "operate"},
    {"api_path": "/api/moral/admin/school-years/create", "api_name": "创建学年", "api_group": "基础配置", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50, "action_type": "operate"},
    {"api_path": "/api/moral/admin/semesters", "api_name": "获取学期列表", "api_group": "基础配置", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10, "action_type": "operate"},
    {"api_path": "/api/moral/admin/semesters/create", "api_name": "创建学期", "api_group": "基础配置", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50, "action_type": "operate"},
    {"api_path": "/api/moral/admin/semesters/{semester_id}/set-current", "api_name": "设置当前学期", "api_group": "基础配置", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50, "match_type": "pattern", "action_type": "operate"},

    # 系统配置
    {"api_path": "/api/moral/admin/config", "api_name": "系统配置", "api_group": "系统配置", "allowed_roles": ["admin"], "min_level": 100},
    {"api_path": "/api/moral/admin/logs", "api_name": "操作日志查询", "api_group": "系统配置", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50, "http_method": "GET", "resource_type": "operation_log", "action_type": "view"},
    {"api_path": "/api/moral/ai-model-config", "api_name": "AI模型配置", "api_group": "系统配置", "allowed_roles": ["admin"], "min_level": 100, "resource_type": "ai_model_config", "action_type": "operate"},
    {"api_path": "/api/moral/scheduler", "api_name": "定时任务调度器", "api_group": "系统配置", "allowed_roles": ["admin"], "min_level": 100, "resource_type": "scheduler", "action_type": "operate"},
    {"api_path": "/api/moral/admin/api-permissions", "api_name": "API权限管理", "api_group": "系统配置", "allowed_roles": ["admin"], "min_level": 100},
    {"api_path": "/api/moral/menu-permission/list", "api_name": "获取菜单配置", "api_group": "菜单权限", "allowed_roles": ["admin"], "min_level": 100, "action_type": "operate"},
    {"api_path": "/api/moral/menu-permission/my-menu", "api_name": "获取当前用户菜单", "api_group": "菜单权限", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher", "student"], "min_level": 0, "action_type": "operate"},
    {"api_path": "/api/moral/menu-permission/groups", "api_name": "获取菜单分组", "api_group": "菜单权限", "allowed_roles": ["admin"], "min_level": 100, "action_type": "operate"},
    {"api_path": "/api/moral/menu-permission/roles", "api_name": "获取菜单角色", "api_group": "菜单权限", "allowed_roles": ["admin"], "min_level": 100, "action_type": "operate"},
    {"api_path": "/api/moral/menu-permission/create", "api_name": "创建菜单配置", "api_group": "菜单权限", "allowed_roles": ["admin"], "min_level": 100, "action_type": "operate"},
    {"api_path": "/api/moral/menu-permission/{menu_key}", "api_name": "修改菜单配置", "api_group": "菜单权限", "allowed_roles": ["admin"], "min_level": 100, "match_type": "pattern", "action_type": "operate"},
    {"api_path": "/api/moral/menu-permission/batch", "api_name": "批量更新菜单权限", "api_group": "菜单权限", "allowed_roles": ["admin"], "min_level": 100, "action_type": "operate"},
    {"api_path": "/api/moral/menu-permission/batch-by-group", "api_name": "按分组更新菜单权限", "api_group": "菜单权限", "allowed_roles": ["admin"], "min_level": 100, "action_type": "operate"},
    {"api_path": "/api/moral/menu-permission/init", "api_name": "初始化菜单权限", "api_group": "菜单权限", "allowed_roles": ["admin"], "min_level": 100, "action_type": "operate"},
    {"api_path": "/api/moral/menu-permission/reset", "api_name": "重置菜单权限", "api_group": "菜单权限", "allowed_roles": ["admin"], "min_level": 100, "action_type": "operate"},
    {"api_path": "/api/moral/admin/database/list", "api_name": "获取数据库列表", "api_group": "数据库管理", "allowed_roles": ["admin"], "min_level": 100, "action_type": "operate"},
    {"api_path": "/api/moral/admin/database/tables/{db_name}", "api_name": "获取数据库表列表", "api_group": "数据库管理", "allowed_roles": ["admin"], "min_level": 100, "match_type": "pattern", "action_type": "operate"},
    {"api_path": "/api/moral/admin/database/protected-tables", "api_name": "获取受保护表", "api_group": "数据库管理", "allowed_roles": ["admin"], "min_level": 100, "action_type": "operate"},
    {"api_path": "/api/moral/admin/database/generate-token/{db_name}/{table_name}", "api_name": "生成清空确认令牌", "api_group": "数据库管理", "allowed_roles": ["admin"], "min_level": 100, "match_type": "pattern", "action_type": "operate"},
    {"api_path": "/api/moral/admin/database/clear/{db_name}/{table_name}", "api_name": "清空数据库表", "api_group": "数据库管理", "allowed_roles": ["admin"], "min_level": 100, "match_type": "pattern", "action_type": "operate"},
    {"api_path": "/api/moral/admin/database/check-integrity", "api_name": "检查数据库完整性", "api_group": "数据库管理", "allowed_roles": ["admin"], "min_level": 100, "action_type": "operate"},
    {"api_path": "/api/moral/admin/database-backup/config", "api_name": "数据库备份配置", "api_group": "数据库管理", "allowed_roles": ["admin"], "min_level": 100, "action_type": "operate"},
    {"api_path": "/api/moral/admin/database-backup/manual", "api_name": "手动执行数据库备份", "api_group": "数据库管理", "allowed_roles": ["admin"], "min_level": 100, "action_type": "operate"},
    {"api_path": "/api/moral/admin/database-backup/history", "api_name": "数据库备份历史", "api_group": "数据库管理", "allowed_roles": ["admin"], "min_level": 100, "action_type": "view"},
    {"api_path": "/api/moral/admin/database-backup/delete/{backup_id}", "api_name": "删除数据库备份", "api_group": "数据库管理", "allowed_roles": ["admin"], "min_level": 100, "match_type": "pattern", "action_type": "delete"},
    {"api_path": "/api/moral/admin/database-backup/download/{backup_id}", "api_name": "下载数据库备份", "api_group": "数据库管理", "allowed_roles": ["admin"], "min_level": 100, "match_type": "pattern", "action_type": "export"},
    {"api_path": "/api/moral/admin/database-backup/schedule", "api_name": "数据库定时备份配置", "api_group": "数据库管理", "allowed_roles": ["admin"], "min_level": 100, "action_type": "operate"},

    # 生日提醒
    {"api_path": "/api/moral/birthdays/upcoming", "api_name": "获取即将生日", "api_group": "生日提醒", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10},
    {"api_path": "/api/moral/birthdays/today", "api_name": "获取今日生日", "api_group": "生日提醒", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"], "min_level": 10},

    # 学生画像
    {"api_path": "/api/moral/timeline", "api_name": "一生一册查看", "api_group": "一生一册", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 20},
    {"api_path": "/api/moral/timeline/search", "api_name": "一生一册学生搜索", "api_group": "一生一册", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 20},
    {"api_path": "/api/moral/timeline/export/{student_id}/xlsx", "api_name": "导出单学生一生一册", "api_group": "一生一册", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 20, "match_type": "pattern"},
    {"api_path": "/api/moral/timeline/export/class/{class_id}", "api_name": "批量导出班级一生一册", "api_group": "一生一册", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 20, "match_type": "pattern"},

    # 学生画像
    {"api_path": "/api/moral/profiles", "api_name": "获取画像列表", "api_group": "学生画像", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 20, "http_method": "GET", "resource_type": "student_profile", "action_type": "view"},
    {"api_path": "/api/moral/profiles/student/{student_id}", "api_name": "获取学生画像", "api_group": "学生画像", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 30, "match_type": "pattern"},
    {"api_path": "/api/moral/profiles/student/{student_id}/generate", "api_name": "生成学生画像", "api_group": "学生画像", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 30, "match_type": "pattern"},
    {"api_path": "/api/moral/profiles/student/{student_id}/generate-async", "api_name": "异步生成学生画像", "api_group": "学生画像", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 30, "match_type": "pattern"},
    {"api_path": "/api/moral/profiles/generation-status/{job_id}", "api_name": "查询画像生成状态", "api_group": "学生画像", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 30, "match_type": "pattern"},
    {"api_path": "/api/moral/profiles/batch-generate", "api_name": "批量生成学生画像", "api_group": "学生画像", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 30},
    {"api_path": "/api/moral/profiles/config", "api_name": "获取画像配置", "api_group": "学生画像", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 30},

    # AI 诊疗
    {"api_path": "/api/moral/consultations", "api_name": "获取诊疗会话列表", "api_group": "AI诊疗", "allowed_roles": ["admin", "xuefa", "g_leader", "cleader"], "min_level": 20},
    {"api_path": "/api/moral/consultations/create", "api_name": "创建诊疗会话", "api_group": "AI诊疗", "allowed_roles": ["admin", "xuefa", "g_leader", "cleader"], "min_level": 20},
    {"api_path": "/api/moral/consultations/update", "api_name": "更新诊疗会话", "api_group": "AI诊疗", "allowed_roles": ["admin", "xuefa", "g_leader", "cleader"], "min_level": 20},
    {"api_path": "/api/moral/consultations/close", "api_name": "关闭诊疗会话", "api_group": "AI诊疗", "allowed_roles": ["admin", "xuefa", "g_leader", "cleader"], "min_level": 20},
    {"api_path": "/api/moral/carryover/execute", "api_name": "执行任务结转", "api_group": "任务结转", "allowed_roles": ["admin", "xuefa"], "min_level": 50, "action_type": "operate"},
    {"api_path": "/api/moral/carryover/preview", "api_name": "预览任务结转", "api_group": "任务结转", "allowed_roles": ["admin", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/carryover/logs", "api_name": "查看任务结转日志", "api_group": "任务结转", "allowed_roles": ["admin", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/carryover/config", "api_name": "任务结转配置", "api_group": "任务结转", "allowed_roles": ["admin", "xuefa"], "min_level": 50, "action_type": "operate"},
    {"api_path": "/api/moral/escalation-rules/student/{student_id}/history", "api_name": "学生累进处罚历史", "api_group": "累进规则", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 20, "match_type": "pattern"},
    {"api_path": "/api/moral/escalation-rules/student/{student_id}/count", "api_name": "学生事件累计次数", "api_group": "累进规则", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 20, "match_type": "pattern"},
    {"api_path": "/api/moral/escalation-rules/student/{student_id}/progress", "api_name": "学生消极事件累计进度", "api_group": "累进规则", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 20, "match_type": "pattern"},
    {"api_path": "/api/moral/escalation-rules", "api_name": "累进规则管理", "api_group": "累进规则", "allowed_roles": ["admin", "xuefa"], "min_level": 20, "resource_type": "escalation_rule", "action_type": "operate"},
    {"api_path": "/api/moral/collective-events/student/{student_id}", "api_name": "学生集体事件得分汇总", "api_group": "集体事件", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "student"], "min_level": 0, "match_type": "pattern"},

    # 评价查询
    {"api_path": "/api/moral/evaluations/student/{student_id}", "api_name": "学生评价查询", "api_group": "评价查询", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "student"], "min_level": 0, "match_type": "pattern"},
    {"api_path": "/api/moral/evaluations/class/{class_id}", "api_name": "班级评价查询", "api_group": "评价查询", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader", "cleader"], "min_level": 30, "match_type": "pattern"},
    {"api_path": "/api/moral/evaluations/grade/{grade_id}", "api_name": "年级评价查询", "api_group": "评价查询", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader"], "min_level": 50, "match_type": "pattern"},
    {"api_path": "/api/moral/evaluations/calculate", "api_name": "计算德育评价", "api_group": "评价查询", "allowed_roles": ["admin", "jiaowu", "xuefa", "g_leader"], "min_level": 50},

    # 学期末评价
    {"api_path": "/api/moral/semester-evaluations/generate", "api_name": "生成单学生学期末评价", "api_group": "学期末评价", "allowed_roles": ["admin", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/semester-evaluations/batch-generate", "api_name": "批量生成学期末评价", "api_group": "学期末评价", "allowed_roles": ["admin", "xuefa", "g_leader", "cleader"], "min_level": 20},
    {"api_path": "/api/moral/semester-evaluations/batch-status/{job_id}", "api_name": "查询学期末评价批量生成状态", "api_group": "学期末评价", "allowed_roles": ["admin", "xuefa", "g_leader", "cleader"], "min_level": 20, "match_type": "pattern"},
    {"api_path": "/api/moral/semester-evaluations/list", "api_name": "查询学期末评价列表", "api_group": "学期末评价", "allowed_roles": ["admin", "xuefa", "g_leader", "cleader"], "min_level": 20},
    {"api_path": "/api/moral/semester-evaluations/{record_id}", "api_name": "查询学期末评价详情", "api_group": "学期末评价", "allowed_roles": ["admin", "xuefa", "g_leader", "cleader"], "min_level": 20, "match_type": "pattern"},
]

VALID_POLICY_MODES = {"role_and_level", "role_or_level", "role_only", "level_only", "public"}
VALID_MATCH_TYPES = {"exact", "prefix", "pattern"}

DEFAULT_OPERATION_SCOPE_RULES = {
    "/api/moral/daily-records/update": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["own_created"],
        "cleader": ["own_created"],
        "teacher": ["own_created"],
    },
    "/api/moral/daily-records/delete": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["own_created"],
        "cleader": ["own_created"],
        "teacher": ["own_created"],
    },
    "/api/moral/moment-records/update": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["own_created"],
        "cleader": ["own_created"],
        "teacher": ["own_created"],
    },
    "/api/moral/moment-records/delete": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["own_created"],
        "cleader": ["own_created"],
        "teacher": ["own_created"],
    },
    "/api/moral/timeline/export/{student_id}/xlsx": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/timeline/export/class/{class_id}": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/school-records/update": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/school-records/delete": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/punishments/update": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/punishments/revoke": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/punishments/review": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/punishment-periods/update": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/punishment-revoke-applications/approve": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/punishment-revoke-applications/reject": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/escalation-rules": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/scheduler": {
        "admin": ["all"],
    },
    "/api/moral/collective-events/update": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/collective-events/delete": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/collective-events/distributions/update": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/carryover/preview": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/carryover/logs": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/escalation-rules/student/{student_id}/history": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/escalation-rules/student/{student_id}/count": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/escalation-rules/student/{student_id}/progress": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/collective-events/student/{student_id}": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
        "student": ["own_created"],
    },
    "/api/teacher/todos/{series_id}": {
        "admin": ["own_created"],
        "jiaowu": ["own_created"],
        "xuefa": ["own_created"],
        "g_leader": ["own_created"],
        "cleader": ["own_created"],
        "teacher": ["own_created"],
    },
    "/api/teacher/todos/occurrences/{occurrence_id}/complete": {
        "admin": ["own_created", "assigned_to_me"],
        "jiaowu": ["own_created", "assigned_to_me"],
        "xuefa": ["own_created", "assigned_to_me"],
        "g_leader": ["own_created", "assigned_to_me"],
        "cleader": ["own_created", "assigned_to_me"],
        "teacher": ["own_created", "assigned_to_me"],
    },
    "/api/teacher/todos/occurrences/{occurrence_id}/reopen": {
        "admin": ["own_created", "assigned_to_me"],
        "jiaowu": ["own_created", "assigned_to_me"],
        "xuefa": ["own_created", "assigned_to_me"],
        "g_leader": ["own_created", "assigned_to_me"],
        "cleader": ["own_created", "assigned_to_me"],
        "teacher": ["own_created", "assigned_to_me"],
    },
}

PERMISSION_TEMPLATES = {
    "record_view": {
        "label": "记录查看模板",
        "data_scope_rules": {
            "admin": ["all"],
            "jiaowu": ["all"],
            "xuefa": ["all"],
            "g_leader": ["own_created", "managed_grades"],
            "cleader": ["own_created", "managed_classes"],
            "teacher": ["own_created"],
        },
        "target_scope_rules": {},
        "operation_scope_rules": {},
    },
    "record_create": {
        "label": "记录创建模板",
        "data_scope_rules": {},
        "target_scope_rules": {
            "admin": ["all_students"],
            "jiaowu": ["all_students"],
            "xuefa": ["all_students"],
            "g_leader": ["teaching_classes", "managed_grades"],
            "cleader": ["teaching_classes", "managed_classes"],
            "teacher": ["teaching_classes"],
        },
        "operation_scope_rules": {},
    },
    "record_action": {
        "label": "记录编辑删除模板",
        "data_scope_rules": {},
        "target_scope_rules": {},
        "operation_scope_rules": {
            "admin": ["all"],
            "jiaowu": ["all"],
            "xuefa": ["all"],
            "g_leader": ["own_created"],
            "cleader": ["own_created"],
            "teacher": ["own_created"],
        },
    },
    "xuefa_manage": {
        "label": "学发专管模板",
        "data_scope_rules": {"admin": ["all"], "xuefa": ["all"]},
        "target_scope_rules": {"admin": ["all_students"], "xuefa": ["all_students"]},
        "operation_scope_rules": {"admin": ["all"], "xuefa": ["all"]},
    },
    "student_archive": {
        "label": "学生档案查看模板",
        "data_scope_rules": {
            "admin": ["all"],
            "jiaowu": ["all"],
            "xuefa": ["all"],
            "g_leader": ["managed_grades"],
            "cleader": ["managed_classes"],
        },
        "target_scope_rules": {},
        "operation_scope_rules": {},
    },
}


def _infer_resource_type(api_path: str) -> str:
    mapping = [
        ("/api/moral/daily-records", "daily_record"),
        ("/api/moral/moment-records", "moment_record"),
        ("/api/moral/school-records", "school_record"),
        ("/api/moral/punishments", "punishment_record"),
        ("/api/moral/tasks", "moral_task"),
        ("/api/moral/collective-events", "collective_event"),
        ("/api/moral/timeline", "student_lifebook"),
        ("/api/moral/profiles", "student_profile"),
        ("/api/moral/consultations", "consultation"),
        ("/api/teacher/todos", "teacher_todo"),
        ("/api/dashboard/score-trend", "score_trend"),
        ("/api/dashboard", "dashboard"),
    ]
    for prefix, resource in mapping:
        if api_path.startswith(prefix):
            return resource
    return ""


def _infer_action_type(api_path: str, http_method: str = "*") -> str:
    path = api_path or ""
    method = (http_method or "*").upper()
    if "/review" in path:
        return "review"
    if "/create" in path or method == "POST" and any(token in path for token in ["/finish", "/batch", "/types"]):
        return "create"
    if any(token in path for token in ["/delete", "/revoke"]) or method == "DELETE":
        return "delete"
    if any(token in path for token in ["/update", "/close", "/review"]) or method == "PUT":
        return "update"
    if "/export" in path:
        return "export"
    if any(token in path for token in ["/trend", "/summary", "/search", "/list"]):
        return "view"
    return "view" if method == "GET" else "operate"

DEFAULT_DATA_SCOPE_RULES = {
    "/api/moral/daily-records": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["own_created", "managed_grades"],
        "cleader": ["own_created", "managed_classes"],
        "teacher": ["own_created"],
    },
    "/api/moral/daily-records/update": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["own_created"],
        "cleader": ["own_created"],
        "teacher": ["own_created"],
    },
    "/api/moral/daily-records/delete": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["own_created"],
        "cleader": ["own_created"],
        "teacher": ["own_created"],
    },
    "/api/moral/daily-records/statistics/student/{student_id}": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["own_created", "managed_grades"],
        "cleader": ["own_created", "managed_classes"],
        "teacher": ["own_created"],
    },
    "/api/moral/moment-records": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["own_created", "managed_grades"],
        "cleader": ["own_created", "managed_classes"],
        "teacher": ["own_created"],
    },
    "/api/moral/moment-records/update": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["own_created"],
        "cleader": ["own_created"],
        "teacher": ["own_created"],
    },
    "/api/moral/moment-records/delete": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["own_created"],
        "cleader": ["own_created"],
        "teacher": ["own_created"],
    },
    "/api/moral/profiles": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/profiles/student/{student_id}": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/profiles/student/{student_id}/generate": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/profiles/student/{student_id}/generate-async": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/profiles/batch-generate": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/consultations": {
        "admin": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/consultations/create": {
        "admin": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/consultations/update": {
        "admin": ["all"],
        "xuefa": ["all"],
        "g_leader": ["own_created"],
        "cleader": ["own_created"],
    },
    "/api/moral/consultations/close": {
        "admin": ["all"],
        "xuefa": ["all"],
        "g_leader": ["own_created"],
        "cleader": ["own_created"],
    },
    "/api/moral/evaluations/student/{student_id}": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
        "student": ["own_created"],
    },
    "/api/moral/evaluations/class/{class_id}": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/evaluations/grade/{grade_id}": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
    },
    "/api/moral/evaluations/calculate": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/admin/students": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/admin/students/create": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/admin/students/update": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/admin/students/batch": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/school-records": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/school-records/update": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/school-records/delete": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/punishments": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/punishments/expiring": {
        "admin": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/punishments/update": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/punishments/revoke": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/punishment-periods": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/punishment-periods/update": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/punishment-revoke-applications": {
        "admin": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/tasks/finish": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/collective-events": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/collective-events/create": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/collective-events/update": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/collective-events/delete": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/collective-events/distributions/update": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/timeline": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/timeline/search": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/timeline/export/{student_id}/xlsx": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/timeline/export/class/{class_id}": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/birthdays/upcoming": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
        "teacher": ["teaching_classes"],
    },
    "/api/moral/birthdays/today": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
        "teacher": ["teaching_classes"],
    },
    "/api/moral/semester-evaluations/{record_id}": {
        "admin": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/semester-evaluations/batch-generate": {
        "admin": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/semester-evaluations/list": {
        "admin": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/admin/grades/promote/preview": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/admin/grades/promote/execute": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/admin/logs": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
    },
    "/api/moral/ai-model-config": {
        "admin": ["all"],
    },
    "/api/moral/scheduler": {
        "admin": ["all"],
    },
    "/api/moral/escalation-rules": {
        "admin": ["all"],
        "xuefa": ["all"],
    },
    "/api/dashboard/score-trend/student/{student_id}": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/dashboard/score-trend/class/{class_id}": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "cleader": ["managed_classes"],
    },
    "/api/dashboard/score-trend/grade/{grade_id}": {
        "admin": ["all"],
        "jiaowu": ["all"],
        "xuefa": ["all"],
        "g_leader": ["managed_grades"],
    },
    "/api/teacher/todos": {
        "admin": ["own_created", "assigned_to_me"],
        "jiaowu": ["own_created", "assigned_to_me"],
        "xuefa": ["own_created", "assigned_to_me"],
        "g_leader": ["own_created", "assigned_to_me"],
        "cleader": ["own_created", "assigned_to_me"],
        "teacher": ["own_created", "assigned_to_me"],
    },
    "/api/teacher/todos/upcoming": {
        "admin": ["own_created", "assigned_to_me"],
        "jiaowu": ["own_created", "assigned_to_me"],
        "xuefa": ["own_created", "assigned_to_me"],
        "g_leader": ["own_created", "assigned_to_me"],
        "cleader": ["own_created", "assigned_to_me"],
        "teacher": ["own_created", "assigned_to_me"],
    },
}

DEFAULT_TARGET_SCOPE_RULES = {
    "/api/moral/daily-records/create": {
        "admin": ["all_students"],
        "jiaowu": ["all_students"],
        "xuefa": ["all_students"],
        "g_leader": ["teaching_classes", "managed_grades"],
        "cleader": ["teaching_classes", "managed_classes"],
        "teacher": ["teaching_classes"],
    },
    "/api/moral/daily-records/batch": {
        "admin": ["all_students"],
        "jiaowu": ["all_students"],
        "xuefa": ["all_students"],
    },
    "/api/moral/moment-records/create": {
        "admin": ["all_students"],
        "jiaowu": ["all_students"],
        "xuefa": ["all_students"],
        "g_leader": ["teaching_classes", "managed_grades"],
        "cleader": ["teaching_classes", "managed_classes"],
        "teacher": ["teaching_classes"],
    },
    "/api/moral/school-records/create": {
        "admin": ["all_students"],
        "xuefa": ["all_students"],
    },
    "/api/moral/punishments/create": {
        "admin": ["all_students"],
        "xuefa": ["all_students"],
    },
    "/api/moral/tasks/finish": {
        "admin": ["all_students"],
        "xuefa": ["all_students"],
    },
    "/api/moral/consultations/create": {
        "admin": ["all_students"],
        "xuefa": ["all_students"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/semester-evaluations/generate": {
        "admin": ["all_students"],
        "xuefa": ["all_students"],
        "g_leader": ["managed_grades"],
        "cleader": ["managed_classes"],
    },
    "/api/moral/punishment-revoke-applications/create": {
        "admin": ["all_students"],
        "cleader": ["managed_classes"],
    },
}


def _json_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _json_dump(value: Optional[List[str]]) -> str:
    return json.dumps(value or [], ensure_ascii=False)


def _json_dict(value: Any) -> Dict[str, List[str]]:
    if isinstance(value, dict):
        return {
            str(role): [str(scope) for scope in scopes]
            for role, scopes in value.items()
            if isinstance(scopes, list)
        }
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return {
                str(role): [str(scope) for scope in scopes]
                for role, scopes in parsed.items()
                if isinstance(scopes, list)
            }
    except Exception:
        pass
    return {}


def _json_dict_dump(value: Optional[Dict[str, List[str]]]) -> str:
    return json.dumps(_json_dict(value), ensure_ascii=False)


def _normalize_policy_mode(policy_mode: Optional[str]) -> str:
    return policy_mode if policy_mode in VALID_POLICY_MODES else "role_and_level"


def _normalize_match_type(match_type: Optional[str]) -> str:
    return match_type if match_type in VALID_MATCH_TYPES else "exact"


def _table_columns(db, table_name: str) -> set:
    rows = db.query_all(f"PRAGMA table_info({table_name})")
    return {row["name"] for row in rows}


def ensure_record_scope_schema(db) -> None:
    """补齐记录类表的创建人字段，用于 own_created 范围判断。"""
    additions = {
        "student_school_record": {"recorder": "TEXT"},
        "student_task_finish": {"recorder": "TEXT"},
    }
    for table_name, columns in additions.items():
        try:
            existing_columns = _table_columns(db, table_name)
        except Exception:
            continue
        if not existing_columns:
            continue
        for column, definition in columns.items():
            if column not in existing_columns:
                db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column} {definition}")


def ensure_api_permission_schema(db) -> None:
    """兼容式补齐API权限模块表和扩展列。"""
    ensure_record_scope_schema(db)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS api_permission_module (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_key TEXT NOT NULL UNIQUE,
            module_name TEXT NOT NULL,
            parent_id INTEGER,
            allowed_roles TEXT NOT NULL DEFAULT '[]',
            min_level INTEGER DEFAULT 0,
            policy_mode TEXT DEFAULT 'role_and_level',
            description TEXT,
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_api_permission_module_key ON api_permission_module(module_key)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_api_permission_module_parent ON api_permission_module(parent_id)")

    columns = _table_columns(db, "api_permission_config")
    migrations = [
        ("module_id", "ALTER TABLE api_permission_config ADD COLUMN module_id INTEGER"),
        ("http_method", "ALTER TABLE api_permission_config ADD COLUMN http_method TEXT DEFAULT '*'"),
        ("match_type", "ALTER TABLE api_permission_config ADD COLUMN match_type TEXT DEFAULT 'exact'"),
        ("policy_mode", "ALTER TABLE api_permission_config ADD COLUMN policy_mode TEXT DEFAULT 'role_and_level'"),
        ("inherit_from_module", "ALTER TABLE api_permission_config ADD COLUMN inherit_from_module INTEGER DEFAULT 0"),
        ("is_public", "ALTER TABLE api_permission_config ADD COLUMN is_public INTEGER DEFAULT 0"),
        ("enforce_backend", "ALTER TABLE api_permission_config ADD COLUMN enforce_backend INTEGER DEFAULT 1"),
        ("resource_type", "ALTER TABLE api_permission_config ADD COLUMN resource_type TEXT DEFAULT ''"),
        ("action_type", "ALTER TABLE api_permission_config ADD COLUMN action_type TEXT DEFAULT ''"),
        ("data_scope_rules", "ALTER TABLE api_permission_config ADD COLUMN data_scope_rules TEXT DEFAULT '{}'"),
        ("target_scope_rules", "ALTER TABLE api_permission_config ADD COLUMN target_scope_rules TEXT DEFAULT '{}'"),
        ("operation_scope_rules", "ALTER TABLE api_permission_config ADD COLUMN operation_scope_rules TEXT DEFAULT '{}'"),
    ]
    for column, sql in migrations:
        if column not in columns:
            db.execute(sql)

    db.execute("CREATE INDEX IF NOT EXISTS idx_api_permission_module_id ON api_permission_config(module_id)")
    _dedupe_permission_modules(db)

    # 为既有 api_group 自动生成模块，并回填 module_id。
    groups = db.query_all(
        "SELECT api_group, MIN(min_level) AS min_level FROM api_permission_config GROUP BY api_group"
    )
    for group in groups:
        group_name = group.get("api_group")
        if not group_name:
            continue
        module_key = _module_key_from_group(group_name)
        existing = db.query_one(
            "SELECT id FROM api_permission_module WHERE module_key = ? OR module_name = ? ORDER BY id LIMIT 1",
            (module_key, group_name),
        )
        if not existing:
            roles = _roles_for_group(db, group_name)
            db.execute(
                """INSERT INTO api_permission_module
                (module_key, module_name, allowed_roles, min_level, policy_mode, description)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    module_key,
                    group_name,
                    _json_dump(roles),
                    int(group.get("min_level") or 0),
                    "role_and_level",
                    f"由API分组 {group_name} 自动生成",
                ),
            )
            module_id = db.lastrowid()
        else:
            module_id = existing["id"]

        db.execute(
            "UPDATE api_permission_config SET module_id = ? WHERE api_group = ? AND module_id IS NULL",
            (module_id, group_name),
        )

    _backfill_default_scope_rules(db)


def _backfill_default_scope_rules(db) -> None:
    """为重点业务API补齐默认数据范围规则，保留管理员已有手工配置。

    对于 daily-records/create 和 moment-records/create，强制修复 teacher 的错误范围。
    """
    # 先处理正常的补齐逻辑
    for api_path, rules in DEFAULT_DATA_SCOPE_RULES.items():
        db.execute(
            """UPDATE api_permission_config
               SET data_scope_rules = ?
               WHERE api_path = ?
                 AND (data_scope_rules IS NULL OR data_scope_rules = '' OR data_scope_rules = '{}')""",
            (_json_dict_dump(rules), api_path),
        )
    for api_path, rules in DEFAULT_TARGET_SCOPE_RULES.items():
        db.execute(
            """UPDATE api_permission_config
               SET target_scope_rules = ?
               WHERE api_path = ?
                 AND (target_scope_rules IS NULL OR target_scope_rules = '' OR target_scope_rules = '{}')""",
            (_json_dict_dump(rules), api_path),
        )
    for api_path, rules in DEFAULT_OPERATION_SCOPE_RULES.items():
        db.execute(
            """UPDATE api_permission_config
               SET operation_scope_rules = ?
               WHERE api_path = ?
                 AND (operation_scope_rules IS NULL OR operation_scope_rules = '' OR operation_scope_rules = '{}')""",
            (_json_dict_dump(rules), api_path),
        )

    # 修复 teacher 的错误目标范围：从 all_students 改为 teaching_classes
    # 同时补齐 g_leader 的范围规则
    _fix_incorrect_scope_rules(db)


def _fix_incorrect_scope_rules(db) -> None:
    """修复已知的范围规则错误：
    - target_scope: teacher: all_students → teaching_classes
    - target_scope: 新增 g_leader: g_leader_grade
    - data_scope: 新增 g_leader 规则（针对日常记录、点滴记录、学生管理等API）
    - allowed_roles: 新增 g_leader 角色
    """
    # 补齐代码默认 API 配置，并同步默认 match_type/http_method。已有手工角色配置不在这里覆盖，
    # 只处理缺失行和动态路径匹配方式，避免 /student/{id} 这类接口绕过配置。
    for default_config in DEFAULT_API_PERMISSIONS:
        existing = db.query_one(
            "SELECT id, module_id FROM api_permission_config WHERE api_path = ?",
            (default_config["api_path"],),
        )
        if not existing:
            module_id = _ensure_module(
                db,
                _module_key_from_group(default_config["api_group"]),
                default_config["api_group"],
                default_config.get("allowed_roles") or [],
                int(default_config.get("min_level") or 0),
            )
            db.execute(
                """INSERT INTO api_permission_config
                   (api_path, api_name, api_group, allowed_roles, min_level, module_id,
                    http_method, match_type, policy_mode, is_active, enforce_backend,
                    resource_type, action_type, data_scope_rules, target_scope_rules, operation_scope_rules)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'role_and_level', 1, 1, ?, ?, ?, ?, ?)""",
                (
                    default_config["api_path"],
                    default_config["api_name"],
                    default_config["api_group"],
                    _json_dump(default_config.get("allowed_roles") or []),
                    int(default_config.get("min_level") or 0),
                    module_id,
                    default_config.get("http_method", "*"),
                    default_config.get("match_type", "exact"),
                    default_config.get("resource_type") or _infer_resource_type(default_config["api_path"]),
                    default_config.get("action_type") or _infer_action_type(default_config["api_path"], default_config.get("http_method", "*")),
                    _json_dict_dump(DEFAULT_DATA_SCOPE_RULES.get(default_config["api_path"], {})),
                    _json_dict_dump(DEFAULT_TARGET_SCOPE_RULES.get(default_config["api_path"], {})),
                    _json_dict_dump(DEFAULT_OPERATION_SCOPE_RULES.get(default_config["api_path"], {})),
                ),
            )
        else:
            db.execute(
                """UPDATE api_permission_config
                   SET http_method = ?, match_type = ?,
                       resource_type = COALESCE(NULLIF(resource_type, ''), ?),
                       action_type = COALESCE(NULLIF(action_type, ''), ?),
                       data_scope_rules = CASE
                           WHEN data_scope_rules IS NULL OR data_scope_rules = '' OR data_scope_rules = '{}'
                           THEN ?
                           ELSE data_scope_rules
                       END,
                       target_scope_rules = CASE
                           WHEN target_scope_rules IS NULL OR target_scope_rules = '' OR target_scope_rules = '{}'
                           THEN ?
                           ELSE target_scope_rules
                       END,
                       operation_scope_rules = CASE
                           WHEN operation_scope_rules IS NULL OR operation_scope_rules = '' OR operation_scope_rules = '{}'
                           THEN ?
                           ELSE operation_scope_rules
                       END
                   WHERE api_path = ?""",
                (
                    default_config.get("http_method", "*"),
                    default_config.get("match_type", "exact"),
                    default_config.get("resource_type") or _infer_resource_type(default_config["api_path"]),
                    default_config.get("action_type") or _infer_action_type(default_config["api_path"], default_config.get("http_method", "*")),
                    _json_dict_dump(DEFAULT_DATA_SCOPE_RULES.get(default_config["api_path"], {})),
                    _json_dict_dump(DEFAULT_TARGET_SCOPE_RULES.get(default_config["api_path"], {})),
                    _json_dict_dump(DEFAULT_OPERATION_SCOPE_RULES.get(default_config["api_path"], {})),
                    default_config["api_path"],
                ),
            )

    db.execute(
        """DELETE FROM api_permission_module
           WHERE module_name = '生日查看'
             AND NOT EXISTS (
                 SELECT 1 FROM api_permission_config c WHERE c.module_id = api_permission_module.id
             )"""
    )

    # 早期数据库把这几个“录入页依赖的查询接口”保留成了纯管理员配置，
    # 会导致教师进入日常表现页时，班级/年级下拉请求直接 403。
    # 这里只修复可识别的旧基线配置，避免覆盖管理员后续手工调整。
    lookup_api_role_repairs = {
        "/api/moral/admin/grades": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"],
        "/api/moral/admin/classes": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"],
        "/api/moral/admin/school-years": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"],
        "/api/moral/admin/semesters": ["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"],
    }
    legacy_admin_lookup_roles = {"admin", "jiaowu", "xuefa"}
    for api_path, expected_roles in lookup_api_role_repairs.items():
        config = db.query_one(
            "SELECT allowed_roles, min_level FROM api_permission_config WHERE api_path = ?",
            (api_path,),
        )
        if not config:
            continue
        try:
            existing_roles = set(json.loads(config.get("allowed_roles") or "[]"))
        except Exception:
            continue
        if existing_roles == legacy_admin_lookup_roles and int(config.get("min_level") or 0) == 0:
            db.execute(
                """UPDATE api_permission_config
                   SET allowed_roles = ?, min_level = 10
                   WHERE api_path = ?""",
                (_json_dump(expected_roles), api_path),
            )

    # 只要 API 允许 teacher 角色访问，最低等级必须为 10；否则数据库历史配置可能让教师被等级拦掉。
    teacher_configs = db.query_all("SELECT id, allowed_roles, min_level FROM api_permission_config")
    for config in teacher_configs:
        try:
            roles = json.loads(config.get("allowed_roles") or "[]")
        except Exception:
            continue
        if "teacher" in roles and int(config.get("min_level") or 0) != 10:
            db.execute(
                "UPDATE api_permission_config SET min_level = 10 WHERE id = ?",
                (config["id"],),
            )
    teacher_modules = db.query_all("SELECT id, allowed_roles, min_level FROM api_permission_module")
    for module in teacher_modules:
        try:
            roles = json.loads(module.get("allowed_roles") or "[]")
        except Exception:
            continue
        if "teacher" in roles and int(module.get("min_level") or 0) != 10:
            db.execute(
                "UPDATE api_permission_module SET min_level = 10 WHERE id = ?",
                (module["id"],),
            )

    # 修复 target_scope_rules
    for api_path in ["/api/moral/daily-records/create", "/api/moral/moment-records/create"]:
        config = db.query_one(
            "SELECT target_scope_rules FROM api_permission_config WHERE api_path = ?",
            (api_path,)
        )
        if not config:
            continue

        try:
            rules = json.loads(config.get("target_scope_rules") or "{}")
        except Exception:
            continue

        # 修复 teacher 的范围
        if "teacher" in rules and "all_students" in rules["teacher"]:
            rules["teacher"] = ["teaching_classes"]

        # 补齐 g_leader 的范围
        if "g_leader" not in rules:
            rules["g_leader"] = ["g_leader_grade"]

        db.execute(
            "UPDATE api_permission_config SET target_scope_rules = ? WHERE api_path = ?",
            (_json_dict_dump(rules), api_path),
        )

    # 修复 data_scope_rules：为相关API补齐 g_leader 规则
    apis_need_g_leader = [
        "/api/moral/daily-records",
        "/api/moral/daily-records/update",
        "/api/moral/daily-records/delete",
        "/api/moral/moment-records",
        "/api/moral/moment-records/update",
        "/api/moral/moment-records/delete",
        "/api/moral/profiles",
        "/api/moral/profiles/student/{student_id}",
        "/api/moral/profiles/student/{student_id}/generate",
        "/api/moral/profiles/student/{student_id}/generate-async",
        "/api/moral/evaluations/student/{student_id}",
        "/api/moral/evaluations/class/{class_id}",
        "/api/moral/evaluations/grade/{grade_id}",
        "/api/moral/evaluations/calculate",
        "/api/moral/admin/students",
        "/api/moral/admin/students/create",
        "/api/moral/admin/students/update",
        "/api/moral/admin/students/batch",
    ]

    for api_path in apis_need_g_leader:
        config = db.query_one(
            "SELECT data_scope_rules FROM api_permission_config WHERE api_path = ?",
            (api_path,)
        )
        if not config:
            continue

        try:
            rules = json.loads(config.get("data_scope_rules") or "{}")
        except Exception:
            continue

        # 学生管理 API 不应该有 own_created（学生表无创建者字段）
        # 正确规则：g_leader 只需 g_leader_grade
        student_apis = [
            "/api/moral/admin/students",
            "/api/moral/admin/students/create",
            "/api/moral/admin/students/batch",
            "/api/moral/admin/students/update",
        ]

        needs_fix = False
        if "g_leader" not in rules:
            needs_fix = True
        elif api_path in student_apis:
            # 学生 API：检查是否有错误的 own_created
            g_leader_rules = rules.get("g_leader", [])
            if "own_created" in g_leader_rules:
                # 移除 own_created，保留 g_leader_grade
                rules["g_leader"] = ["g_leader_grade"]
                needs_fix = True

        if needs_fix:
            if "g_leader" not in rules:
                # 根据API类型设置合适的范围
                if api_path in student_apis:
                    rules["g_leader"] = ["g_leader_grade"]
                elif api_path.endswith("/update") or api_path.endswith("/delete"):
                    rules["g_leader"] = ["own_created"]
                else:
                    rules["g_leader"] = ["own_created", "g_leader_grade"]

            db.execute(
                "UPDATE api_permission_config SET data_scope_rules = ? WHERE api_path = ?",
                (_json_dict_dump(rules), api_path),
            )

    # 补齐 allowed_roles：为相关API添加 g_leader 角色
    for api_path in apis_need_g_leader + ["/api/moral/daily-records/create", "/api/moral/moment-records/create",
                                            "/api/moral/daily-records/types", "/api/moral/birthdays/upcoming",
                                            "/api/moral/birthdays/today"]:
        config = db.query_one(
            "SELECT allowed_roles FROM api_permission_config WHERE api_path = ?",
            (api_path,)
        )
        if not config:
            continue

        try:
            roles = json.loads(config.get("allowed_roles") or "[]")
        except Exception:
            continue

        if "g_leader" not in roles:
            roles.append("g_leader")
            db.execute(
                "UPDATE api_permission_config SET allowed_roles = ? WHERE api_path = ?",
                (_json_dump(roles), api_path),
            )

    # 校级事件、处分管理、德育任务、集体事件是学发/管理员业务入口；
    # 班主任/年级主任只能通过一生一册查看授权学生的只读汇总。
    restricted_management_apis = [
        "/api/moral/school-records",
        "/api/moral/school-records/create",
        "/api/moral/school-records/update",
        "/api/moral/school-records/delete",
        "/api/moral/punishments",
        "/api/moral/punishments/create",
        "/api/moral/punishments/update",
        "/api/moral/punishments/revoke",
        "/api/moral/tasks",
        "/api/moral/tasks/finish",
        "/api/moral/collective-events",
        "/api/moral/collective-events/create",
        "/api/moral/collective-events/update",
        "/api/moral/collective-events/delete",
        "/api/moral/collective-events/distributions/update",
    ]
    for api_path in restricted_management_apis:
        db.execute(
            """UPDATE api_permission_config
               SET allowed_roles = ?, min_level = ?
               WHERE api_path = ?""",
            (_json_dump(["admin", "xuefa"]), 20, api_path),
        )

    # 修复学生画像 API 的 allowed_roles（补齐 g_leader 和 cleader）
    profile_apis = [
        "/api/moral/profiles",
        "/api/moral/profiles/student/{student_id}",
        "/api/moral/profiles/student/{student_id}/generate",
        "/api/moral/profiles/student/{student_id}/generate-async",
        "/api/moral/profiles/batch-generate"
    ]
    for api_path in profile_apis:
        config = db.query_one(
            "SELECT allowed_roles FROM api_permission_config WHERE api_path = ?",
            (api_path,)
        )
        if not config:
            continue
        try:
            roles = json.loads(config.get("allowed_roles") or "[]")
        except Exception:
            continue
        if "g_leader" not in roles:
            roles.append("g_leader")
        if "cleader" not in roles:
            roles.append("cleader")
        db.execute(
            "UPDATE api_permission_config SET allowed_roles = ? WHERE api_path = ?",
            (_json_dump(roles), api_path),
        )

    # 确保 consultation API 权限配置存在
    consultation_apis = [
        ("/api/moral/consultations", "获取诊疗会话列表"),
        ("/api/moral/consultations/create", "创建诊疗会话"),
        ("/api/moral/consultations/update", "更新诊疗会话"),
        ("/api/moral/consultations/close", "关闭诊疗会话"),
    ]
    for api_path, api_name in consultation_apis:
        exists = db.query_one(
            "SELECT 1 FROM api_permission_config WHERE api_path = ?",
            (api_path,)
        )
        if not exists:
            db.execute(
                """INSERT INTO api_permission_config
                   (api_path, api_name, api_group, allowed_roles, min_level, is_active)
                   VALUES (?, ?, 'AI诊疗', ?, 20, 1)""",
                (api_path, api_name, _json_dump(["admin", "xuefa", "g_leader", "cleader"])),
            )


def apply_permission_fix_on_startup() -> None:
    """启动时应用权限范围修复。

    修复 teacher 的错误范围（all_students → teaching_classes）
    以及补齐 g_leader 的范围规则。
    """
    try:
        with get_moral_db() as db:
            # 先确保表存在
            ensure_api_permission_schema(db)
            # 应用修复
            _fix_incorrect_scope_rules(db)
            logger.info("[APIPermission] Permission scope fix applied on startup")
    except Exception as e:
        logger.warning(f"[APIPermission] Permission fix failed on startup: {e}")


def _module_key_from_group(group_name: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z_]+", "_", group_name.strip()).strip("_")
    if slug:
        return slug
    digest = hashlib.md5(group_name.encode("utf-8")).hexdigest()[:12]
    return f"module_{digest}"


def _dedupe_permission_modules(db) -> None:
    """按模块名称合并历史自动生成的重复模块。"""
    duplicates = db.query_all(
        """SELECT module_name, MIN(id) AS keep_id, COUNT(*) AS c
           FROM api_permission_module
           GROUP BY module_name
           HAVING COUNT(*) > 1"""
    )
    for item in duplicates:
        module_name = item["module_name"]
        keep_id = item["keep_id"]
        dupes = db.query_all(
            "SELECT id FROM api_permission_module WHERE module_name = ? AND id != ?",
            (module_name, keep_id),
        )
        for dupe in dupes:
            db.execute(
                "UPDATE api_permission_config SET module_id = ? WHERE module_id = ?",
                (keep_id, dupe["id"]),
            )
            db.execute("DELETE FROM api_permission_module WHERE id = ?", (dupe["id"],))


def _roles_for_group(db, group_name: str) -> List[str]:
    rows = db.query_all(
        "SELECT allowed_roles FROM api_permission_config WHERE api_group = ?",
        (group_name,),
    )
    roles = set()
    for row in rows:
        roles.update(_json_list(row.get("allowed_roles")))
    return sorted(roles)


def _ensure_module(db, module_key: str, module_name: str, allowed_roles: Optional[List[str]] = None, min_level: int = 0) -> int:
    module = db.query_one(
        "SELECT id FROM api_permission_module WHERE module_key = ? OR module_name = ? ORDER BY id LIMIT 1",
        (module_key, module_name),
    )
    if module:
        return module["id"]
    db.execute(
        """INSERT INTO api_permission_module
        (module_key, module_name, allowed_roles, min_level, policy_mode, description)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (
            module_key,
            module_name,
            _json_dump(allowed_roles or []),
            min_level,
            "role_and_level",
            "系统同步生成",
        ),
    )
    return db.lastrowid()


def _sync_legacy_api_level_yaml(db) -> Dict[str, int]:
    """将 lesson/config/api_level.yaml 同步到数据库权限配置。"""
    try:
        from config.config import Config
    except Exception as exc:
        logger.warning("无法导入Config，跳过api_level.yaml同步: %s", exc)
        return {"created": 0, "updated": 0, "skipped": 0}

    cfg_all = Config().get_config_all("api_level.yaml")
    routes = cfg_all.get("routes", {}) or {}
    module_id = _ensure_module(db, "legacy_lesson_api", "旧版教务接口", ["admin"], 0)
    created = 0
    updated = 0
    skipped = 0

    for raw_path, rule in routes.items():
        rule = rule or {}
        api_path = raw_path if raw_path.startswith("/api/") else f"/api{raw_path}"
        allowed_roles = rule.get("allowed_roles") or []
        is_public = 1 if rule.get("jwt_required") is False or "all" in allowed_roles else 0
        normalized_roles = [role for role in allowed_roles if role != "all"]
        min_level = int(rule.get("min_level") or 0)
        match_type = "pattern" if "{" in raw_path and "}" in raw_path else "exact"
        api_name = f"旧版接口 {raw_path}"

        existing = db.query_one("SELECT id FROM api_permission_config WHERE api_path = ?", (api_path,))
        if existing:
            db.execute(
                """UPDATE api_permission_config
                   SET module_id = COALESCE(module_id, ?),
                       api_group = CASE WHEN api_group = '' THEN ? ELSE api_group END,
                       allowed_roles = ?,
                       min_level = ?,
                       http_method = COALESCE(http_method, '*'),
                       match_type = ?,
                       policy_mode = COALESCE(policy_mode, 'role_and_level'),
                       is_public = ?,
                       updated_at = datetime('now', 'localtime')
                   WHERE id = ?""",
                (
                    module_id,
                    "旧版教务接口",
                    _json_dump(normalized_roles),
                    min_level,
                    match_type,
                    is_public,
                    existing["id"],
                ),
            )
            updated += 1
            continue

        db.execute(
            """INSERT INTO api_permission_config
            (api_path, api_name, api_group, allowed_roles, min_level, module_id,
             http_method, match_type, policy_mode, is_public, enforce_backend, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                api_path,
                api_name,
                "旧版教务接口",
                _json_dump(normalized_roles),
                min_level,
                module_id,
                "*",
                match_type,
                "role_and_level",
                is_public,
                1,
                "由 lesson/config/api_level.yaml 同步",
            ),
        )
        created += 1

    return {"created": created, "updated": updated, "skipped": skipped}


def _path_matches(api_path: str, request_path: str, match_type: str) -> bool:
    match_type = _normalize_match_type(match_type)
    if match_type == "prefix":
        return request_path.startswith(api_path)
    if match_type == "pattern":
        api_parts = [p for p in api_path.strip("/").split("/") if p]
        req_parts = [p for p in request_path.strip("/").split("/") if p]
        if len(api_parts) != len(req_parts):
            return False
        return all(ap == rp or (ap.startswith("{") and ap.endswith("}")) for ap, rp in zip(api_parts, req_parts))
    return api_path == request_path


def _get_matching_config(db, api_path: str, http_method: str = "*") -> Optional[Dict[str, Any]]:
    configs = db.query_all(
        """
        SELECT c.*, m.module_name, m.allowed_roles AS module_allowed_roles,
               m.min_level AS module_min_level, m.policy_mode AS module_policy_mode,
               m.is_active AS module_is_active
        FROM api_permission_config c
        LEFT JOIN api_permission_module m ON c.module_id = m.id
        WHERE c.is_active = 1
        ORDER BY
            CASE c.match_type WHEN 'exact' THEN 0 WHEN 'pattern' THEN 1 ELSE 2 END,
            LENGTH(c.api_path) DESC
        """
    )
    method = (http_method or "*").upper()
    for config in configs:
        config_method = (config.get("http_method") or "*").upper()
        if config_method not in ("*", method):
            continue
        if config.get("module_is_active") == 0:
            continue
        if _path_matches(config.get("api_path") or "", api_path, config.get("match_type") or "exact"):
            return config
    return None


def _effective_policy(config: Dict[str, Any]) -> Dict[str, Any]:
    inherit = int(config.get("inherit_from_module") or 0) == 1
    if inherit:
        allowed_roles = _json_list(config.get("module_allowed_roles"))
        min_level = int(config.get("module_min_level") or 0)
        policy_mode = _normalize_policy_mode(config.get("module_policy_mode"))
    else:
        allowed_roles = _json_list(config.get("allowed_roles"))
        min_level = int(config.get("min_level") or 0)
        policy_mode = _normalize_policy_mode(config.get("policy_mode"))

    if int(config.get("is_public") or 0) == 1:
        policy_mode = "public"

    return {
        "allowed_roles": allowed_roles,
        "min_level": min_level,
        "policy_mode": policy_mode,
        "is_public": int(config.get("is_public") or 0),
        "inherit_from_module": int(config.get("inherit_from_module") or 0),
    }


def is_api_allowed(user: User, config: Dict[str, Any]) -> Dict[str, Any]:
    """按统一语义判断API权限。默认角色和等级同时生效。"""
    policy = _effective_policy(config)
    if policy["policy_mode"] == "public" or policy["is_public"] == 1:
        return {"allowed": True, "reason": "公开API无需鉴权", "policy": policy}

    if not user:
        return {"allowed": False, "reason": "未登录", "policy": policy}

    if is_admin_user(user):
        return {"allowed": True, "reason": "admin拥有所有权限", "policy": policy}

    user_roles = get_user_roles(user)
    user_level = get_user_role_level(user)
    allowed_roles = policy["allowed_roles"]
    min_level = policy["min_level"]
    role_pass = not allowed_roles or any(role in allowed_roles for role in user_roles)
    level_pass = min_level <= 0 or user_level >= min_level
    mode = policy["policy_mode"]

    if mode == "role_only":
        allowed = role_pass
    elif mode == "level_only":
        allowed = level_pass
    elif mode == "role_or_level":
        allowed = role_pass or level_pass
    else:
        allowed = role_pass and level_pass

    reason = "允许" if allowed else f"无权限：角色={user_roles}，等级={user_level}，要求角色={allowed_roles}，最低等级={min_level}"
    return {"allowed": allowed, "reason": reason, "policy": policy}


def check_configured_api_permission(
    user: User,
    api_path: str,
    http_method: str = "*",
    *,
    allow_missing: bool = True,
) -> Dict[str, Any]:
    """
    使用 api_permission_config 做后端统一鉴权。

    allow_missing=True 时，未配置的 API 仍回退到原有代码内权限判断；
    已配置且 enforce_backend=1 的 API 必须满足配置中的角色、等级和策略。
    """
    with get_moral_db() as db:
        ensure_api_permission_schema(db)
        config = _get_matching_config(db, api_path, http_method)
        if not config:
            return {
                "allowed": bool(allow_missing),
                "reason": "无权限配置，默认允许" if allow_missing else "无权限配置",
                "policy": {},
                "config": None,
            }

        # Batch77: 修复 enforce_backend=0 判定逻辑
        # enforce_backend 字段：0=不启用后端鉴权（放行），1=启用，None/缺失=默认启用
        enforce_backend_val = config.get("enforce_backend")
        if enforce_backend_val is not None and int(enforce_backend_val) == 0:
            return {
                "allowed": True,
                "reason": "该API未启用后端配置鉴权",
                "policy": _effective_policy(config),
                "config": config,
            }

        decision = is_api_allowed(user, config)
        decision["config"] = config
        return decision


def require_configured_api_permission(
    api_path: str,
    http_method: str = "*",
    *,
    allow_missing: bool = True,
):
    """FastAPI 依赖：按 api_permission_config 校验当前用户能否调用 API。"""
    async def check(user: User = Depends(get_current_user)):
        decision = check_configured_api_permission(
            user,
            api_path,
            http_method,
            allow_missing=allow_missing,
        )
        if not decision["allowed"]:
            raise HTTPException(status_code=403, detail=decision["reason"])
        return user

    return check


# =============================================================================
# 统一鉴权入口 - 支持数据库配置 + YAML fallback
# =============================================================================

def _match_route_yaml(path: str, pattern: str) -> bool:
    """YAML路由匹配逻辑"""
    path_parts = [p for p in path.strip("/").split("/") if p != ""]
    pattern_parts = [p for p in pattern.strip("/").split("/") if p != ""]
    if len(path_parts) != len(pattern_parts):
        return False
    for pp, tp in zip(path_parts, pattern_parts):
        if tp.startswith("{") and tp.endswith("}"):
            continue
        if pp != tp:
            return False
    return True


def _get_yaml_rule(path: str) -> Dict[str, Any]:
    """获取YAML配置的API规则"""
    norm_path = path
    if norm_path.startswith("/api/"):
        norm_path = norm_path[4:]
    try:
        cfg_all = Config().get_config_all("api_level.yaml")
    except Exception:
        cfg_all = {}
    defaults = cfg_all.get("defaults", {})
    routes = cfg_all.get("routes", {})
    for patt, conf in routes.items():
        if _match_route_yaml(norm_path, patt):
            merged = dict(defaults)
            merged.update(conf or {})
            return merged
    return defaults


def _check_yaml_permission(user: Optional[User], rule: Dict[str, Any]) -> Dict[str, Any]:
    """基于YAML规则的权限检查"""
    allowed_roles = rule.get("allowed_roles", [])
    min_level = int(rule.get("min_level", 0))
    jwt_required = rule.get("jwt_required", True)

    # 公开API判断
    if "all" in allowed_roles and min_level == 0:
        return {"allowed": True, "reason": "公开API (yaml)", "source": "yaml"}
    if not jwt_required:
        return {"allowed": True, "reason": "jwt_required=false (yaml)", "source": "yaml"}

    # 需要登录
    if not user:
        return {"allowed": False, "reason": "未登录", "source": "yaml"}

    # admin放行
    if is_admin_user(user):
        return {"allowed": True, "reason": "admin拥有所有权限", "source": "yaml"}

    # 角色检查
    user_roles = get_user_roles(user)
    user_level = get_user_role_level(user)
    if allowed_roles and not any(role in allowed_roles for role in user_roles):
        return {"allowed": False, "reason": f"角色不允许: {user_roles} vs {allowed_roles}", "source": "yaml"}
    if user_level < min_level:
        return {"allowed": False, "reason": f"等级不足: {user_level} < {min_level}", "source": "yaml"}

    return {"allowed": True, "reason": "权限通过", "source": "yaml"}


def unified_api_permission(
    api_path: str,
    http_method: str = "*",
    *,
    allow_missing: bool = True,
):
    """
    统一鉴权入口 - 支持JWT和微信token双通道。

    auth_mode字段控制通道选择：
    - 'jwt': 仅JWT鉴权（默认）
    - 'wechat_token': 仅微信token鉴权
    - 'both': JWT或微信token均可

    公开API (is_public=1) 不强制要求token。
    """
    async def check(
        request: Request,
        user: Optional[User] = Depends(get_current_user_optional),
    ):
        # 1. 先查数据库配置
        with get_moral_db() as db:
            ensure_api_permission_schema(db)
            config = _get_matching_config(db, api_path, http_method)

        if config:
            # 数据库有配置 → 用数据库规则
            # is_public=1 时，直接放行
            if int(config.get("is_public") or 0) == 1:
                return user

            # 获取auth_mode配置
            auth_mode = config.get("auth_mode") or "jwt"

            # 公开API（policy_mode='public'）放行
            policy = _effective_policy(config)
            if policy.get("policy_mode") == "public":
                return user

            # JWT通道
            if auth_mode in ("jwt", "both"):
                if user:
                    decision = is_api_allowed(user, config)
                    if decision["allowed"]:
                        return user
                    # JWT失败，如果是both模式继续尝试微信通道
                    if auth_mode != "both":
                        raise HTTPException(status_code=403, detail=decision["reason"])

            # 微信token通道
            if auth_mode in ("wechat_token", "both"):
                try:
                    from models.datas_api.wechat_auth import get_wechat_identity, check_wechat_permission
                    wechat_identity = get_wechat_identity(request)
                    if wechat_identity and wechat_identity.get("wxid"):
                        decision = check_wechat_permission(wechat_identity, config)
                        if decision["allowed"]:
                            return wechat_identity
                except Exception as e:
                    logger.warning(f"微信token鉴权失败: {e}")

            # 双通道都失败
            if auth_mode == "both":
                raise HTTPException(status_code=401, detail="JWT或微信token认证失败")

            # 单通道失败
            if auth_mode == "jwt":
                if not user:
                    raise HTTPException(status_code=401, detail="未登录")
                raise HTTPException(status_code=403, detail="JWT权限不足")

            if auth_mode == "wechat_token":
                raise HTTPException(status_code=401, detail="微信token无效")

        # 2. 数据库无配置 → fallback到YAML（仅JWT通道）
        rule = _get_yaml_rule(api_path)

        # YAML公开API
        if "all" in rule.get("allowed_roles", []) and int(rule.get("min_level", 0)) == 0:
            return user
        if not rule.get("jwt_required", True):
            return user

        # YAML需要登录
        if not user:
            raise HTTPException(status_code=401, detail="未登录")

        decision = _check_yaml_permission(user, rule)
        if not decision["allowed"]:
            raise HTTPException(status_code=403, detail=decision["reason"])
        return user

    return check


def _parse_config_row(config: Dict[str, Any]) -> Dict[str, Any]:
    config["allowed_roles"] = _json_list(config.get("allowed_roles"))
    config["data_scope_rules"] = _json_dict(config.get("data_scope_rules"))
    config["target_scope_rules"] = _json_dict(config.get("target_scope_rules"))
    config["operation_scope_rules"] = _json_dict(config.get("operation_scope_rules"))
    config["resource_type"] = config.get("resource_type") or _infer_resource_type(config.get("api_path") or "")
    config["action_type"] = config.get("action_type") or _infer_action_type(config.get("api_path") or "", config.get("http_method") or "*")
    if config.get("module_allowed_roles") is not None:
        config["module_allowed_roles"] = _json_list(config.get("module_allowed_roles"))
    config["effective_policy"] = _effective_policy(config)
    config["risk_flags"] = _permission_risk_flags(config)
    return config


def _permission_risk_flags(config: Dict[str, Any]) -> List[str]:
    risks: List[str] = []
    action_type = config.get("action_type") or ""
    api_path = config.get("api_path") or ""
    allowed_roles = set(_json_list(config.get("allowed_roles")))
    data_rules = config.get("data_scope_rules") or {}
    target_rules = config.get("target_scope_rules") or {}
    operation_rules = config.get("operation_scope_rules") or {}
    role_scope_expectations = {
        "view": data_rules,
        "create": target_rules,
        "update": operation_rules,
        "delete": operation_rules,
        "review": operation_rules,
        "export": operation_rules,
    }
    if "{" in api_path and "}" in api_path and (config.get("match_type") or "exact") != "pattern":
        risks.append("动态路径建议使用参数模式")
    if int(config.get("enforce_backend") or 0) == 0:
        risks.append("未参与后端统一鉴权")
    if int(config.get("is_public") or 0) == 1 and api_path not in EXPECTED_PUBLIC_API_PATHS:
        risks.append("公开接口")
    if action_type == "view" and not data_rules:
        risks.append("查看动作未配置数据范围")
    if action_type == "create" and not target_rules:
        risks.append("创建动作未配置目标范围")
    if action_type in {"update", "delete", "review", "export"} and not operation_rules:
        risks.append("动作范围未配置")
    for scope_name, rules in {
        "数据范围": data_rules,
        "目标范围": target_rules,
        "动作范围": operation_rules,
    }.items():
        extra_roles = sorted(set(rules.keys()) - allowed_roles)
        if extra_roles:
            risks.append(f"{scope_name}存在未授权角色：{'、'.join(extra_roles)}")
    expected_rules = role_scope_expectations.get(action_type)
    if expected_rules is not None and expected_rules:
        missing_roles = sorted(allowed_roles - set(expected_rules.keys()))
        if missing_roles:
            risks.append(f"允许角色缺少对应范围：{'、'.join(missing_roles)}")
    return risks


def _build_permission_audit(configs: List[Dict[str, Any]]) -> Dict[str, Any]:
    risk_counter: Dict[str, int] = {}
    module_counter: Dict[str, int] = {}
    action_counter: Dict[str, int] = {}
    risky_items: List[Dict[str, Any]] = []

    for config in configs:
        parsed = _parse_config_row(dict(config))
        risks = parsed.get("risk_flags") or []
        module_name = parsed.get("module_name") or parsed.get("api_group") or "未分组"
        action_type = parsed.get("action_type") or "unknown"

        if risks:
            module_counter[module_name] = module_counter.get(module_name, 0) + 1
            action_counter[action_type] = action_counter.get(action_type, 0) + 1
            for risk in risks:
                risk_counter[risk] = risk_counter.get(risk, 0) + 1
            risky_items.append(
                {
                    "id": parsed.get("id"),
                    "module_id": parsed.get("module_id"),
                    "api_name": parsed.get("api_name"),
                    "api_path": parsed.get("api_path"),
                    "module_name": module_name,
                    "action_type": action_type,
                    "risk_flags": risks,
                }
            )

    return {
        "summary": {
            "total": len(configs),
            "risky": len(risky_items),
            "healthy": len(configs) - len(risky_items),
        },
        "risk_counts": [
            {"label": label, "count": count}
            for label, count in sorted(risk_counter.items(), key=lambda item: (-item[1], item[0]))
        ],
        "module_counts": [
            {"label": label, "count": count}
            for label, count in sorted(module_counter.items(), key=lambda item: (-item[1], item[0]))
        ],
        "action_counts": [
            {"label": label, "count": count}
            for label, count in sorted(action_counter.items(), key=lambda item: (-item[1], item[0]))
        ],
        "items": risky_items,
    }


# =============================================================================
# API路由
# =============================================================================

def require_admin(user: User = Depends(get_current_user)):
    """仅admin可访问"""
    if not is_admin_user(user):
        raise HTTPException(403, "仅管理员可访问")
    return user


@router.get("", summary="获取API权限配置列表")
async def get_api_permissions(
    api_group: Optional[str] = Query(None, description="API分组筛选"),
    user: User = Depends(require_admin)
):
    """获取API权限配置列表（仅admin）"""
    with get_moral_db() as db:
        ensure_api_permission_schema(db)
        if api_group:
            configs = db.query_all(
                """SELECT c.*, m.module_name, m.allowed_roles AS module_allowed_roles,
                          m.min_level AS module_min_level, m.policy_mode AS module_policy_mode,
                          m.is_active AS module_is_active
                   FROM api_permission_config c
                   LEFT JOIN api_permission_module m ON c.module_id = m.id
                   WHERE c.api_group = ?
                   ORDER BY c.api_group, c.api_path""",
                (api_group,)
            )
        else:
            configs = db.query_all(
                """SELECT c.*, m.module_name, m.allowed_roles AS module_allowed_roles,
                          m.min_level AS module_min_level, m.policy_mode AS module_policy_mode,
                          m.is_active AS module_is_active
                   FROM api_permission_config c
                   LEFT JOIN api_permission_module m ON c.module_id = m.id
                   ORDER BY c.api_group, c.api_path"""
            )

        for config in configs:
            _parse_config_row(config)

        return {"success": True, "data": configs}


@router.get("/modules", summary="获取API权限模块列表")
async def get_api_permission_modules(user: User = Depends(require_admin)):
    """获取API权限模块列表（仅admin）"""
    with get_moral_db() as db:
        ensure_api_permission_schema(db)
        modules = db.query_all(
            """SELECT m.*,
                      COUNT(c.id) AS api_count
               FROM api_permission_module m
               LEFT JOIN api_permission_config c ON c.module_id = m.id
               GROUP BY m.id
               ORDER BY m.sort_order, m.module_name"""
        )
        for module in modules:
            module["allowed_roles"] = _json_list(module.get("allowed_roles"))
        return {"success": True, "data": modules}


@router.post("/modules", summary="创建API权限模块")
async def create_api_permission_module(
    module: ApiPermissionModuleCreate,
    request: Request,
    user: User = Depends(require_admin),
):
    """创建API权限模块（仅admin）"""
    with get_moral_db() as db:
        ensure_api_permission_schema(db)
        existing = db.query_one(
            "SELECT id FROM api_permission_module WHERE module_key = ?",
            (module.module_key,),
        )
        if existing:
            raise HTTPException(400, f"模块标识 {module.module_key} 已存在")

        db.execute(
            """INSERT INTO api_permission_module
            (module_key, module_name, parent_id, allowed_roles, min_level, policy_mode, description, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                module.module_key,
                module.module_name,
                module.parent_id,
                _json_dump(module.allowed_roles),
                module.min_level,
                _normalize_policy_mode(module.policy_mode),
                module.description,
                module.sort_order,
            ),
        )
        module_id = db.lastrowid()
        log_operation(db, user.username, user.role, "INSERT", "api_permission_module", module_id, new_data=module.dict())
        return {"success": True, "message": "模块创建成功", "data": {"id": module_id}}


@router.put("/modules/{module_id}", summary="更新API权限模块")
async def update_api_permission_module(
    module_id: int,
    module: ApiPermissionModuleUpdate,
    request: Request,
    user: User = Depends(require_admin),
):
    """更新API权限模块（仅admin）"""
    with get_moral_db() as db:
        ensure_api_permission_schema(db)
        existing = db.query_one("SELECT * FROM api_permission_module WHERE id = ?", (module_id,))
        if not existing:
            raise HTTPException(404, "模块不存在")

        updates = []
        params = []
        for field in ["module_key", "module_name", "parent_id", "min_level", "description", "sort_order", "is_active"]:
            value = getattr(module, field)
            if value is not None:
                updates.append(f"{field} = ?")
                params.append(value)

        if module.allowed_roles is not None:
            updates.append("allowed_roles = ?")
            params.append(_json_dump(module.allowed_roles))
        if module.policy_mode is not None:
            updates.append("policy_mode = ?")
            params.append(_normalize_policy_mode(module.policy_mode))

        updates.append("updated_at = datetime('now', 'localtime')")
        params.append(module_id)
        db.execute(f"UPDATE api_permission_module SET {', '.join(updates)} WHERE id = ?", tuple(params))
        log_operation(db, user.username, user.role, "UPDATE", "api_permission_module", module_id, new_data=module.dict(exclude_unset=True))
        return {"success": True, "message": "模块更新成功"}


@router.post("/modules/{module_id}/apply", summary="将模块权限应用到模块内API")
async def apply_module_permission(
    module_id: int,
    request: Request,
    user: User = Depends(require_admin),
):
    """将模块权限批量写入模块下API，并取消单API覆盖。"""
    with get_moral_db() as db:
        ensure_api_permission_schema(db)
        module = db.query_one("SELECT * FROM api_permission_module WHERE id = ?", (module_id,))
        if not module:
            raise HTTPException(404, "模块不存在")
        affected = db.execute(
            """UPDATE api_permission_config
               SET allowed_roles = ?, min_level = ?, policy_mode = ?,
                   inherit_from_module = 1, api_group = ?,
                   updated_at = datetime('now', 'localtime')
               WHERE module_id = ?""",
            (
                module["allowed_roles"],
                module["min_level"],
                module["policy_mode"],
                module["module_name"],
                module_id,
            ),
        )
        log_operation(db, user.username, user.role, "APPLY", "api_permission_module", module_id, new_data={"affected": affected})
        return {"success": True, "message": f"已应用到 {affected} 个API"}


@router.get("/templates", summary="获取API权限模板")
async def get_api_permission_templates(user: User = Depends(require_admin)):
    return {
        "success": True,
        "data": [
            {"key": key, "label": payload["label"]}
            for key, payload in PERMISSION_TEMPLATES.items()
        ],
    }


@router.post("/templates/apply", summary="批量套用API权限模板")
async def apply_api_permission_template(
    payload: ApiPermissionTemplateApply,
    request: Request,
    user: User = Depends(require_admin),
):
    template = PERMISSION_TEMPLATES.get(payload.template_key)
    if not template:
        raise HTTPException(400, "模板不存在")
    if not payload.config_ids:
        raise HTTPException(400, "请选择需要更新的API")

    with get_moral_db() as db:
        ensure_api_permission_schema(db)
        updated = 0
        for config_id in payload.config_ids:
            existing = db.query_one("SELECT id FROM api_permission_config WHERE id = ?", (config_id,))
            if not existing:
                continue
            db.execute(
                """UPDATE api_permission_config
                   SET data_scope_rules = ?, target_scope_rules = ?, operation_scope_rules = ?,
                       updated_at = datetime('now', 'localtime')
                   WHERE id = ?""",
                (
                    _json_dict_dump(template["data_scope_rules"]),
                    _json_dict_dump(template["target_scope_rules"]),
                    _json_dict_dump(template["operation_scope_rules"]),
                    config_id,
                ),
            )
            updated += 1
        log_operation(
            db,
            user.username,
            user.role,
            "APPLY_TEMPLATE",
            "api_permission_config",
            None,
            new_data={"template": payload.template_key, "updated": updated, "config_ids": payload.config_ids},
        )
        return {"success": True, "message": f"已套用模板到 {updated} 条API", "data": {"updated": updated}}


@router.post("/audit", summary="巡检API权限配置风险")
async def audit_api_permissions(
    payload: ApiPermissionAuditRequest,
    user: User = Depends(require_admin),
):
    with get_moral_db() as db:
        ensure_api_permission_schema(db)
        params: List[Any] = []
        where_sql = ""
        if payload.config_ids:
            placeholders = ",".join("?" for _ in payload.config_ids)
            where_sql = f"WHERE c.id IN ({placeholders})"
            params.extend(payload.config_ids)
        configs = db.query_all(
            f"""SELECT c.*, m.module_name, m.allowed_roles AS module_allowed_roles,
                       m.min_level AS module_min_level, m.policy_mode AS module_policy_mode,
                       m.is_active AS module_is_active
                FROM api_permission_config c
                LEFT JOIN api_permission_module m ON c.module_id = m.id
                {where_sql}
                ORDER BY c.api_group, c.api_path""",
            tuple(params),
        )
        return {"success": True, "data": _build_permission_audit(configs)}


@router.post("/sync-legacy-yaml", summary="同步旧版YAML权限配置")
async def sync_legacy_yaml_permissions(
    request: Request,
    user: User = Depends(require_admin),
):
    """将 lesson/config/api_level.yaml 导入统一API权限配置（仅admin）。"""
    with get_moral_db() as db:
        ensure_api_permission_schema(db)
        result = _sync_legacy_api_level_yaml(db)
        log_operation(db, user.username, user.role, "SYNC", "api_permission_config", None, new_data=result)
        return {
            "success": True,
            "message": f"同步完成：新增 {result['created']} 条，更新 {result['updated']} 条",
            "data": result,
        }


@router.post("/sync-default-scope-rules", summary="强制同步默认数据范围规则")
async def sync_default_scope_rules(
    request: Request,
    force: int = Query(0, description="强制覆盖已有配置，默认只补齐空配置"),
    user: User = Depends(require_admin),
):
    """将代码中的 DEFAULT_DATA_SCOPE_RULES 和 DEFAULT_TARGET_SCOPE_RULES 同步到数据库。

    Args:
        force: 0=只补齐空配置，1=强制覆盖所有配置

    Returns:
        更新统计
    """
    with get_moral_db() as db:
        ensure_api_permission_schema(db)
        updated_data_scope = 0
        updated_target_scope = 0
        updated_operation_scope = 0

        # 同步数据范围规则
        for api_path, rules in DEFAULT_DATA_SCOPE_RULES.items():
            if force:
                # 强制覆盖
                db.execute(
                    "UPDATE api_permission_config SET data_scope_rules = ? WHERE api_path = ?",
                    (_json_dict_dump(rules), api_path),
                )
                updated_data_scope += 1
            else:
                # 只补齐空配置
                result = db.execute(
                    """UPDATE api_permission_config
                       SET data_scope_rules = ?
                       WHERE api_path = ?
                         AND (data_scope_rules IS NULL OR data_scope_rules = '' OR data_scope_rules = '{}')""",
                    (_json_dict_dump(rules), api_path),
                )
                if result:
                    updated_data_scope += 1

        # 同步目标范围规则
        for api_path, rules in DEFAULT_TARGET_SCOPE_RULES.items():
            if force:
                db.execute(
                    "UPDATE api_permission_config SET target_scope_rules = ? WHERE api_path = ?",
                    (_json_dict_dump(rules), api_path),
                )
                updated_target_scope += 1
            else:
                result = db.execute(
                    """UPDATE api_permission_config
                       SET target_scope_rules = ?
                       WHERE api_path = ?
                         AND (target_scope_rules IS NULL OR target_scope_rules = '' OR target_scope_rules = '{}')""",
                    (_json_dict_dump(rules), api_path),
                )
                if result:
                    updated_target_scope += 1

        for api_path, rules in DEFAULT_OPERATION_SCOPE_RULES.items():
            if force:
                db.execute(
                    "UPDATE api_permission_config SET operation_scope_rules = ? WHERE api_path = ?",
                    (_json_dict_dump(rules), api_path),
                )
                updated_operation_scope += 1
            else:
                result = db.execute(
                    """UPDATE api_permission_config
                       SET operation_scope_rules = ?
                       WHERE api_path = ?
                         AND (operation_scope_rules IS NULL OR operation_scope_rules = '' OR operation_scope_rules = '{}')""",
                    (_json_dict_dump(rules), api_path),
                )
                if result:
                    updated_operation_scope += 1

        # 补齐 g_leader allowed_roles
        _fix_incorrect_scope_rules(db)

        log_operation(
            db, user.username, user.role, "SYNC_SCOPE", "api_permission_config", None,
            new_data={
                "data_scope": updated_data_scope,
                "target_scope": updated_target_scope,
                "operation_scope": updated_operation_scope,
                "force": force,
            }
        )

        return {
            "success": True,
            "message": (
                f"同步完成：数据范围更新 {updated_data_scope} 条，"
                f"目标范围更新 {updated_target_scope} 条，动作范围更新 {updated_operation_scope} 条"
            ),
            "data": {
                "updated_data_scope": updated_data_scope,
                "updated_target_scope": updated_target_scope,
                "updated_operation_scope": updated_operation_scope,
                "force": force,
            },
        }


@router.post("", summary="创建API权限配置")
async def create_api_permission(
    config: ApiPermissionCreate,
    request: Request,
    user: User = Depends(require_admin)
):
    """创建API权限配置（仅admin）"""
    with get_moral_db() as db:
        ensure_api_permission_schema(db)
        # 检查是否已存在
        existing = db.query_one(
            "SELECT id FROM api_permission_config WHERE api_path = ?",
            (config.api_path,)
        )
        if existing:
            raise HTTPException(400, f"API路径 {config.api_path} 已存在")

        allowed_roles_json = _json_dump(config.allowed_roles)
        module_id = config.module_id
        if not module_id and config.api_group:
            module = db.query_one(
                "SELECT id FROM api_permission_module WHERE module_name = ?",
                (config.api_group,),
            )
            module_id = module["id"] if module else None

        db.execute(
            """INSERT INTO api_permission_config
            (api_path, api_name, api_group, allowed_roles, min_level, module_id, http_method,
             match_type, policy_mode, inherit_from_module, is_public, enforce_backend,
             resource_type, action_type, data_scope_rules, target_scope_rules, operation_scope_rules, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                config.api_path,
                config.api_name,
                config.api_group,
                allowed_roles_json,
                config.min_level,
                module_id,
                (config.http_method or "*").upper(),
                _normalize_match_type(config.match_type),
                _normalize_policy_mode(config.policy_mode),
                config.inherit_from_module,
                config.is_public,
                config.enforce_backend,
                config.resource_type or _infer_resource_type(config.api_path),
                config.action_type or _infer_action_type(config.api_path, config.http_method),
                _json_dict_dump(config.data_scope_rules),
                _json_dict_dump(config.target_scope_rules),
                _json_dict_dump(config.operation_scope_rules),
                config.description,
            )
        )

        config_id = db.lastrowid()

        log_operation(
            db, user.username, user.role, 'INSERT', 'api_permission_config', config_id,
            new_data=config.dict()
        )

        return {"success": True, "message": "创建成功", "data": {"id": config_id}}


@router.put("/{config_id}", summary="更新API权限配置")
async def update_api_permission(
    config_id: int,
    config: ApiPermissionUpdate,
    request: Request,
    user: User = Depends(require_admin)
):
    """更新API权限配置（仅admin）"""
    with get_moral_db() as db:
        ensure_api_permission_schema(db)
        existing = db.query_one(
            "SELECT * FROM api_permission_config WHERE id = ?",
            (config_id,)
        )
        if not existing:
            raise HTTPException(404, "配置不存在")

        updates = []
        params = []

        if config.api_name is not None:
            updates.append("api_name = ?")
            params.append(config.api_name)

        if config.api_group is not None:
            updates.append("api_group = ?")
            params.append(config.api_group)

        if config.module_id is not None:
            updates.append("module_id = ?")
            params.append(config.module_id)

        if config.allowed_roles is not None:
            updates.append("allowed_roles = ?")
            params.append(_json_dump(config.allowed_roles))

        if config.min_level is not None:
            updates.append("min_level = ?")
            params.append(config.min_level)

        if config.http_method is not None:
            updates.append("http_method = ?")
            params.append((config.http_method or "*").upper())

        if config.match_type is not None:
            updates.append("match_type = ?")
            params.append(_normalize_match_type(config.match_type))

        if config.policy_mode is not None:
            updates.append("policy_mode = ?")
            params.append(_normalize_policy_mode(config.policy_mode))

        if config.inherit_from_module is not None:
            updates.append("inherit_from_module = ?")
            params.append(config.inherit_from_module)

        if config.is_public is not None:
            updates.append("is_public = ?")
            params.append(config.is_public)

        if config.enforce_backend is not None:
            updates.append("enforce_backend = ?")
            params.append(config.enforce_backend)

        if config.resource_type is not None:
            updates.append("resource_type = ?")
            params.append(config.resource_type)

        if config.action_type is not None:
            updates.append("action_type = ?")
            params.append(config.action_type)

        if config.data_scope_rules is not None:
            updates.append("data_scope_rules = ?")
            params.append(_json_dict_dump(config.data_scope_rules))

        if config.target_scope_rules is not None:
            updates.append("target_scope_rules = ?")
            params.append(_json_dict_dump(config.target_scope_rules))

        if config.operation_scope_rules is not None:
            updates.append("operation_scope_rules = ?")
            params.append(_json_dict_dump(config.operation_scope_rules))

        if config.description is not None:
            updates.append("description = ?")
            params.append(config.description)

        if config.is_active is not None:
            updates.append("is_active = ?")
            params.append(config.is_active)

        updates.append("updated_at = datetime('now', 'localtime')")

        if not updates:
            return {"success": True, "message": "无变更"}

        params.append(config_id)

        db.execute(
            f"UPDATE api_permission_config SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'api_permission_config', config_id,
            new_data=config.dict(exclude_unset=True)
        )

        return {"success": True, "message": "更新成功"}


@router.delete("/{config_id}", summary="删除API权限配置")
async def delete_api_permission(
    config_id: int,
    request: Request,
    user: User = Depends(require_admin)
):
    """删除API权限配置（仅admin）"""
    with get_moral_db() as db:
        ensure_api_permission_schema(db)
        existing = db.query_one(
            "SELECT * FROM api_permission_config WHERE id = ?",
            (config_id,)
        )
        if not existing:
            raise HTTPException(404, "配置不存在")

        db.execute(
            "DELETE FROM api_permission_config WHERE id = ?",
            (config_id,)
        )

        log_operation(
            db, user.username, user.role, 'DELETE', 'api_permission_config', config_id
        )

        return {"success": True, "message": "删除成功"}


@router.get("/my-permissions", summary="获取当前用户可访问的API列表")
async def get_my_api_permissions(user: User = Depends(get_current_user)):
    """获取当前用户可访问的API列表"""
    with get_moral_db() as db:
        ensure_api_permission_schema(db)
        # 获取所有启用的API配置
        configs = db.query_all(
            """SELECT c.*, m.module_name, m.allowed_roles AS module_allowed_roles,
                      m.min_level AS module_min_level, m.policy_mode AS module_policy_mode,
                      m.is_active AS module_is_active
               FROM api_permission_config c
               LEFT JOIN api_permission_module m ON c.module_id = m.id
               WHERE c.is_active = 1 AND COALESCE(c.enforce_backend, 1) = 1"""
        )

        # 过滤用户有权限的API
        allowed_apis = []
        for config in configs:
            if config.get("module_is_active") == 0:
                continue
            decision = is_api_allowed(user, config)
            if decision["allowed"]:
                allowed_apis.append({
                    "api_path": config['api_path'],
                    "api_name": config['api_name'],
                    "api_group": config['api_group'],
                    "module_id": config.get("module_id"),
                    "module_name": config.get("module_name"),
                    "effective_policy": decision["policy"],
                })

        return {"success": True, "data": allowed_apis}


@router.get("/check", summary="检查用户对特定API的权限")
async def check_api_permission_endpoint(
    api_path: str = Query(..., description="API路径"),
    http_method: str = Query("*", description="HTTP方法"),
    user: User = Depends(get_current_user)
):
    """检查用户对特定API的权限"""
    with get_moral_db() as db:
        ensure_api_permission_schema(db)
        config = _get_matching_config(db, api_path, http_method)

        # 无配置则默认允许（依赖原有装饰器）
        if not config:
            return {"success": True, "data": {"has_permission": True, "reason": "无权限配置，默认允许"}}

        decision = is_api_allowed(user, config)
        return {
            "success": True,
            "data": {
                "has_permission": decision["allowed"],
                "reason": decision["reason"],
                "effective_policy": decision["policy"],
            },
        }


@router.post("/init", summary="初始化默认API权限配置")
async def init_api_permissions(
    request: Request,
    user: User = Depends(require_admin)
):
    """初始化默认API权限配置（仅admin）"""
    with get_moral_db() as db:
        ensure_api_permission_schema(db)
        created_count = 0
        skipped_count = 0

        for default_config in DEFAULT_API_PERMISSIONS:
            existing = db.query_one(
                "SELECT id FROM api_permission_config WHERE api_path = ?",
                (default_config['api_path'],)
            )

            if existing:
                skipped_count += 1
                continue

            module_key = _module_key_from_group(default_config["api_group"])
            module = db.query_one(
                "SELECT id FROM api_permission_module WHERE module_key = ? OR module_name = ? ORDER BY id LIMIT 1",
                (module_key, default_config["api_group"]),
            )
            if not module:
                db.execute(
                    """INSERT INTO api_permission_module
                    (module_key, module_name, allowed_roles, min_level, policy_mode, description)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        module_key,
                        default_config["api_group"],
                        _json_dump(default_config["allowed_roles"]),
                        default_config["min_level"],
                        "role_and_level",
                        "默认API权限模块",
                    ),
                )
                module_id = db.lastrowid()
            else:
                module_id = module["id"]

            allowed_roles_json = _json_dump(default_config['allowed_roles'])

            db.execute(
                """INSERT INTO api_permission_config
                (api_path, api_name, api_group, allowed_roles, min_level, module_id, http_method,
                 match_type, policy_mode, resource_type, action_type,
                 data_scope_rules, target_scope_rules, operation_scope_rules, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    default_config['api_path'],
                    default_config['api_name'],
                    default_config['api_group'],
                    allowed_roles_json,
                    default_config['min_level'],
                    module_id,
                    default_config.get('http_method', '*'),
                    default_config.get('match_type', 'exact'),
                    "role_and_level",
                    default_config.get("resource_type") or _infer_resource_type(default_config['api_path']),
                    default_config.get("action_type") or _infer_action_type(default_config['api_path'], default_config.get('http_method', '*')),
                    _json_dict_dump(default_config.get('data_scope_rules')),
                    _json_dict_dump(default_config.get('target_scope_rules')),
                    _json_dict_dump(DEFAULT_OPERATION_SCOPE_RULES.get(default_config['api_path'], {})),
                    default_config.get('description', '')
                )
            )
            created_count += 1

        log_operation(
            db, user.username, user.role, 'INIT', 'api_permission_config', None,
            new_data={"created": created_count, "skipped": skipped_count}
        )

        legacy_result = _sync_legacy_api_level_yaml(db)

        return {
            "success": True,
            "message": (
                f"初始化完成：创建 {created_count} 条，跳过 {skipped_count} 条已存在配置；"
                f"同步旧版接口新增 {legacy_result['created']} 条，更新 {legacy_result['updated']} 条"
            )
        }


@router.get("/groups", summary="获取API分组列表")
async def get_api_groups(user: User = Depends(get_current_user)):
    """获取API分组列表"""
    with get_moral_db() as db:
        ensure_api_permission_schema(db)
        groups = db.query_all(
            "SELECT DISTINCT api_group FROM api_permission_config ORDER BY api_group"
        )
        return {"success": True, "data": [g['api_group'] for g in groups]}
