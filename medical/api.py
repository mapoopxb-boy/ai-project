"""
医疗模块 API 入口
独立运行的 FastAPI 服务
使用 DeepSeek API 进行智能分诊，降级规则引擎
"""

import os
import json
import httpx
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from pydantic import BaseModel
from typing import Optional

# 导入内部模块（规则引擎、安全过滤器）
from medical.triage import triage as rule_based_triage
from medical.safety import MedicalSafetyFilter

# ---------- DeepSeek 配置 ----------
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

if not DEEPSEEK_API_KEY:
    print("⚠️ 警告: DEEPSEEK_API_KEY 未设置，将仅使用规则引擎。")

# ---------- OpenAI 客户端（兼容 DeepSeek）----------
from openai import OpenAI
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    timeout=httpx.Timeout(60.0)
) if DEEPSEEK_API_KEY else None

# ---------- FastAPI 应用 ----------
app = FastAPI(title="医疗AI助手", version="2.0")

# ---------- 请求/响应模型 ----------
class TriageRequest(BaseModel):
    symptoms: str
    user_id: Optional[str] = "test_user"

class TriageResponse(BaseModel):
    code: int
    department: str
    reason: str
    tips: str
    confidence: str

# ---------- 健康检查 ----------
@app.get("/health")
async def health():
    return {"status": "ok", "service": "医疗AI助手", "version": "2.0"}

# ---------- 分诊接口（智能 + 规则降级）----------
@app.post("/triage", response_model=TriageResponse)
async def handle_triage(req: TriageRequest):
    symptoms = req.symptoms.strip()
    if len(symptoms) < 2:
        return TriageResponse(
            code=400,
            department="",
            reason="请描述您的症状，我会帮您分析。例如：头痛、发烧两天了",
            tips="描述越详细，分析越准确",
            confidence=""
        )

    # 1. 紧急情况快速处理（关键词检测）
    emergency_result = MedicalSafetyFilter.check_input(symptoms)
    if emergency_result.get("need_emergency"):
        return TriageResponse(
            code=200,
            department="急诊科",
            reason=emergency_result["message"],
            tips="请立即就医！",
            confidence="紧急"
        )

    # 2. 尝试调用 DeepSeek API
    if client is not None:
        try:
            prompt = f"""你是一位专业的医疗分诊助手。用户描述了以下症状："{symptoms}"。

请根据症状分析可能涉及的科室，并给出就诊建议。请严格按照以下 JSON 格式返回（只输出 JSON，不要有其他文字）：
{{
    "department": "科室名称（例如：呼吸内科）",
    "reason": "分析理由（一句话说明为什么推荐此科室）",
    "tips": "就诊建议（例如：建议空腹前往，携带身份证医保卡）",
    "confidence": "高/中/低"
}}
如果症状不足或无法判断，department 填"全科/普通内科"，confidence 填"低"。
注意：不能给出任何诊断结论，仅提供参考建议。"""

            response = client.chat.completions.create(
                model="deepseek-v4-flash",  # 或 "deepseek-chat" / "deepseek-v4-pro"
                messages=[
                    {"role": "system", "content": "你是医疗分诊助手，输出必须为合法 JSON。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            reason = MedicalSafetyFilter.safe_response(result.get("reason", ""), symptoms)
            return TriageResponse(
                code=200,
                department=result.get("department", "全科/普通内科"),
                reason=reason,
                tips=result.get("tips", "就诊时请携带身份证、医保卡"),
                confidence=result.get("confidence", "中")
            )
        except Exception as e:
            print(f"DeepSeek API 调用失败，降级使用规则引擎: {e}")
            # 继续执行降级逻辑

    # 3. 降级：使用关键词规则引擎
    result = rule_based_triage(symptoms)
    result["reason"] = MedicalSafetyFilter.safe_response(result["reason"], symptoms)
    return TriageResponse(
        code=200,
        department=result["department"],
        reason=result["reason"],
        tips=result["tips"],
        confidence=result["confidence"]
    )

# ---------- 报告解读接口（占位）----------
@app.post("/analyze_report")
async def analyze_report(
    file: UploadFile = File(...),
    user_id: str = Form("test_user")
):
    """解读上传的检查报告（图片）—— 演示版本"""
    file_type = file.content_type
    if not file_type.startswith('image/'):
        return {"code": 400, "answer": "请上传图片格式的报告（如化验单、检查单）"}
    # 模拟解读（可后续接入真实 OCR + 大模型）
    answer = (
        "📄 报告已收到。\n\n"
        "根据公开医学知识，常见的检查报告指标解读建议如下：\n"
        "• 请关注报告中标注「↑」或「↓」的异常指标\n"
        "• 异常结果需结合临床症状由医生综合判断\n"
        "• 建议携带报告前往相应科室咨询医生\n\n"
        "---\n⚠️ 本解读仅供参考，不能替代医生诊断。"
    )
    return {"code": 200, "answer": answer}

# ---------- 启动入口 ----------
if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("🏥 医疗AI助手服务启动中...")
    print("=" * 50)
    print("📋 功能: 智能分诊 | 报告解读 | 症状分析 | 科室推荐")
    print("🚀 服务地址: http://127.0.0.1:8001")
    print("📡 分诊接口: http://127.0.0.1:8001/triage")
    print("📡 报告解读: http://127.0.0.1:8001/analyze_report")
    print("🏥 健康检查: http://127.0.0.1:8001/health")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8001)