"""
医疗AI安全过滤器
负责输入检测、输出加固、合规控制
"""

import re
from typing import Dict, Tuple

class MedicalSafetyFilter:
    """医疗AI安全过滤器"""
    
    # 紧急情况关键词（优先处理）
    URGENT_KEYWORDS = [
        "胸痛", "呼吸困难", "昏迷", "大出血", "剧烈头痛",
        "无法说话", "半身不遂", "剧烈腹痛", "吐血", "便血",
        "心脏骤停", "窒息", "抽搐", "意识模糊", "胸口疼"
    ]
    
    # 禁止回答的问题类型
    FORBIDDEN_PATTERNS = {
        "diagnosis": ["确诊", "确定是", "肯定是", "就是", "诊断结果是", "得了什么病"],
        "prescription": [r"吃\s*\d+", r"用\s*\d+", r"服用\s*\d+", r"剂量", "mg", "毫升"],
        "treatment": ["治疗方法", "手术方案", "化疗方案", "治疗方案"],
        "promise": ["保证治愈", "100%", "一定治好", "绝对有效"],
    }
    
    @classmethod
    def check_input(cls, user_input: str) -> Dict:
        """检查用户输入，返回检测结果"""
        user_input_lower = user_input.lower()
        
        # 1. 检查紧急情况
        for keyword in cls.URGENT_KEYWORDS:
            if keyword in user_input_lower:
                return {
                    "is_safe": True,
                    "need_emergency": True,
                    "emergency_keyword": keyword,
                    "message": cls._get_emergency_message(keyword)
                }
        
        # 2. 检查禁止内容
        for category, patterns in cls.FORBIDDEN_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, user_input_lower):
                    return {
                        "is_safe": False,
                        "need_emergency": False,
                        "blocked_reason": category,
                        "message": cls._get_blocked_message(category)
                    }
        
        return {"is_safe": True, "need_emergency": False}
    
    @classmethod
    def _get_emergency_message(cls, keyword: str) -> str:
        """获取紧急情况提示"""
        return f"""🚨【紧急提醒】🚨

您描述的「{keyword}」属于紧急症状！

请立即：
1. 前往最近医院的【急诊科】
2. 或拨打120急救电话
3. 如有人陪护，请尽快行动

⚠️ 这不是AI诊断，是紧急情况提醒。"""
    
    @classmethod
    def _get_blocked_message(cls, category: str) -> str:
        """获取禁止内容提示"""
        messages = {
            "diagnosis": "抱歉，我无法进行疾病诊断。请前往正规医院进行检查，由医生出具诊断。",
            "prescription": "抱歉，我无法提供具体的用药建议。请遵医嘱使用药物。",
            "treatment": "抱歉，治疗方案需要由医生根据具体情况制定。建议咨询专业医生。",
            "promise": "抱歉，医疗问题不存在保证治愈的说法。请相信专业医生的判断。"
        }
        return messages.get(category, "抱歉，这个问题超出了我的能力范围，建议咨询专业医生。")
    
    @classmethod
    def safe_response(cls, ai_response: str, user_input: str = "") -> str:
        """对AI回复进行安全加固"""
        result = ai_response
        
        # 移除绝对性词汇
        result = cls._remove_absolute_words(result)
        
        # 添加免责声明
        disclaimer = "\n\n---\n⚠️ 本信息仅供参考，不能替代医生诊断。如有不适，请及时就医。"
        
        return result + disclaimer
    
    @classmethod
    def _remove_absolute_words(cls, text: str) -> str:
        """移除绝对性词汇"""
        replacements = {
            "确诊": "建议进一步检查",
            "一定是": "可能是",
            "肯定是": "倾向于",
            "绝对是": "可能是",
            "100%": "",
            "保证治愈": "建议积极治疗",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
