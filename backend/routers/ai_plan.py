from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from openai import OpenAI
from pydantic import BaseModel
from typing import Optional, Any
from datetime import date, datetime
import httpx
import json
import os
import logging

from database.db import get_db
from models import Doctor, Patient, PatientRehabPlan, RehabTemplate, DailyTask
from api.dependencies import get_current_doctor
from utils.rehab import generate_tasks_for_plan

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI康复计划"])

# ============== 配置 ==============
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# ============== 共享 OpenAI 客户端 ==============
_client: OpenAI | None = None


def get_ai_client() -> OpenAI:
    """获取或创建 OpenAI 客户端（与 main.py 使用相同的配置）。"""
    global _client
    if _client is not None:
        return _client

    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY 未设置，AI 功能不可用")

    _client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        timeout=httpx.Timeout(120.0, connect=10.0),
        max_retries=0,
    )
    logger.info("✅ AI 客户端已创建（ai_plan）")
    return _client


# ============== Pydantic 模型 ==============


class AutoGenPlanResponse(BaseModel):
    """自动生成康复计划响应"""
    id: int
    patient_id: int
    name: Optional[str] = None
    start_date: Optional[date] = None
    status: str = "active"
    source: str = "auto_generate"
    review_status: Optional[str] = "pending"
    phases: Optional[Any] = None

    model_config = {"from_attributes": True}


class PendingPlanItem(BaseModel):
    """待审核计划列表项"""
    id: int
    patient_id: int
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    plan_name: Optional[str] = None
    start_date: Optional[date] = None
    source: Optional[str] = None
    review_status: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReviewRequest(BaseModel):
    """审核请求"""
    action: str  # "approve" or "reject"
    reason: Optional[str] = None


class ReviewResponse(BaseModel):
    """审核响应"""
    id: int
    patient_id: int
    review_status: str
    review_comment: Optional[str] = None
    status: str
    message: str

    model_config = {"from_attributes": True}


# ============== 接口 ==============


@router.post(
    "/patients/{patient_id}/auto-gen-plan",
    response_model=AutoGenPlanResponse,
)
async def auto_generate_plan(
    patient_id: int,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    """
    为指定患者自动生成个性化康复计划。

    流程：
    1. 验证患者归属
    2. 从数据库获取患者信息
    3. 调用 DeepSeek API 生成计划
    4. 解析 JSON 并创建 PatientRehabPlan 记录
    """
    # ── 1. 验证患者归属 ──
    patient_stmt = select(Patient).where(
        Patient.id == patient_id,
        Patient.attending_doctor_id == current_doctor.id,
    )
    patient_result = await db.execute(patient_stmt)
    patient = patient_result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="患者不存在或非当前医生负责",
        )

    # ── 2. 校验必要字段 ──
    discharge_summary = patient.discharge_summary or "（未提供）"
    surgery_date = patient.surgery_date
    name = patient.name or "（未提供）"

    # ── 3. 构建 Prompt ──
    age_info = ""
    surgery_date_str = surgery_date.isoformat() if surgery_date else "（未提供）"

    prompt = (
        "你是一个康复专家。根据以下患者信息，生成一个个性化的康复计划。计划应包含：\n"
        "- 计划名称（简短）\n"
        "- 若干阶段，每个阶段有名称、持续天数（单位：天）\n"
        "- 每个阶段下包含若干任务，每个任务有类型（exercise/questionnaire/education）、名称、频率（如\"每天2次\"）\n\n"
        "患者信息：\n"
        f"- 诊断：{discharge_summary}\n"
        f"- 手术日期：{surgery_date_str}\n"
        f"- 姓名：{name}\n"
        f"{age_info}"
        "\n"
        '输出格式为严格的 JSON，结构如下：\n'
        '{\n'
        ' "name": "计划名称",\n'
        ' "phases": [\n'
        '  {\n'
        '   "name": "阶段名称",\n'
        '   "duration_days": 数字,\n'
        '   "tasks": [\n'
        '    { "type": "exercise", "name": "任务名称", "frequency": "每天X次" }\n'
        '   ]\n'
        '  }\n'
        ' ]\n'
        '}\n\n'
        "注意：只返回 JSON，不要包含多余的说明文字。"
    )

    # ── 4. 调用 DeepSeek API ──
    try:
        ai_client = get_ai_client()
        response = ai_client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的康复医学专家，擅长根据患者情况制定个性化的康复计划。只输出JSON，不要多余文字。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            top_p=1.0,
            extra_body={"thinking_mode": "non-thinking"},
        )
        raw_content = response.choices[0].message.content.strip()
        logger.info(f"DeepSeek 返回原始内容（前200字符）: {raw_content[:200]}")
    except Exception as e:
        logger.error(f"DeepSeek API 调用失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 服务调用失败: {str(e)}",
        )

    # ── 5. 解析 JSON ──
    try:
        cleaned = raw_content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        plan_data = json.loads(cleaned)
        plan_name = plan_data.get("name", "自动生成康复计划")
        phases = plan_data.get("phases", [])
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"JSON 解析失败，原始内容: {raw_content}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 返回数据解析失败: {str(e)}",
        )

    if not phases:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI 生成的计划中没有包含康复阶段",
        )

    # ── 6. 创建 RehabTemplate 保存生成的 phases ──
    template = RehabTemplate(
        disease_category="自动生成",
        name=plan_name,
        phases=phases,
        is_active=False,
    )
    db.add(template)
    await db.flush()

    # ── 7. 创建 PatientRehabPlan 记录 ──
    new_plan = PatientRehabPlan(
        patient_id=patient_id,
        template_id=template.id,
        start_date=date.today(),
        current_phase=0,
        status="active",
        source="auto_generate",
        review_status="pending",
        auto_gen_prompt=prompt,
    )
    db.add(new_plan)
    await db.flush()
    await db.commit()
    await db.refresh(new_plan)

    logger.info(
        f"✅ 自动生成康复计划成功: plan_id={new_plan.id}, patient_id={patient_id}, "
        f"name={plan_name}, phases={len(phases)}"
    )

    return AutoGenPlanResponse(
        id=new_plan.id,
        patient_id=patient_id,
        name=plan_name,
        start_date=new_plan.start_date,
        status=new_plan.status,
        source="auto_generate",
        review_status="pending",
        phases=phases,
    )


# ==================== 审核管理 ====================


@router.get(
    "/rehab_plans/pending",
    response_model=list[PendingPlanItem],
)
async def list_pending_plans(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前医生所有患者的待审核计划（review_status='pending'）。
    关联患者姓名和电话。
    """
    stmt = (
        select(PatientRehabPlan, Patient.name, Patient.phone, RehabTemplate.name)
        .join(Patient, PatientRehabPlan.patient_id == Patient.id)
        .outerjoin(RehabTemplate, PatientRehabPlan.template_id == RehabTemplate.id)
        .where(
            Patient.attending_doctor_id == current_doctor.id,
            PatientRehabPlan.review_status == "pending",
            PatientRehabPlan.source == "auto_generate",
        )
        .order_by(PatientRehabPlan.start_date.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for plan, patient_name, patient_phone, tpl_name in rows:
        items.append(PendingPlanItem(
            id=plan.id,
            patient_id=plan.patient_id,
            patient_name=patient_name,
            patient_phone=patient_phone,
            plan_name=tpl_name,
            start_date=plan.start_date,
            source=plan.source,
            review_status=plan.review_status,
            created_at=plan.id,
        ))

    return items


@router.put(
    "/rehab_plans/{plan_id}/review",
    response_model=ReviewResponse,
)
async def review_plan(
    plan_id: int,
    req: ReviewRequest,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    """
    审核康复计划。

    - action='approve': review_status → approved，自动生成每日任务
    - action='reject':  review_status → rejected，记录原因
    """
    # 验证计划属于当前医生的某个患者
    stmt = (
        select(PatientRehabPlan)
        .join(Patient, PatientRehabPlan.patient_id == Patient.id)
        .where(
            PatientRehabPlan.id == plan_id,
            Patient.attending_doctor_id == current_doctor.id,
        )
    )
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="康复计划不存在或非当前医生负责",
        )

    if req.action == "approve":
        plan.review_status = "approved"
        plan.review_comment = req.reason
        await db.commit()

        # 生成每日任务
        try:
            await generate_tasks_for_plan(plan.id)
            logger.info(f"✅ 计划 {plan_id} 审核通过，已生成每日任务")
        except Exception as e:
            logger.error(f"❌ 计划 {plan_id} 生成每日任务失败: {e}")
            return ReviewResponse(
                id=plan.id,
                patient_id=plan.patient_id,
                review_status="approved",
                review_comment=req.reason,
                status=plan.status,
                message=f"审核通过，但生成每日任务失败: {str(e)}",
            )

        return ReviewResponse(
            id=plan.id,
            patient_id=plan.patient_id,
            review_status="approved",
            review_comment=req.reason,
            status=plan.status,
            message="审核通过，每日任务已生成",
        )

    elif req.action == "reject":
        plan.review_status = "rejected"
        plan.review_comment = req.reason or "未通过审核"
        plan.status = "paused"
        await db.commit()

        return ReviewResponse(
            id=plan.id,
            patient_id=plan.patient_id,
            review_status="rejected",
            review_comment=req.reason,
            status="paused",
            message="计划已驳回",
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="action 必须是 'approve' 或 'reject'",
        )
