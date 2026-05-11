# -*- coding: utf-8 -*-
"""
AI诊疗核心 AI 调用模块

实现 AI 模型调用、变量填充、追问调度等核心功能
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List
from openai import OpenAI

from config.config import Config
from .ai_model_config import get_current_model
from .consultation_prompts import (
    SYSTEM_PROMPTS,
    FIRST_ANALYSIS_PROMPTS,
    FOLLOWUP_PROMPTS,
    TRIGGER_KEYWORDS,
    API_CONFIG,
    DISCLAIMER
)

logger = logging.getLogger(__name__)


# =============================================================================
# 核心调用函数
# =============================================================================

def call_ai_model(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 2000
) -> str:
    """
    调用阿里百炼 Kimi K2.5 模型

    Args:
        system_prompt: 系统提示词（角色定义）
        user_prompt: 用户提示词（具体问题）
        temperature: 温度参数，越低越稳定
        max_tokens: 最大输出长度

    Returns:
        AI 生成的回复内容
    """
    try:
        client = OpenAI(
            api_key=Config().get_config("bailian_token", "token.yaml"),
            base_url="https://coding.dashscope.aliyuncs.com/v1",
            timeout=90,  # 增加超时时间
        )
        completion = client.chat.completions.create(
            model=get_current_model('ai_diagnosis'),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        result = completion.choices[0].message.content.strip()
        # 添加免责声明（缩短版）
        return result + "\n\n---\n*AI分析仅供参考，最终判断由专业人员负责*"
    except Exception as e:
        logger.error(f"AI 调用失败: {e}")
        return f"AI 分析暂时不可用，请稍后重试。\n\n错误详情：{str(e)}"


def fill_prompt_template(template: str, variables: Dict) -> str:
    """
    填充 Prompt 模板变量

    Args:
        template: 包含 {{变量名}} 的模板字符串
        variables: 变量字典

    Returns:
        填充后的 Prompt
    """
    result = template
    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        # 处理空值
        display_value = str(value) if value else "暂无"
        result = result.replace(placeholder, display_value)
    return result


# =============================================================================
# 首次分析生成
# =============================================================================

def generate_initial_analysis(
    consultation_type: str,
    student: Dict,
    description: str,
    priority: str = "normal"
) -> Dict:
    """
    生成首次 AI 分析

    Args:
        consultation_type: 诊疗类型（psychological/behavior/academic/comprehensive）
        student: 学生信息字典（包含 name, class_name, gender 等）
        description: 问题描述
        priority: 优先级

    Returns:
        包含 analysis, suggestions, risk_assessment 的字典
    """
    # 获取 System Prompt
    system_prompt = SYSTEM_PROMPTS.get(consultation_type, SYSTEM_PROMPTS["comprehensive"])

    # 构建变量
    variables = {
        "student_name": student.get("name", student.get("student_name", "")),
        "grade_class": student.get("class_name", student.get("grade_class", "")),
        "gender": student.get("gender", "未知"),
        "description": description or "暂无详细描述",
        "priority": _get_priority_display(priority),
    }

    # 获取并填充首次分析 Prompt
    first_prompt_template = FIRST_ANALYSIS_PROMPTS.get(
        consultation_type,
        FIRST_ANALYSIS_PROMPTS["comprehensive"]
    )
    user_prompt = fill_prompt_template(first_prompt_template, variables)

    # 根据类型获取参数配置
    config = API_CONFIG.get(consultation_type, API_CONFIG["comprehensive"])

    # 调用 AI
    analysis_content = call_ai_model(
        system_prompt,
        user_prompt,
        temperature=config["temperature"],
        max_tokens=config["max_tokens"]
    )

    # 提取风险等级
    risk_assessment = "low"
    if "🔴 高风险" in analysis_content or "高风险预警" in analysis_content or "极高危" in analysis_content:
        risk_assessment = "high"
    elif "🟡 中风险" in analysis_content or "需关注" in analysis_content:
        risk_assessment = "medium"

    # 提取建议（简单解析，提取编号条目）
    suggestions = []
    lines = analysis_content.split("\n")
    for line in lines:
        stripped = line.strip()
        # 匹配以数字编号开头的建议
        if stripped and stripped[0].isdigit() and "." in stripped[:3]:
            suggestions.append(stripped)

    return {
        "analysis": analysis_content,
        "suggestions": suggestions[:6] if suggestions else ["请查看完整分析报告"],
        "risk_assessment": risk_assessment,
    }


def _get_priority_display(priority: str) -> str:
    """获取优先级显示文本"""
    priority_map = {
        "urgent": "非常紧急",
        "high": "紧急",
        "normal": "普通",
        "low": "低优先级"
    }
    return priority_map.get(priority, "普通")


# =============================================================================
# 追问调度与分析
# =============================================================================

def detect_followup_type(
    consultation_type: str,
    teacher_message: str,
    days_elapsed: int = 0
) -> str:
    """
    根据教师消息内容检测追问类型

    Args:
        consultation_type: 诊疗类型
        teacher_message: 教师发送的消息内容
        days_elapsed: 诊疗已持续天数

    Returns:
        追问类型（risk_exploration/information_supplement/intervention_deepen 等）
    """
    triggers = TRIGGER_KEYWORDS.get(consultation_type, {})

    # 优先级1：风险信号 → 立即触发风险深探（最高优先）
    risk_keywords = triggers.get("risk_exploration", [])
    for keyword in risk_keywords:
        if keyword in teacher_message:
            return "risk_exploration"

    # 优先级2：升级信号（行为问题特有）
    escalation_keywords = triggers.get("escalation", [])
    for keyword in escalation_keywords:
        if keyword in teacher_message:
            return "escalation"

    # 优先级3：结案请求
    closure_keywords = triggers.get("closure_summary", [])
    for keyword in closure_keywords:
        if keyword in teacher_message:
            return "closure_summary"

    # 优先级4：进展反馈（至少有一定时间才评估）
    progress_keywords = triggers.get("progress_evaluation", [])
    for keyword in progress_keywords:
        if keyword in teacher_message:
            return "progress_evaluation"

    # 优先级5：干预请求
    intervention_keywords = triggers.get("intervention_deepen", [])
    for keyword in intervention_keywords:
        if keyword in teacher_message:
            return "intervention_deepen"

    # 优先级6：动力重建（学业问题特有）
    motivation_keywords = triggers.get("motivation_rebuild", [])
    for keyword in motivation_keywords:
        if keyword in teacher_message:
            return "motivation_rebuild"

    # 优先级7：家校协同（行为问题）
    family_keywords = triggers.get("family_cooperation", [])
    for keyword in family_keywords:
        if keyword in teacher_message:
            return "family_cooperation"

    # 优先级8：诊断深化（学业问题）
    diagnosis_keywords = triggers.get("diagnosis_deepen", [])
    for keyword in diagnosis_keywords:
        if keyword in teacher_message:
            return "diagnosis_deepen"

    # 优先级9：数据补充（行为问题）
    data_keywords = triggers.get("data_supplement", [])
    for keyword in data_keywords:
        if keyword in teacher_message:
            return "data_supplement"

    # 优先级10：信息补充
    info_keywords = triggers.get("information_supplement", [])
    for keyword in info_keywords:
        if keyword in teacher_message:
            return "information_supplement"

    # 默认：信息补充追问
    return "information_supplement"


def generate_followup_analysis(
    consultation_type: str,
    followup_type: str,
    student: Dict,
    teacher_message: str,
    last_analysis: str = "",
    days_elapsed: int = 0,
    current_risk_level: str = "low"
) -> str:
    """
    生成追问分析

    Args:
        consultation_type: 诊疗类型
        followup_type: 追问类型
        student: 学生信息
        teacher_message: 教师新消息
        last_analysis: 上次 AI 分析摘要
        days_elapsed: 诊疗已持续天数
        current_risk_level: 当前风险等级

    Returns:
        AI 回复内容
    """
    # 获取 System Prompt
    system_prompt = SYSTEM_PROMPTS.get(consultation_type, SYSTEM_PROMPTS["comprehensive"])

    # 获取追问 Prompt 模板
    followup_templates = FOLLOWUP_PROMPTS.get(consultation_type, {})
    # 如果找不到指定类型，回退到 information_supplement 或通用模板
    prompt_template = followup_templates.get(followup_type)
    if not prompt_template:
        prompt_template = followup_templates.get("information_supplement", "")
    if not prompt_template:
        # 如果还是没有，使用综合类型的 information_supplement
        prompt_template = FOLLOWUP_PROMPTS.get("comprehensive", {}).get("information_supplement", "")

    # 检测风险关键词
    risk_keywords = []
    triggers = TRIGGER_KEYWORDS.get(consultation_type, {})
    for keyword in triggers.get("risk_exploration", []):
        if keyword in teacher_message:
            risk_keywords.append(keyword)

    # 构建变量
    variables = {
        "student_name": student.get("name", student.get("student_name", "")),
        "grade_class": student.get("class_name", student.get("grade_class", "")),
        "gender": student.get("gender", "未知"),
        "teacher_new_input": teacher_message,
        "last_analysis": last_analysis[:600] if last_analysis else "暂无",
        "days_elapsed": days_elapsed,
        "current_risk_level": current_risk_level,
        "initial_risk_level": current_risk_level,  # 简化处理
        "risk_keywords": ", ".join(risk_keywords) if risk_keywords else "无",
    }

    # 填充 Prompt
    user_prompt = fill_prompt_template(prompt_template, variables)

    # 根据追问类型调整温度
    if followup_type == "risk_exploration":
        temperature = 0.25  # 风险评估最保守
    else:
        config = API_CONFIG.get(consultation_type, API_CONFIG["comprehensive"])
        temperature = config["temperature"]

    # 调用 AI
    return call_ai_model(system_prompt, user_prompt, temperature=temperature)


# =============================================================================
# 结案报告生成
# =============================================================================

def generate_closure_report(
    consultation_type: str,
    student: Dict,
    start_date: str,
    end_date: str,
    outcome_description: str,
    initial_risk_level: str = "low",
    final_risk_level: str = "low"
) -> str:
    """
    生成结案报告

    Args:
        consultation_type: 诊疗类型
        student: 学生信息
        start_date: 开始日期
        end_date: 结束日期
        outcome_description: 教师填写的处理结果
        initial_risk_level: 初始风险等级
        final_risk_level: 最终风险等级

    Returns:
        结案报告内容
    """
    # 计算持续天数
    days_elapsed = calculate_days_elapsed(start_date)

    # 获取 System Prompt 和结案模板
    system_prompt = SYSTEM_PROMPTS.get(consultation_type, SYSTEM_PROMPTS["comprehensive"])
    followup_templates = FOLLOWUP_PROMPTS.get(consultation_type, {})
    prompt_template = followup_templates.get("closure_summary", "")
    if not prompt_template:
        prompt_template = FOLLOWUP_PROMPTS.get("comprehensive", {}).get("closure_summary", "")

    # 构建变量
    variables = {
        "student_name": student.get("name", student.get("student_name", "")),
        "grade_class": student.get("class_name", student.get("grade_class", "")),
        "gender": student.get("gender", "未知"),
        "start_date": start_date[:10] if start_date else "未知",
        "end_date": end_date[:10] if end_date else datetime.now().strftime("%Y-%m-%d"),
        "days_elapsed": days_elapsed,
        "outcome_description": outcome_description or "暂无处理结果描述",
        "initial_risk_level": initial_risk_level,
        "current_risk_level": final_risk_level,
    }

    # 填充 Prompt
    user_prompt = fill_prompt_template(prompt_template, variables)

    # 调用 AI
    return call_ai_model(system_prompt, user_prompt, temperature=0.3, max_tokens=1500)


def calculate_days_elapsed(start_date: str) -> int:
    """
    计算诊疗持续天数

    Args:
        start_date: 开始日期字符串

    Returns:
        持续天数
    """
    if not start_date:
        return 0
    try:
        # 处理不同格式
        date_str = start_date[:10]  # 只取前10位 YYYY-MM-DD
        start = datetime.strptime(date_str, "%Y-%m-%d")
        now = datetime.now()
        return max(0, (now - start).days)
    except Exception as e:
        logger.warning(f"日期解析失败: {start_date}, {e}")
        return 0


# =============================================================================
# 辅助函数
# =============================================================================

def get_risk_level_display(level: str) -> str:
    """获取风险等级显示文本"""
    level_map = {
        "high": "🔴 高风险",
        "medium": "🟡 中风险",
        "low": "🟢 低风险"
    }
    return level_map.get(level, "🟢 低风险")