"""
数据库初始化脚本
手动执行，幂等设计（重复运行不会出错）。
用法: python init_db.py
"""

import asyncio
import bcrypt
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import engine, Base, AsyncSessionLocal
from models.patient import Doctor, Patient, RehabTemplate


async def init_db():
    async with AsyncSessionLocal() as session:
        # ---------- 1. 创建所有表（幂等） ----------
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ 数据库表创建/已存在")

        # ---------- 2. 检查是否已初始化 ----------
        result = await session.execute(select(Doctor).limit(1))
        existing_doctor = result.scalar_one_or_none()
        if existing_doctor:
            print("ℹ️  数据库已初始化，跳过演示数据写入")
            return

        # ---------- 3. 演示医生 ----------
        hashed = bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode("utf-8")
        doctor = Doctor(
            name="演示医生",
            department="康复科",
            phone="13800001111",
            login_name="demo_doctor",
            password_hash=hashed,
        )
        session.add(doctor)
        await session.flush()  # 获取 doctor.id
        print("✅ 创建演示医生: demo_doctor / 123456")

        # ---------- 4. 演示患者 ----------
        patient = Patient(
            hospital_patient_id="P2026001",
            name="张明",
            phone="13900001111",
            department="康复科",
            attending_doctor_id=doctor.id,
            discharge_summary="患者因右膝关节置换术后入院，术后恢复良好，建议进行系统康复训练。",
            surgery_date=date(2026, 4, 15),
        )
        session.add(patient)
        await session.flush()
        print(f"✅ 创建演示患者: {patient.name}（ID: {patient.id}）")

        # ---------- 5. 康复计划模板 ----------
        template = RehabTemplate(
            disease_category="骨科",
            name="膝关节置换术后康复方案",
            phases=[
                {
                    "name": "早期（术后1-2周）",
                    "duration_days": 14,
                    "tasks": [
                        {"type": "exercise", "name": "踝泵运动", "frequency": "每日3组，每组10次"},
                        {"type": "exercise", "name": "股四头肌等长收缩", "frequency": "每日3组，每组10次"},
                        {"type": "medication", "name": "口服止痛药", "frequency": "遵医嘱"},
                        {"type": "questionnaire", "name": "疼痛评分", "frequency": "每日1次"},
                    ],
                },
                {
                    "name": "中期（术后3-6周）",
                    "duration_days": 28,
                    "tasks": [
                        {"type": "exercise", "name": "膝关节被动屈伸", "frequency": "每日2次，每次15分钟"},
                        {"type": "exercise", "name": "直腿抬高训练", "frequency": "每日3组，每组8次"},
                        {"type": "exercise", "name": "站立位重心转移", "frequency": "每日2次，每次10分钟"},
                        {"type": "questionnaire", "name": "疼痛评分", "frequency": "每日1次"},
                        {"type": "photo", "name": "手术伤口拍照", "frequency": "每2日1次"},
                    ],
                },
                {
                    "name": "后期（术后7-12周）",
                    "duration_days": 42,
                    "tasks": [
                        {"type": "exercise", "name": "靠墙静蹲", "frequency": "每日2组，每组30秒"},
                        {"type": "exercise", "name": "上下楼梯训练", "frequency": "每日2次，每次5组"},
                        {"type": "exercise", "name": "步行训练", "frequency": "每日2次，每次15分钟"},
                        {"type": "questionnaire", "name": "疼痛评分", "frequency": "每周2次"},
                    ],
                },
            ],
            is_active=True,
        )
        session.add(template)
        print("✅ 创建康复计划模板: 膝关节置换术后康复方案")

        # ---------- 提交 ----------
        await session.commit()
        print("✅ 演示数据写入完成")


# 直接运行此脚本时执行初始化并清理引擎
if __name__ == "__main__":
    async def cli_main():
        try:
            await init_db()
        finally:
            await engine.dispose()
    asyncio.run(cli_main())
