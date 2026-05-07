# 康复数据 Schema 定义
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime


# ============ 请求 Schema ============

class RehabRecordCreate(BaseModel):
    """创建康复记录请求"""
    patient_id: int = Field(..., description="患者ID")
    record_date: date = Field(..., description="记录日期")
    pain_score: Optional[float] = Field(None, ge=0, le=10, description="疼痛评分 (0-10)")
    training_completion: Optional[float] = Field(None, ge=0, le=100, description="训练完成度 (0-100%)")
    blood_pressure_systolic: Optional[int] = Field(None, ge=60, le=250, description="收缩压")
    blood_pressure_diastolic: Optional[int] = Field(None, ge=40, le=150, description="舒张压")
    blood_sugar: Optional[float] = Field(None, ge=1.0, le=30.0, description="血糖 (mmol/L)")
    notes: Optional[str] = Field(None, max_length=500, description="备注")

    @validator("blood_pressure_systolic")
    def validate_systolic(cls, v):
        if v is not None and v < 60:
            raise ValueError("收缩压不能低于60")
        return v

    @validator("blood_pressure_diastolic")
    def validate_diastolic(cls, v):
        if v is not None and v < 40:
            raise ValueError("舒张压不能低于40")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": 1,
                "record_date": "2026-05-07",
                "pain_score": 3.5,
                "training_completion": 85.0,
                "blood_pressure_systolic": 120,
                "blood_pressure_diastolic": 80,
                "blood_sugar": 5.6,
                "notes": "今日训练完成情况良好"
            }
        }


class RehabRecordUpdate(BaseModel):
    """更新康复记录请求"""
    pain_score: Optional[float] = Field(None, ge=0, le=10, description="疼痛评分")
    training_completion: Optional[float] = Field(None, ge=0, le=100, description="训练完成度")
    blood_pressure_systolic: Optional[int] = Field(None, ge=60, le=250, description="收缩压")
    blood_pressure_diastolic: Optional[int] = Field(None, ge=40, le=150, description="舒张压")
    blood_sugar: Optional[float] = Field(None, ge=1.0, le=30.0, description="血糖")
    notes: Optional[str] = Field(None, max_length=500, description="备注")


# ============ 响应 Schema ============

class RehabRecordResponse(BaseModel):
    """康复记录响应"""
    id: int
    patient_id: int
    record_date: date
    pain_score: Optional[float] = None
    training_completion: Optional[float] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    blood_sugar: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RehabRecordListResponse(BaseModel):
    """康复记录列表响应"""
    total: int
    records: List[RehabRecordResponse]


class RehabRecordLatestResponse(BaseModel):
    """最新康复记录响应"""
    record: Optional[RehabRecordResponse] = None
    message: Optional[str] = None


# ============ 错误响应 ============

class ErrorResponse(BaseModel):
    """错误响应"""
    detail: str
    code: Optional[str] = None