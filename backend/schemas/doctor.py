from pydantic import BaseModel
from typing import Optional, Any
from datetime import date, datetime


class PatientListItem(BaseModel):
    """患者列表项"""
    id: int
    name: Optional[str] = None
    hospital_patient_id: str
    department: Optional[str] = None
    discharge_summary: Optional[str] = None
    surgery_date: Optional[date] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RehabPlanSummary(BaseModel):
    """康复计划摘要"""
    id: int
    template_id: int
    template_name: Optional[str] = None
    start_date: Optional[date] = None
    current_phase: int = 0
    status: str = "active"

    model_config = {"from_attributes": True}


class PatientDetail(BaseModel):
    """患者详细信息"""
    id: int
    name: Optional[str] = None
    hospital_patient_id: str
    phone: Optional[str] = None
    department: Optional[str] = None
    attending_doctor_id: Optional[int] = None
    discharge_summary: Optional[str] = None
    surgery_date: Optional[date] = None
    created_at: Optional[datetime] = None
    rehab_plans: list[RehabPlanSummary] = []

    model_config = {"from_attributes": True}


class PatientUpdate(BaseModel):
    """患者信息更新请求"""
    discharge_summary: Optional[str] = None


class RehabTemplateItem(BaseModel):
    """康复模板项"""
    id: int
    disease_category: Optional[str] = None
    name: Optional[str] = None
    phases: Optional[Any] = None
    is_active: Optional[bool] = True

    model_config = {"from_attributes": True}


class RehabPlanCreate(BaseModel):
    """创建康复计划请求"""
    template_id: int
    start_date: date


class RehabPlanCreated(BaseModel):
    """创建康复计划响应"""
    id: int
    patient_id: int
    template_id: int
    start_date: Optional[date] = None
    current_phase: int = 0
    status: str = "active"
    tasks_created: int = 0

    model_config = {"from_attributes": True}


class DailyTaskItem(BaseModel):
    """每日任务项"""
    id: int
    plan_id: Optional[int] = None
    task_date: Optional[date] = None
    task_type: Optional[str] = None
    task_content: Optional[Any] = None
    status: str = "pending"
    completed_at: Optional[datetime] = None
    result_data: Optional[Any] = None

    model_config = {"from_attributes": True}


class TaskRecordRequest(BaseModel):
    """任务完成记录请求"""
    result_data: Optional[dict] = None


class TaskRecordResponse(BaseModel):
    """任务完成记录响应"""
    id: int
    status: str
    completed_at: Optional[datetime] = None
    result_data: Optional[Any] = None
    message: str = "任务记录已更新"
