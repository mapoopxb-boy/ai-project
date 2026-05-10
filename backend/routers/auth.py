from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
import logging

from database.db import get_db
from models import Doctor
from schemas.auth import DoctorLogin, Token, DoctorResponse
from api.dependencies import get_current_doctor
from utils.auth import verify_password, create_access_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["认证"])


@router.post("/login", response_model=Token)
async def login(req: DoctorLogin, db: AsyncSession = Depends(get_db)):
    """
    医生登录：验证 login_name 和密码，返回 JWT access_token（有效期 8 小时）。
    """
    logger.info(f"医生登录尝试: login_name={req.login_name}")

    stmt = select(Doctor).where(Doctor.login_name == req.login_name)
    result = await db.execute(stmt)
    doctor = result.scalar_one_or_none()

    if not doctor:
        logger.warning(f"登录失败：医生不存在 - {req.login_name}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录名或密码错误",
        )

    if not verify_password(req.password, doctor.password_hash):
        logger.warning(f"登录失败：密码错误 - {req.login_name}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录名或密码错误",
        )

    access_token = create_access_token(
        data={"sub": str(doctor.id), "role": "doctor"},
        expires_delta=timedelta(hours=8),
    )

    logger.info(f"医生登录成功: id={doctor.id}, name={doctor.name}")
    return Token(access_token=access_token)


@router.get("/me", response_model=DoctorResponse)
async def get_me(
    current_doctor: Doctor = Depends(get_current_doctor),
):
    """
    获取当前登录医生信息。需在 Authorization Header 中提供 Bearer token。
    """
    return DoctorResponse(
        id=current_doctor.id,
        name=current_doctor.name,
        department=current_doctor.department,
        phone=current_doctor.phone,
        login_name=current_doctor.login_name,
    )
