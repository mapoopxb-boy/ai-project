# 康复数据 API 路由
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional
from datetime import date

from database.db import get_db
from models.rehab_record import RehabRecord
from models.patient import Patient
from schemas.rehab_record import (
    RehabRecordCreate,
    RehabRecordUpdate,
    RehabRecordResponse,
    RehabRecordListResponse,
    RehabRecordLatestResponse,
)

router = APIRouter(prefix="/api/rehab", tags=["康复数据"])


# ============ 辅助函数 ============

async def get_patient_or_404(db: AsyncSession, patient_id: int) -> Patient:
    """获取患者，不存在则抛出404"""
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"患者ID {patient_id} 不存在"
        )
    return patient


# ============ API 端点 ============


@router.post(
    "/records",
    response_model=RehabRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="提交每日康复数据"
)
async def create_rehab_record(
    record: RehabRecordCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    提交每日康复数据

    - **patient_id**: 患者ID
    - **record_date**: 记录日期
    - **pain_score**: 疼痛评分 (0-10)
    - **training_completion**: 训练完成度 (0-100%)
    - **blood_pressure_systolic**: 收缩压
    - **blood_pressure_diastolic**: 舒张压
    - **blood_sugar**: 血糖 (mmol/L)
    - **notes**: 备注
    """
    # 验证患者是否存在
    await get_patient_or_404(db, record.patient_id)

    # 检查同一天是否已有记录
    result = await db.execute(
        select(RehabRecord).where(
            RehabRecord.patient_id == record.patient_id,
            RehabRecord.record_date == record.record_date
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"患者 {record.patient_id} 在 {record.record_date} 已存在康复记录"
        )

    # 创建新记录
    db_record = RehabRecord(**record.model_dump())
    db.add(db_record)
    await db.commit()
    await db.refresh(db_record)

    return db_record


@router.get(
    "/patients/{patient_id}/records",
    response_model=RehabRecordListResponse,
    summary="获取患者历史记录"
)
async def get_patient_records(
    patient_id: int,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(30, ge=1, le=100, description="返回记录数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取患者历史康复记录

    - **patient_id**: 患者ID
    - **start_date**: 开始日期筛选（可选）
    - **end_date**: 结束日期筛选（可选）
    - **limit**: 返回记录数限制（默认30，最大100）
    - **offset**: 偏移量（用于分页）
    """
    # 验证患者是否存在
    await get_patient_or_404(db, patient_id)

    # 构建查询
    query = select(RehabRecord).where(RehabRecord.patient_id == patient_id)

    if start_date:
        query = query.where(RehabRecord.record_date >= start_date)
    if end_date:
        query = query.where(RehabRecord.record_date <= end_date)

    # 获取总数
    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 获取分页结果
    query = query.order_by(desc(RehabRecord.record_date)).offset(offset).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    return {"total": total, "records": records}


@router.get(
    "/patients/{patient_id}/records/latest",
    response_model=RehabRecordLatestResponse,
    summary="获取最新一条记录"
)
async def get_latest_record(
    patient_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取患者最新的一条康复记录

    - **patient_id**: 患者ID
    """
    # 验证患者是否存在
    await get_patient_or_404(db, patient_id)

    # 查询最新记录
    result = await db.execute(
        select(RehabRecord)
        .where(RehabRecord.patient_id == patient_id)
        .order_by(desc(RehabRecord.record_date))
        .limit(1)
    )
    record = result.scalar_one_or_none()

    if not record:
        return {
            "record": None,
            "message": "暂无康复记录"
        }

    return {"record": record}


@router.get(
    "/records/{record_id}",
    response_model=RehabRecordResponse,
    summary="获取单条记录详情"
)
async def get_record_by_id(
    record_id: int,
    db: AsyncSession = Depends(get_db)
):
    """根据记录ID获取康复记录详情"""
    result = await db.execute(select(RehabRecord).where(RehabRecord.id == record_id))
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"记录ID {record_id} 不存在"
        )

    return record


@router.put(
    "/records/{record_id}",
    response_model=RehabRecordResponse,
    summary="更新康复记录"
)
async def update_rehab_record(
    record_id: int,
    record_update: RehabRecordUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新康复记录"""
    result = await db.execute(select(RehabRecord).where(RehabRecord.id == record_id))
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"记录ID {record_id} 不存在"
        )

    # 更新非空字段
    update_data = record_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    await db.commit()
    await db.refresh(record)

    return record


@router.delete(
    "/records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除康复记录"
)
async def delete_rehab_record(
    record_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除康复记录"""
    result = await db.execute(select(RehabRecord).where(RehabRecord.id == record_id))
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"记录ID {record_id} 不存在"
        )

    await db.delete(record)
    await db.commit()

    return None