from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from database.db import get_db
from models import Doctor, Patient
from utils.auth import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["认证"])

class LoginRequest(BaseModel):
    username: str   # 对于患者：手机号；对于医生：登录名
    password: str
    role: str       # 'patient' 或 'doctor'

class LoginResponse(BaseModel):
    code: int
    token: str
    role: str
    user_id: int
    name: str

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    if req.role == "patient":
        # 患者使用手机号登录（假设 phone 字段唯一）
        stmt = select(Patient).where(Patient.phone == req.username)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="患者不存在")
        # 目前患者表没有密码字段，这里先模拟免密登录（开发阶段），实际应加入 password_hash
        # 为简化演示，我们假设患者登录无需密码（可后续完善）
        # 仅当手机号匹配即成功
        token = create_access_token(data={"sub": str(user.id), "role": "patient"})
        return LoginResponse(code=200, token=token, role="patient", user_id=user.id, name=user.name)
    
    elif req.role == "doctor":
        stmt = select(Doctor).where(Doctor.login_name == req.username)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="医生不存在")
        if not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="密码错误")
        token = create_access_token(data={"sub": str(user.id), "role": "doctor"})
        return LoginResponse(code=200, token=token, role="doctor", user_id=user.id, name=user.name)
    
    else:
        raise HTTPException(status_code=400, detail="无效角色")