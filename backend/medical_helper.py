# medical_helper.py
import re
import json
import httpx
from openai import OpenAI
import os

# 安全过滤器
class MedicalSafetyFilter:
    URGENT_KEYWORDS = ["胸痛", "呼吸困难", "昏迷", "大出血", "剧烈头痛", "无法说话", "半身不遂", "剧烈腹痛", "吐血", "便血"]
    FORBIDDEN_PATTERNS = {
        "diagnosis": ["确诊", "确定是", "肯定是", "就是", "诊断结果是", "得了什么病"],
        "prescription": [r"吃\s*\d+", r"用\s*\d+", r"服用\s*\d+", r"剂量", "mg", "毫升"],
        "treatment": ["治疗方法", "手术方案", "化疗方案", "治疗方案"],
        "promise": ["保证治愈", "100%", "一定治好", "绝对有效"],
    }
    @classmethod
    def check_input(cls, user_input: str):
        user_input_lower = user_input.lower()
        for keyword in cls.URGENT_KEYWORDS:
            if keyword in user_input_lower:
                return {"need_emergency": True, "message": f"🚨【紧急提醒】🚨\n\n您描述的「{keyword}」属于紧急症状！\n\n请立即：\n1. 前往最近医院的【急诊科】\n2. 或拨打120急救电话\n3. 如有人陪护，请尽快行动\n\n⚠️ 这不是AI诊断，是紧急情况提醒。"}
        for category, patterns in cls.FORBIDDEN_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, user_input_lower):
                    return {"need_emergency": False, "blocked": True, "message": "抱歉，这个问题超出了我的能力范围，建议咨询专业医生。"}
        return {"need_emergency": False, "blocked": False}
    @classmethod
    def safe_response(cls, ai_response: str, user_input: str = ""):
        result = ai_response
        replacements = {"确诊": "建议进一步检查", "一定是": "可能是", "肯定是": "倾向于", "绝对是": "可能是", "100%": "", "保证治愈": "建议积极治疗"}
        for old, new in replacements.items():
            result = result.replace(old, new)
        disclaimer = "\n\n---\n⚠️ 本信息仅供参考，不能替代医生诊断。如有不适，请及时就医。"
        return result + disclaimer

# 规则引擎备用
SYMPTOM_DEPARTMENT_MAP = {
    "呼吸内科": ["咳嗽", "咳痰", "发烧", "发热", "呼吸困难", "胸痛", "气喘", "肺炎", "感冒", "流感", "喉咙痛", "咽痛"],
    "消化内科": ["胃痛", "腹痛", "腹泻", "恶心", "呕吐", "便秘", "胃胀", "消化不良", "便血", "胃酸", "反酸"],
    "心内科": ["胸痛", "心悸", "心慌", "高血压", "冠心病", "心脏病", "胸闷", "气短", "心律不齐"],
    "神经内科": ["头痛", "头晕", "眩晕", "失眠", "记忆力下降", "手脚麻木", "癫痫", "中风", "脑梗", "偏头痛"],
    "骨科": ["腰痛", "腿痛", "关节痛", "骨折", "颈椎病", "腰椎间盘突出", "关节炎", "肩周炎"],
    "皮肤科": ["皮疹", "瘙痒", "湿疹", "痘痘", "荨麻疹", "皮肤过敏", "脱发", "癣"],
    "眼科": ["视力模糊", "眼痛", "眼红", "眼干", "近视", "白内障", "青光眼", "麦粒肿"],
    "耳鼻喉科": ["耳鸣", "听力下降", "鼻塞", "流鼻涕", "喉咙痛", "扁桃体炎", "中耳炎", "鼻炎"],
    "儿科": ["儿童", "幼儿", "宝宝", "小儿", "孩子发烧", "小孩咳嗽", "婴儿"],
    "妇科": ["月经不调", "痛经", "白带异常", "妇科炎症", "不孕", "更年期", "盆腔炎"],
    "泌尿外科": ["尿频", "尿急", "尿痛", "血尿", "肾结石", "前列腺", "泌尿"],
    "普通外科": ["肿块", "囊肿", "阑尾炎", "疝气", "胆囊炎", "痔疮"],
    "口腔科": ["牙痛", "牙龈出血", "口腔溃疡", "智齿", "牙齿矫正", "蛀牙"],
    "精神心理科": ["焦虑", "抑郁", "失眠", "情绪低落", "心理", "精神", "压力大"],
    "内分泌科": ["糖尿病", "甲亢", "甲减", "内分泌", "血糖", "甲状腺"],
    "肾内科": ["肾炎", "肾衰竭", "尿蛋白", "水肿", "肾"],
}

def rule_based_triage(symptoms: str) -> dict:
    symptoms_lower = symptoms.lower()
    matches = []
    for dept, keywords in SYMPTOM_DEPARTMENT_MAP.items():
        matched = [kw for kw in keywords if kw in symptoms_lower]
        if matched:
            matches.append((dept, len(matched), matched))
    if not matches:
        return {"department": "全科/普通内科", "reason": "未匹配到明确专科，建议先挂普通内科或全科进行初步诊断", "tips": "建议：如果症状持续或加重，请及时就医。", "confidence": "低"}
    matches.sort(key=lambda x: x[1], reverse=True)
    dept = matches[0][0]
    return {"department": dept, "reason": f"根据症状「{symptoms}」，建议优先到【{dept}】就诊", "tips": "就诊前请携带身份证、医保卡，必要时空腹前往", "confidence": "中"}

# 智能分诊（调用 DeepSeek API）
async def ai_triage(symptoms: str, client) -> dict:
    prompt = f"""你是一位专业的医疗分诊助手。用户描述了以下症状："{symptoms}"。
请根据症状分析可能涉及的科室，并给出就诊建议。请严格按照以下 JSON 格式返回（只输出 JSON）：
{{"department": "科室名称", "reason": "分析理由", "tips": "就诊建议", "confidence": "高/中/低"}}
如果症状不足或无法判断，department 填"全科/普通内科"，confidence 填"低"。
不能给出诊断结论，仅提供参考。"""
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {"role": "system", "content": "你是医疗分诊助手，输出必须为合法 JSON。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    result = json.loads(response.choices[0].message.content)
    return result