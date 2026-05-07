from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import uvicorn

app = FastAPI(title="医疗分诊助手", version="1.0")

# 症状关键词 → 科室映射库
SYMPTOM_MAP = {
    "呼吸内科": ["咳嗽", "咳痰", "发烧", "发热", "呼吸困难", "胸痛", "气喘", "肺炎", "感冒", "流感"],
    "消化内科": ["胃痛", "腹痛", "腹泻", "恶心", "呕吐", "便秘", "胃胀", "消化不良", "肝炎", "胃炎"],
    "心内科": ["胸痛", "心悸", "心慌", "高血压", "冠心病", "心脏病", "胸闷", "气短"],
    "神经内科": ["头痛", "头晕", "眩晕", "失眠", "记忆力下降", "手脚麻木", "癫痫", "中风"],
    "骨科": ["腰痛", "腿痛", "关节痛", "骨折", "颈椎病", "腰椎间盘突出", "关节炎"],
    "皮肤科": ["皮疹", "瘙痒", "湿疹", "痘痘", "荨麻疹", "皮肤过敏", "脱发"],
    "眼科": ["视力模糊", "眼痛", "眼红", "眼干", "近视", "白内障", "青光眼"],
    "耳鼻喉科": ["耳鸣", "听力下降", "鼻塞", "流鼻涕", "喉咙痛", "扁桃体炎", "中耳炎"],
    "儿科": ["儿童", "幼儿", "宝宝", "小儿", "孩子发烧", "小孩咳嗽"],
    "妇科": ["月经不调", "痛经", "白带异常", "妇科炎症", "不孕", "更年期"],
    "泌尿外科": ["尿频", "尿急", "尿痛", "血尿", "肾结石", "前列腺"],
    "普通外科": ["肿块", "囊肿", "阑尾炎", "疝气", "胆囊炎", "痔疮"],
    "口腔科": ["牙痛", "牙龈出血", "口腔溃疡", "智齿", "牙齿矫正", "蛀牙"],
    "精神心理科": ["焦虑", "抑郁", "失眠", "情绪低落", "心理", "精神"],
}

class TriageRequest(BaseModel):
    symptoms: str

class TriageResponse(BaseModel):
    code: int
    department: str
    reason: str
    tips: str
    confidence: str

@app.get("/health")
async def health():
    return {"status": "ok", "service": "医疗分诊助手"}

@app.post("/triage", response_model=TriageResponse)
async def triage(req: TriageRequest):
    symptoms = req.symptoms.lower()

    # 匹配科室
    matched_departments = []
    for dept, keywords in SYMPTOM_MAP.items():
        for keyword in keywords:
            if keyword in symptoms:
                matched_departments.append(dept)
                break

    # 去重
    matched_departments = list(set(matched_departments))

    if not matched_departments:
        return TriageResponse(
            code=200,
            department="全科/普通内科",
            reason="未匹配到明确专科，建议先挂普通内科或全科进行初步诊断",
            tips="建议：如果症状持续或加重，请及时就医。可以描述更详细的症状帮助进一步判断。",
            confidence="低"
        )

    # 返回第一个匹配的科室（按优先级）
    department = matched_departments[0]

    return TriageResponse(
        code=200,
        department=department,
        reason=f"根据您描述的症状「{req.symptoms}」，建议优先到【{department}】就诊",
        tips="就诊前可准备：身份证、医保卡、既往病历，必要时空腹前往",
        confidence="中" if len(matched_departments) == 1 else "中"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
