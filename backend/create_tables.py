"""
创建康复记录表
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import engine, Base
from models.rehab_record import RehabRecord


async def create_tables():
    """创建所有表"""
    async with engine.begin() as conn:
        # 只创建 RehabRecord 表，不删除其他表
        await conn.run_sync(Base.metadata.create_all, tables=[RehabRecord.__table__])
    print("✅ 康复记录表创建成功!")


if __name__ == "__main__":
    asyncio.run(create_tables())