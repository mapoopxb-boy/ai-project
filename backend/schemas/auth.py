from pydantic import BaseModel
from typing import Optional


class DoctorLogin(BaseModel):
    """医生登录请求"""
    login_name: str
    password: str


class Token(BaseModel):
    """JWT Token 响应"""
    access_token: str
    token_type: str = "bearer"


class DoctorResponse(BaseModel):
    """医生信息响应"""
    id: int
    name: str
    department: Optional[str] = None
    phone: Optional[str] = None
    login_name: str
