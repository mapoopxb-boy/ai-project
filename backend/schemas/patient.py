from pydantic import BaseModel
from typing import Optional, Any
from datetime import date, datetime


class PatientLogin(BaseModel):
    """患者登录请求"""
    phone: str
    password: str


class PatientToken(BaseModel):
    """患者 JWT Token 响应"""
    access_token: str
    token_type: str = "bearer"


class DoctorBrief(BaseModel):
    """负责医师简要信息"""
    id: int
    name: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None

    model_config = {"from_attributes": True}


class PatientProfile(BaseModel):
    """患者个人信息（含负责医师）"""
    id: int
    name: Optional[str] = None
    hospital_patient_id: str
    phone: Optional[str] = None
    department: Optional[str] = None
    discharge_summary: Optional[str] = None
    surgery_date: Optional[date] = None
    created_at: Optional[datetime] = None
    doctor: Optional[DoctorBrief] = None

    model_config = {"from_attributes": True}


class TaskContent(BaseModel):
    """每日任务内容"""
    id: int
    task_date: Optional[date] = None
    task_type: Optional[str] = None
    task_content: Optional[Any] = None
    status: str = "pending"
    completed_at: Optional[datetime] = None
    result_data: Optional[Any] = None

    model_config = {"from_attributes": True}


class PhaseInfo(BaseModel):
    """康复阶段信息"""
    phase_index: int = 0
    phase_name: str = ""
    duration_days: int = 0

    model_config = {"from_attributes": True}


class RehabPlanPatient(BaseModel):
    """患者视角的康复计划详情"""
    id: int
    template_id: int
    template_name: Optional[str] = None
    disease_category: Optional[str] = None
    start_date: Optional[date] = None
    current_phase: int = 0
    total_phases: int = 0
    phases_info: list[PhaseInfo] = []
    status: str = "active"
    tasks: list[TaskContent] = []

    model_config = {"from_attributes": True}


class TaskCompleteRequest(BaseModel):
    """标记任务完成请求"""
    result_data: Optional[dict] = None


class TaskCompleteResponse(BaseModel):
    """标记任务完成响应"""
    id: int
    status: str
    completed_at: Optional[datetime] = None
    message: str = "任务已完成"


class HealthDataPoint(BaseModel):
    """健康数据点（用于图表）"""
    record_date: str  # YYYY-MM-DD
    pain_score: Optional[float] = None
    training_completion: Optional[float] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    blood_sugar: Optional[float] = None


class ChatRequest(BaseModel):
    """患者 AI 对话请求"""
    user_input: str
    user_id: Optional[str] = None  # 可选，不传则使用当前患者 ID


class ChatResponse(BaseModel):
    """患者 AI 对话响应"""
    code: int = 200
    answer: str
    processing_time: Optional[float] = None
