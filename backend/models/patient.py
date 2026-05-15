from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database.db import Base

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True, index=True)
    hospital_patient_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(50))
    phone = Column(String(20))
    department = Column(String(50))
    attending_doctor_id = Column(Integer, ForeignKey("doctors.id"))
    discharge_summary = Column(Text)
    surgery_date = Column(Date)
    password_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    doctor = relationship("Doctor", back_populates="patients")
    rehab_plans = relationship("PatientRehabPlan", back_populates="patient")
    rehab_records = relationship("RehabRecord", back_populates="patient")
    alerts = relationship("Alert", back_populates="patient")
    messages = relationship("Message", back_populates="patient")

class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    department = Column(String(50))
    phone = Column(String(20))
    login_name = Column(String(50), unique=True)
    password_hash = Column(String(255))

    patients = relationship("Patient", back_populates="doctor")
    messages = relationship("Message", back_populates="doctor")

class RehabTemplate(Base):
    __tablename__ = "rehab_templates"
    id = Column(Integer, primary_key=True, index=True)
    disease_category = Column(String(50))
    name = Column(String(100))
    phases = Column(JSON)       # 存储各阶段的任务定义
    is_active = Column(Boolean, default=True)

class PatientRehabPlan(Base):
    __tablename__ = "patient_rehab_plans"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    template_id = Column(Integer, ForeignKey("rehab_templates.id"))
    start_date = Column(Date)
    current_phase = Column(Integer, default=0)
    status = Column(String(20), default="active")   # active, completed, paused
    source = Column(String(30), nullable=True, default=None)  # manual, auto_generate, template
    review_status = Column(String(20), nullable=True, default=None)  # pending, approved, rejected
    review_comment = Column(Text, nullable=True, default=None)
    auto_gen_prompt = Column(Text, nullable=True, default=None)

    patient = relationship("Patient", back_populates="rehab_plans")
    daily_tasks = relationship("DailyTask", back_populates="plan")

class DailyTask(Base):
    __tablename__ = "daily_tasks"
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("patient_rehab_plans.id"))
    task_date = Column(Date)
    task_type = Column(String(30))  # medication, exercise, questionnaire, photo
    task_content = Column(JSON)
    status = Column(String(20), default="pending")  # pending, done, skipped
    completed_at = Column(DateTime, nullable=True)
    result_data = Column(JSON, nullable=True)
    source = Column(String(30), nullable=True, default=None)  # template, auto_generate, manual
    review_status = Column(String(20), nullable=True, default=None)  # pending, approved, rejected

    plan = relationship("PatientRehabPlan", back_populates="daily_tasks")

class AlertRule(Base):
    __tablename__ = "alert_rules"
    id = Column(Integer, primary_key=True, index=True)
    indicator = Column(String(30))  # pain_score, blood_pressure_systolic...
    threshold_value = Column(Integer)
    operator = Column(String(5))   # ">", ">=", "<", "<="
    severity = Column(String(20))  # low, medium, high

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    rule_id = Column(Integer, ForeignKey("alert_rules.id"))
    triggered_value = Column(Integer)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
    resolved_by = Column(Integer, ForeignKey("doctors.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="alerts")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    content = Column(Text)
    is_from_patient = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="messages")
    doctor = relationship("Doctor", back_populates="messages")
