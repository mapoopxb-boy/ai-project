from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import date, datetime, timedelta
import json
import logging
import time

from database.db import get_db
from models import Patient, Doctor, PatientRehabPlan, DailyTask, RehabRecord, RehabTemplate
from api.dependencies import get_current_patient
from utils.auth import verify_password, create_access_token, hash_password
from schemas.patient import (
    PatientLogin,
    PatientToken,
    PatientProfile,
    DoctorBrief,
    RehabPlanPatient,
    TaskContent,
    PhaseInfo,
    TaskCompleteRequest,
    TaskCompleteResponse,
    HealthDataPoint,
    ChatRequest,
    ChatResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["患者端"])


# ==================== 患者登录 ====================


@router.post("/login", response_model=PatientToken)
async def patient_login(
    req: PatientLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    患者使用手机号和密码登录。
    默认密码为手机号后 6 位。
    返回 JWT token，role="patient"。
    """
    logger.info(f"患者登录尝试: phone={req.phone}")

    stmt = select(Patient).where(Patient.phone == req.phone)
    result = await db.execute(stmt)
    patient = result.scalar_one_or_none()

    if not patient:
        logger.warning(f"登录失败：患者不存在 - {req.phone}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="手机号或密码错误",
        )

    # 验证密码
    default_password = patient.phone[-6:] if patient.phone else ""
    if patient.password_hash:
        if not verify_password(req.password, patient.password_hash):
            logger.warning(f"登录失败：密码错误 - {req.phone}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="手机号或密码错误",
            )
    else:
        # 兼容未设置密码的患者：使用默认密码（手机号后6位）
        if req.password != default_password:
            logger.warning(f"登录失败：默认密码错误 - {req.phone}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="手机号或密码错误",
            )

    access_token = create_access_token(
        data={"sub": str(patient.id)},
        role="patient",
        expires_delta=timedelta(days=30),
    )

    logger.info(f"患者登录成功: id={patient.id}, name={patient.name}")
    return PatientToken(access_token=access_token)


# ==================== 患者个人资料 ====================


@router.get("/profile", response_model=PatientProfile)
async def get_profile(
    current_patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """获取患者个人信息及负责医师信息。"""
    # 加载负责医师
    if current_patient.attending_doctor_id:
        doctor_stmt = select(Doctor).where(
            Doctor.id == current_patient.attending_doctor_id
        )
        doctor_result = await db.execute(doctor_stmt)
        doctor = doctor_result.scalar_one_or_none()
        doctor_brief = DoctorBrief.model_validate(doctor) if doctor else None
    else:
        doctor_brief = None

    profile = PatientProfile.model_validate(current_patient)
    profile.doctor = doctor_brief
    return profile


# ==================== 当前康复计划 ====================


@router.get("/rehab_plan", response_model=RehabPlanPatient)
async def get_rehab_plan(
    current_patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """获取当前激活的康复计划详情（含模板信息和每日任务）。"""
    # 查找当前患者的活跃康复计划
    plan_stmt = (
        select(PatientRehabPlan)
        .options(selectinload(PatientRehabPlan.daily_tasks))
        .where(
            PatientRehabPlan.patient_id == current_patient.id,
            PatientRehabPlan.status == "active",
        )
        .order_by(PatientRehabPlan.start_date.desc())
        .limit(1)
    )
    plan_result = await db.execute(plan_stmt)
    plan = plan_result.scalar_one_or_none()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="暂无激活的康复计划",
        )

    # 获取模板信息
    tpl_stmt = select(RehabTemplate).where(RehabTemplate.id == plan.template_id)
    tpl_result = await db.execute(tpl_stmt)
    template = tpl_result.scalar_one_or_none()

    # 解析阶段信息
    phases_info: list[PhaseInfo] = []
    total_phases = 0
    if template and template.phases:
        phases_data = template.phases
        if isinstance(phases_data, list):
            total_phases = len(phases_data)
            for idx, phase in enumerate(phases_data):
                if isinstance(phase, dict):
                    phases_info.append(
                        PhaseInfo(
                            phase_index=idx,
                            phase_name=phase.get("name", f"第{idx+1}阶段"),
                            duration_days=phase.get("duration_days", 7),
                        )
                    )

    # 处理每日任务
    tasks = []
    for dt in plan.daily_tasks:
        content = dt.task_content
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                pass

        result_data = dt.result_data
        if isinstance(result_data, str):
            try:
                result_data = json.loads(result_data)
            except (json.JSONDecodeError, TypeError):
                pass

        tasks.append(
            TaskContent(
                id=dt.id,
                task_date=dt.task_date,
                task_type=dt.task_type,
                task_content=content,
                status=dt.status,
                completed_at=dt.completed_at,
                result_data=result_data,
            )
        )

    return RehabPlanPatient(
        id=plan.id,
        template_id=plan.template_id,
        template_name=template.name if template else None,
        disease_category=template.disease_category if template else None,
        start_date=plan.start_date,
        current_phase=plan.current_phase,
        total_phases=total_phases,
        phases_info=phases_info,
        status=plan.status,
        tasks=tasks,
    )


# ==================== 每日任务 ====================


@router.get("/daily_tasks", response_model=list[TaskContent])
async def get_daily_tasks(
    task_date: date = None,
    current_patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """
    获取今日或指定日期的待办任务列表。
    如不传 task_date，则默认查询今天。
    """
    query_date = task_date or date.today()
    logger.info(
        f"患者 {current_patient.id} 查询 {query_date} 的每日任务"
    )

    # 获取患者的所有康复计划 ID
    plans_stmt = select(PatientRehabPlan.id).where(
        PatientRehabPlan.patient_id == current_patient.id
    )
    plans_result = await db.execute(plans_stmt)
    plan_ids = plans_result.scalars().all()

    if not plan_ids:
        return []

    # 查询指定日期的任务
    tasks_stmt = (
        select(DailyTask)
        .where(
            DailyTask.plan_id.in_(plan_ids),
            DailyTask.task_date == query_date,
        )
        .order_by(DailyTask.id.asc())
    )
    tasks_result = await db.execute(tasks_stmt)
    tasks = tasks_result.scalars().all()

    result = []
    for dt in tasks:
        content = dt.task_content
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                pass

        result_data = dt.result_data
        if isinstance(result_data, str):
            try:
                result_data = json.loads(result_data)
            except (json.JSONDecodeError, TypeError):
                pass

        result.append(
            TaskContent(
                id=dt.id,
                task_date=dt.task_date,
                task_type=dt.task_type,
                task_content=content,
                status=dt.status,
                completed_at=dt.completed_at,
                result_data=result_data,
            )
        )

    return result


# ==================== 标记任务完成 ====================


@router.post(
    "/daily_tasks/{task_id}/complete",
    response_model=TaskCompleteResponse,
)
async def complete_daily_task(
    task_id: int,
    req: TaskCompleteRequest,
    current_patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """
    患者标记今日任务完成，同时记录结果数据。
    """
    logger.info(
        f"患者 {current_patient.id} 尝试完成任务 {task_id}"
    )

    # 验证任务属于该患者（通过康复计划关联）
    task_stmt = (
        select(DailyTask)
        .join(PatientRehabPlan, DailyTask.plan_id == PatientRehabPlan.id)
        .where(
            DailyTask.id == task_id,
            PatientRehabPlan.patient_id == current_patient.id,
        )
    )
    task_result = await db.execute(task_stmt)
    task = task_result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或不属于当前患者",
        )

    if task.status == "done":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该任务已完成，无法重复提交",
        )

    # 更新任务状态
    task.status = "done"
    task.completed_at = datetime.utcnow()
    if req.result_data:
        task.result_data = json.dumps(req.result_data, ensure_ascii=False)

    await db.commit()
    await db.refresh(task)

    logger.info(
        f"患者 {current_patient.id} 完成任务 {task_id} (type={task.task_type})"
    )
    return TaskCompleteResponse(
        id=task.id,
        status=task.status,
        completed_at=task.completed_at,
        message="任务已完成",
    )


# ==================== 康复健康数据（图表用） ====================


@router.get("/health_data", response_model=list[HealthDataPoint])
async def get_health_data(
    days: int = 30,
    current_patient: Patient = Depends(get_current_patient),
    db: AsyncSession = Depends(get_db),
):
    """
    获取近期康复健康数据（用于图表展示）。
    默认返回最近 30 天的数据。
    """
    since = date.today() - timedelta(days=days)

    stmt = (
        select(RehabRecord)
        .where(
            RehabRecord.patient_id == current_patient.id,
            RehabRecord.record_date >= since,
        )
        .order_by(RehabRecord.record_date.asc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    return [
        HealthDataPoint(
            record_date=r.record_date.isoformat() if r.record_date else "",
            pain_score=r.pain_score,
            training_completion=r.training_completion,
            blood_pressure_systolic=r.blood_pressure_systolic,
            blood_pressure_diastolic=r.blood_pressure_diastolic,
            blood_sugar=r.blood_sugar,
        )
        for r in records
    ]


# ==================== 患者 AI 对话 ====================


@router.post("/chat", response_model=ChatResponse)
async def patient_chat(
    req: ChatRequest,
    current_patient: Patient = Depends(get_current_patient),
):
    """
    患者与 AI 助手对话（自动关联患者上下文）。
    调用原 AI 助手的流接口，输入为患者提问。
    """
    import httpx
    start_time = time.time()

    patient_name = current_patient.name or "患者"
    patient_dept = current_patient.department or ""

    # 构建带患者上下文的 prompt
    context_prompt = (
        f"【患者上下文】\n"
        f"姓名：{patient_name}\n"
        f"科室：{patient_dept}\n"
        f"诊断：{current_patient.discharge_summary or '未记录'}\n"
        f"手术日期：{current_patient.surgery_date or '未记录'}\n"
        f"住院号：{current_patient.hospital_patient_id}\n"
        f"\n"
        f"请基于以上患者信息回答以下问题，给出专业、温暖的建议。\n"
        f"---\n"
        f"{req.user_input}"
    )

    try:
        # 调用本地的 AI 助手接口
        async with httpx.AsyncClient(timeout=120) as client:
            # 内部调用 /ai-assistant 接口
            payload = {
                "user_input": context_prompt,
                "user_id": req.user_id or str(current_patient.id),
                "agent_type": "auto",
                "file_type": None,
                "file_data": None,
                "file_name": None,
            }
            response = await client.post(
                "http://127.0.0.1:8000/ai-assistant",
                json=payload,
            )
            if response.status_code == 200:
                ai_data = response.json()
                answer = ai_data.get("answer", "AI 助手暂时无法回复，请稍后再试。")
            else:
                answer = f"AI 服务暂不可用（{response.status_code}），请稍后再试。"
    except Exception as e:
        logger.error(f"AI 对话失败: {e}")
        answer = "AI 服务连接失败，请检查网络或稍后再试。"

    processing_time = time.time() - start_time
    logger.info(
        f"患者 {current_patient.id} AI 对话完成，耗时 {processing_time:.2f}s"
    )

    return ChatResponse(
        code=200,
        answer=answer,
        processing_time=round(processing_time, 2),
    )
