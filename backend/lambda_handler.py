"""
云函数入口文件
将 FastAPI 应用适配为腾讯云函数
"""

import sys
import os
from mangum import Mangum

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入 FastAPI 应用
from main import app

# 创建 Mangum 适配器
handler = Mangum(app, lifespan="off")

# 可选：添加健康检查
def main_handler(event, context):
    """主入口函数"""
    return handler(event, context)
