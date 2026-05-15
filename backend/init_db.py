"""
数据库初始化脚本
手动执行，幂等设计（重复运行不会出错）。
用法: python init_db.py
"""

import asyncio
import bcrypt
from datetime import date
from sqlalchemy import select, inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import engine, Base, AsyncSessionLocal
from models.patient import Doctor, Patient, RehabTemplate, PatientRehabPlan, DailyTask


# ================= 自动同步缺失列 =================
async def sync_missing_columns():
    """
    自动为已存在的表增加模型中新定义的列（仅添加，不删除，不修改类型）。
    幂等，重复执行不会报错。
    兼容 PostgreSQL 和 SQLite。
    """
    from sqlalchemy.dialects import sqlite, postgresql

    async with engine.begin() as conn:
        # 获取当前数据库连接的方言
        dialect = conn.dialect

        def _get_existing_tables(sync_conn):
            insp = inspect(sync_conn)
            tables = {}
            for tname in insp.get_table_names():
                tables[tname] = {c['name'] for c in insp.get_columns(tname)}
            return tables

        existing_tables = await conn.run_sync(_get_existing_tables)

        model_tables = {}
        for table in Base.metadata.sorted_tables:
            cols = {col.name for col in table.columns}
            model_tables[table.name] = cols

        for table_name, model_cols in model_tables.items():
            if table_name not in existing_tables:
                continue
            existing_cols = existing_tables[table_name]
            missing = model_cols - existing_cols
            if not missing:
                continue
            for col_name in sorted(missing):
                col_obj = next(col for col in Base.metadata.tables[table_name].columns if col.name == col_name)
                # 根据数据库方言编译类型字符串
                col_type_str = col_obj.type.compile(dialect=dialect)
                # SQLite 不支持 ALTER TABLE ADD COLUMN 时指定 NOT NULL（除非有默认值）
                # 所有新增列都设为 NULL 以避免兼容性问题
                sql = text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type_str} NULL')
                try:
                    await conn.execute(sql)
                    print(f"✅ 已添加缺失列: {table_name}.{col_name} ({col_type_str})")
                except Exception as e:
                    print(f"⚠️ 添加列 {table_name}.{col_name} 失败: {e}")


# ================= 演示数据插入 =================
async def init_db():
    # 1. 创建所有表（幂等，不会影响已有表）
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. 同步缺失的列（自动增列）
    await sync_missing_columns()

    # 3. 插入演示数据（幂等）
    async with AsyncSessionLocal() as session:
        # ---------- 演示医生 ----------
        result = await session.execute(select(Doctor).where(Doctor.login_name == "demo_doctor"))
        doctor = result.scalar_one_or_none()
        if doctor is None:
            hashed = bcrypt.hashpw(b"123456", bcrypt.gensalt()).decode('utf-8')
            doctor = Doctor(
                name="演示医生",
                department="康复科",
                phone="13800001111",
                login_name="demo_doctor",
                password_hash=hashed
            )
            session.add(doctor)
            await session.commit()
            print("✅ 创建演示医生: demo_doctor / 123456")
        else:
            print("ℹ️ 演示医生已存在，跳过")

        # ---------- 演示患者 ----------
        result = await session.execute(select(Patient).where(Patient.hospital_patient_id == "P2026001"))
        patient = result.scalar_one_or_none()
        if patient is None:
            # 确保医生已存在
            if doctor is None:
                doctor = await session.execute(select(Doctor).where(Doctor.login_name == "demo_doctor"))
                doctor = doctor.scalar_one()
            # 生成患者密码哈希（手机号后6位 001111）
            hashed_pwd = bcrypt.hashpw(b"001111", bcrypt.gensalt()).decode('utf-8')
            patient = Patient(
                hospital_patient_id="P2026001",
                name="张明",
                phone="13900001111",
                department="康复科",
                attending_doctor_id=doctor.id,
                discharge_summary="患者因右膝关节置换术后入院，术后恢复良好，建议进行系统康复训练。",
                surgery_date=date.today(),
                password_hash=hashed_pwd   # 直接赋值
            )
            session.add(patient)
            await session.commit()
            print("✅ 创建演示患者: 张明")
        else:
            print("ℹ️ 演示患者已存在，跳过")

        # ---------- 康复模板 ----------
        result = await session.execute(select(RehabTemplate).limit(1))
        template = result.scalar_one_or_none()
        if template is None:
            template = RehabTemplate(
                disease_category="骨科",
                name="膝关节置换术后康复方案",
                phases=[
                    {"name": "早期（术后1-2周）", "duration_days": 14,
                     "tasks": [{"type": "exercise", "name": "踝泵运动", "frequency": "每天3次"},
                               {"type": "exercise", "name": "股四头肌等长收缩", "frequency": "每天2次"}]},
                    {"name": "中期（术后3-6周）", "duration_days": 28,
                     "tasks": [{"type": "exercise", "name": "直腿抬高", "frequency": "每天2次"},
                               {"type": "exercise", "name": "坐位屈膝", "frequency": "每天2次"}]},
                    {"name": "晚期（术后7周以上）", "duration_days": 999,
                     "tasks": [{"type": "exercise", "name": "靠墙静蹲", "frequency": "每天1次"},
                               {"type": "questionnaire", "name": "疼痛评分", "frequency": "每周2次"}]}
                ],
                is_active=True
            )
            session.add(template)
            await session.commit()
            print("✅ 创建康复模板: 膝关节置换术后康复方案")
        else:
            print("ℹ️ 康复模板已存在，跳过")

        # ---------- 为患者创建康复计划（如果计划不存在） ----------
        if patient is not None and template is not None:
            result = await session.execute(select(PatientRehabPlan).where(PatientRehabPlan.patient_id == patient.id))
            plan = result.scalar_one_or_none()
            if plan is None:
                plan = PatientRehabPlan(
                    patient_id=patient.id,
                    template_id=template.id,
                    start_date=date.today(),
                    current_phase=1,
                    status="active"
                )
                session.add(plan)
                await session.commit()
                print("✅ 为患者张明创建康复计划")

                # 生成演示每日任务（简化：只生成前3天）
                from datetime import timedelta
                for i in range(1, 4):
                    task_date = date.today() + timedelta(days=i-1)
                    task = DailyTask(
                        plan_id=plan.id,
                        task_date=task_date,
                        task_type="exercise",
                        task_content={"name": f"第{task_date.day}日康复训练", "duration_minutes": 15},
                        status="pending"
                    )
                    session.add(task)
                await session.commit()
                print("✅ 生成演示每日任务（前3天）")
            else:
                print("ℹ️ 康复计划已存在，跳过")
        else:
            print("⚠️ 患者或模板缺失，无法创建康复计划")

        print("🎉 数据库初始化完成")


if __name__ == "__main__":
    asyncio.run(init_db())