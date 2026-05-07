"""
医疗分诊核心逻辑
"""

from medical.knowledge_base import get_department, get_department_detail
from medical.safety import MedicalSafetyFilter

def triage(symptoms: str) -> dict:
    """
    执行分诊逻辑
    返回: {
        "department": str,
        "reason": str,
        "tips": str,
        "confidence": str
    }
    """
    # 1. 安全检查
    safety_check = MedicalSafetyFilter.check_input(symptoms)
    
    if safety_check.get("need_emergency"):
        return {
            "department": "急诊科",
            "reason": safety_check["message"],
            "tips": "请立即就医！",
            "confidence": "紧急"
        }
    
    if not safety_check.get("is_safe"):
        return {
            "department": "无法提供",
            "reason": safety_check["message"],
            "tips": "建议咨询正规医院医生",
            "confidence": "无"
        }
    
    # 2. 科室匹配
    department, match_count, matched_keywords = get_department(symptoms)
    
    # 3. 获取科室详情
    dept_detail = get_department_detail(department)
    
    # 4. 构建回复
    if match_count == 0:
        reason = f"根据您描述的症状「{symptoms}」，未匹配到明确的专科。建议先挂【全科/普通内科】进行初步诊断。"
        confidence = "低"
    else:
        keywords_str = "、".join(matched_keywords[:3])
        reason = f"根据您描述的症状「{symptoms}」，检测到【{keywords_str}】等关键词。\n\n建议优先到【{department}】就诊。\n\n{dept_detail.get('description', '')}"
        confidence = "中" if match_count >= 2 else "低"
    
    return {
        "department": department,
        "reason": reason,
        "tips": dept_detail.get("tips", "就诊前请携带身份证、医保卡，必要时空腹前往"),
        "confidence": confidence
    }
