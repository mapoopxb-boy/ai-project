import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from database.db import DATABASE_URL
from models import Doctor, Patient
import bcrypt

async def seed():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        # 检查是否已有医生
        result = await conn.execute(select(Doctor).where(Doctor.login_name == "demo_doctor"))
        doctor = result.scalar_one_or_none()
        if not doctor:
            hashed = bcrypt.hashpw(b"123456", bcrypt.gensalt())
            doctor = Doctor(
                name="演示医生",
                department="内科",
                login_name="demo_doctor",
                password_hash=hashed.decode('utf-8')
            )
            await conn.execute(insert(Doctor).values(doctor))
            print("创建演示医生成功")
        else:
            print("演示医生已存在")

        # 可选创建测试患者
        result = await conn.execute(select(Patient).where(Patient.phone == "13800000000"))
        patient = result.scalar_one_or_none()
        if not patient:
            patient = Patient(
                hospital_patient_id="P001",
                name="测试患者",
                phone="13800000000",
                department="内科",
                attending_doctor_id=1,
                discharge_summary="高血压出院"
            )
            await conn.execute(insert(Patient).values(patient))
            print("创建测试患者成功")

    await engine.dispose()

if __name__ == "__main__":
    from sqlalchemy import insert
    asyncio.run(seed())
