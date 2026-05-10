import bcrypt
from datetime import datetime, timedelta
import os

from jose import jwt

JWT_SECRET = os.environ.get("JWT_SECRET", "your_jwt_secret_key_change_this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def hash_password(password: str) -> str:
    """使用 bcrypt 对密码进行哈希处理"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否与哈希值匹配"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )

def create_access_token(
    data: dict,
    expires_delta: timedelta = None,
    role: str = None,
):
    """
    创建 JWT access_token。

    :param data: 要编码的数据（至少包含 "sub" 字段，表示用户/患者 ID）
    :param expires_delta: 过期时间差，默认为 7 天
    :param role: 用户角色，如 "doctor" 或 "patient"，会自动写入 token payload
    """
    to_encode = data.copy()
    if role:
        to_encode["role"] = role
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt