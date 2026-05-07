# 康复数据记录模型
from sqlalchemy import Column, Integer, Float, Date, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from datetime import datetime
from database.db import Base


class RehabRecord(Base):
    """康复数据记录"""
    __tablename__ = "rehab_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    # 记录日期
    record_date = Column(Date, nullable=False)

    # 疼痛评分 (0-10)
    pain_score = Column(Float, nullable=True)

    # 训练完成度 (0-100%)
    training_completion = Column(Float, nullable=True)

    # 血压 - 收缩压
    blood_pressure_systolic = Column(Integer, nullable=True)

    # 血压 - 舒张压
    blood_pressure_diastolic = Column(Integer, nullable=True)

    # 血糖 (mmol/L)
    blood_sugar = Column(Float, nullable=True)

    # 备注
    notes = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    patient = relationship("Patient", back_populates="rehab_records")