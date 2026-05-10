from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import json
import logging

from database.db import get_db
from models import Doctor, Patient, RehabTemplate, PatientRehabPlan, DailyTask
from api.dependencies import get_current_doctor
from schemas.doctor import (
    PatientListItem,
    PatientDetail,
    PatientUpdate,
    RehabTemplateItem,
    RehabPlanCreate,
    RehabPlanCreated,
    DailyTaskItem,
    TaskRecordRequest,
    TaskRecordResponse,
    RehabPlanSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["医生端"])


# ==================== 患者管理 ====================


@router.get("/patients", response_model=list[PatientListItem])
async def list_patients(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    """获取当前医生负责的所有患者列表，按创建时间倒序排列。"""
    stmt = (
        select(Patient)
        .where(Patient.attending_doctor_id == current_doctor.id)
        .order_by(Patient.created_at.desc())
    )
    result = await db.execute(stmt)
    patients = result.scalars().all()
    return [PatientListItem.model_validate(p) for p in patients]


@router.get("/patients/{patient_id}", response_model=PatientDetail)
async def get_patient(
    patient_id: int,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    """获取特定患者的详细信息，包含基本信息、诊断及康复计划列表。"""
    stmt = (
        select(Patient)
        .options(selectinload(Patient.rehab_plans))
        .where(Patient.id == patient_id, Patient.attending_doctor_id == current_doctor.id)
    )
    result = await db.execute(stmt)
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="患者不存在或非当前医生负责",
        )

    detail = PatientDetail.model_validate(patient)

    # 填充康复计划的模板名称
    for plan_summary in detail.rehab_plans:
        tpl_result = await db.execute(
            select(RehabTemplate.name).where(RehabTemplate.id == plan_summary.template_id)
        )
        tpl_name = tpl_result.scalar_one_or_none()
        plan_summary.template_name = tpl_name

    return detail


@router.put("/patients/{patient_id}", response_model=PatientDetail)
async def update_patient(
    patient_id: int,
    update: PatientUpdate,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    """更新患者的核心信息，如诊断（discharge_summary）。"""
    stmt = (
        select(Patient)
        .options(selectinload(Patient.rehab_plans))
        .where(
            Patient.id == patient_id,
            Patient.attending_doctor_id == current_doctor.id
        )
    )
    result = await db.execute(stmt)
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="患者不存在或非当前医生负责",
        )

    # 更新非空字段
    update_data = update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未提供需要更新的字段",
        )

    for field, value in update_data.items():
        setattr(patient, field, value)

    await db.commit()
    await db.refresh(patient)

    # 手动构建返回，避免惰性加载问题
    from sqlalchemy.orm import selectinload as _sl
    stmt_patient = (
        select(Patient)
        .options(_sl(Patient.rehab_plans))
        .where(Patient.id == patient_id)
    )
    result_patient = await db.execute(stmt_patient)
    refreshed_patient = result_patient.scalar_one_or_none()

    if not refreshed_patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="患者不存在",
        )

    detail = PatientDetail.model_validate(refreshed_patient)

    # 填充康复计划的模板名称
    for plan_summary in detail.rehab_plans:
        tpl_result = await db.execute(
            select(RehabTemplate.name).where(
                RehabTemplate.id == plan_summary.template_id
            )
        )
        tpl_name = tpl_result.scalar_one_or_none()
        plan_summary.template_name = tpl_name

    return detail


# ==================== 康复计划管理 ====================


@router.get("/rehab_templates", response_model=list[RehabTemplateItem])
async def list_rehab_templates(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    """获取系统中所有可用的康复模板列表。"""
    stmt = select(RehabTemplate).where(RehabTemplate.is_active == True)
    result = await db.execute(stmt)
    templates = result.scalars().all()
    return [RehabTemplateItem.model_validate(t) for t in templates]


@router.post("/patients/{patient_id}/rehab_plan", response_model=RehabPlanCreated)
async def create_rehab_plan(
    patient_id: int,
    req: RehabPlanCreate,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    """
    为指定患者创建新的康复计划。
    系统根据模板阶段自动生成每日任务。
    """
    # 验证患者归属
    patient_stmt = select(Patient).where(
        Patient.id == patient_id, Patient.attending_doctor_id == current_doctor.id
    )
    patient_result = await db.execute(patient_stmt)
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="患者不存在或非当前医生负责",
        )

    # 验证模板
    tpl_stmt = select(RehabTemplate).where(RehabTemplate.id == req.template_id)
    tpl_result = await db.execute(tpl_stmt)
    template = tpl_result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="康复模板不存在",
        )

    # 检查是否已有该患者的活跃计划
    active_stmt = select(PatientRehabPlan).where(
        PatientRehabPlan.patient_id == patient_id,
        PatientRehabPlan.status == "active",
    )
    active_result = await db.execute(active_stmt)
    if active_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该患者已有活跃的康复计划，请先完成或暂停现有计划",
        )

    # 创建康复计划
    new_plan = PatientRehabPlan(
        patient_id=patient_id,
        template_id=req.template_id,
        start_date=req.start_date,
        current_phase=0,
        status="active",
    )
    db.add(new_plan)
    await db.flush()  # 获取 new_plan.id

    # 解析阶段数据，自动生成每日任务
    phases = template.phases
    tasks_created = 0
    if phases and isinstance(phases, list):
        for phase_idx, phase in enumerate(phases):
            phase_tasks = phase.get("tasks", []) if isinstance(phase, dict) else []
            duration_days = phase.get("duration_days", 7) if isinstance(phase, dict) else 7

            for task_template in phase_tasks:
                task_type = task_template.get("type", "exercise")
                task_name = task_template.get("name", "")

                # 根据频次计算哪些日期需要生成任务
                frequency = task_template.get("frequency", "每天")
                for day_offset in range(duration_days):
                    task_date = req.start_date + timedelta(days=day_offset + phase_idx * duration_days)

                    # 简单的频次过滤
                    if frequency == "每天":
                        should_create = True
                    elif frequency in ["每周1次", "每周3次"]:
                        should_create = (day_offset % 7) < int(frequency[2]) if len(frequency) > 2 else True
                    elif frequency in ["每2天1次", "每2天"]:
                        should_create = day_offset % 2 == 0
                    elif "每" in frequency and "次" in frequency:
                        # "每2天1次" 或 "每2天3次"
                        try:
                            interval = int(frequency[1])
                            should_create = day_offset % interval == 0
                        except (ValueError, IndexError):
                            should_create = True
                    else:
                        should_create = True

                    if should_create:
                        task_content = task_template.copy()
                        task_content.pop("type", None)
                        task_content.pop("frequency", None)

                        daily_task = DailyTask(
                            plan_id=new_plan.id,
                            task_date=task_date,
                            task_type=task_type,
                            task_content=json.dumps(task_content, ensure_ascii=False) if isinstance(task_content, dict) else task_content,
                            status="pending",
                        )
                        db.add(daily_task)
                        tasks_created += 1

    await db.commit()
    await db.refresh(new_plan)

    return RehabPlanCreated(
        id=new_plan.id,
        patient_id=new_plan.patient_id,
        template_id=new_plan.template_id,
        start_date=new_plan.start_date,
        current_phase=new_plan.current_phase,
        status=new_plan.status,
        tasks_created=tasks_created,
    )


# ==================== 任务跟踪与数据管理 ====================


@router.get("/patients/{patient_id}/daily_tasks", response_model=list[DailyTaskItem])
async def list_daily_tasks(
    patient_id: int,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    """获取特定患者的所有每日任务清单。"""
    # 验证患者归属
    patient_stmt = select(Patient).where(
        Patient.id == patient_id, Patient.attending_doctor_id == current_doctor.id
    )
    patient_result = await db.execute(patient_stmt)
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="患者不存在或非当前医生负责",
        )

    # 获取患者的所有康复计划 ID
    plans_stmt = select(PatientRehabPlan.id).where(
        PatientRehabPlan.patient_id == patient_id
    )
    plans_result = await db.execute(plans_stmt)
    plan_ids = plans_result.scalars().all()

    if not plan_ids:
        return []

    # 获取所有每日任务，按日期正序排列
    tasks_stmt = (
        select(DailyTask)
        .where(DailyTask.plan_id.in_(plan_ids))
        .order_by(DailyTask.task_date.asc(), DailyTask.id.asc())
    )
    tasks_result = await db.execute(tasks_stmt)
    tasks = tasks_result.scalars().all()

    items = []
    for task in tasks:
        item = DailyTaskItem.model_validate(task)
        # 将字符串 task_content 转回 dict 方便前端使用
        if isinstance(item.task_content, str):
            try:
                item.task_content = json.loads(item.task_content)
            except (json.JSONDecodeError, TypeError):
                pass
        items.append(item)

    return items


@router.post(
    "/patients/{patient_id}/daily_tasks/{task_id}/record",
    response_model=TaskRecordResponse,
)
async def record_daily_task(
    patient_id: int,
    task_id: int,
    req: TaskRecordRequest,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    """为患者记录特定任务的完成情况。"""
    # 验证患者归属
    patient_stmt = select(Patient).where(
        Patient.id == patient_id, Patient.attending_doctor_id == current_doctor.id
    )
    patient_result = await db.execute(patient_stmt)
    patient = patient_result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="患者不存在或非当前医生负责",
        )

    # 验证任务属于该患者（通过康复计划关联）
    task_stmt = (
        select(DailyTask)
        .join(PatientRehabPlan, DailyTask.plan_id == PatientRehabPlan.id)
        .where(
            DailyTask.id == task_id,
            PatientRehabPlan.patient_id == patient_id,
        )
    )
    task_result = await db.execute(task_stmt)
    task = task_result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在或不属于该患者",
        )

    # 更新任务
    task.status = "done"
    task.completed_at = datetime.utcnow()
    if req.result_data:
        task.result_data = json.dumps(req.result_data, ensure_ascii=False)

    await db.commit()
    await db.refresh(task)

    result_data = task.result_data
    if isinstance(result_data, str):
        try:
            result_data = json.loads(result_data)
        except (json.JSONDecodeError, TypeError):
            pass

    return TaskRecordResponse(
        id=task.id,
        status=task.status,
        completed_at=task.completed_at,
        result_data=result_data,
        message="任务记录已更新",
    )
