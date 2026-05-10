from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError, ExpiredSignatureError
import os

from database.db import get_db
from models import Doctor, Patient

SECRET_KEY = os.environ.get("JWT_SECRET", "your_jwt_secret_key_change_this")
ALGORITHM = "HS256"

security = HTTPBearer()


def _decode_token_payload(token: str) -> dict:
    """
    解码 JWT token 并返回 payload。
    统一处理各类异常。
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已过期",
        )
    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 Token",
        )


async def get_current_doctor(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Doctor:
    """
    从 Authorization Header 解析 JWT，返回当前医生对象。

    校验流程：
      1. 解码 token
      2. 检查 role 是否为 "doctor"
      3. 根据 sub 中的 doctor_id 查询数据库
    """
    token = credentials.credentials
    payload = _decode_token_payload(token)

    role: str = payload.get("role")
    if role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="非医生用户，无权访问",
        )

    doctor_id: int = int(payload.get("sub"))
    stmt = select(Doctor).where(Doctor.id == doctor_id)
    result = await db.execute(stmt)
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="医生不存在",
        )
    return doctor


async def get_current_patient(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Patient:
    """
    从 Authorization Header 解析 JWT，返回当前患者对象。

    校验流程：
      1. 解码 token
      2. 检查 role 是否为 "patient"
      3. 根据 sub 中的 patient_id 查询数据库
    """
    token = credentials.credentials
    payload = _decode_token_payload(token)

    role: str = payload.get("role")
    if role != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="非患者用户，无权访问",
        )

    patient_id: int = int(payload.get("sub"))
    stmt = select(Patient).where(Patient.id == patient_id)
    result = await db.execute(stmt)
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="患者不存在",
        )
    return patient
