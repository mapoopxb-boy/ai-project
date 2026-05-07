# 康复数据模块使用指南

## 模块结构

```
backend/
├── api/
│   └── rehab_records.py      # API 路由
├── models/
│   ├── __init__.py
│   ├── patient.py           # 患者模型 (已更新)
│   └── rehab_record.py      # 康复记录模型
├── schemas/
│   └── rehab_record.py      # Pydantic Schema
├── tests/
│   └── test_rehab_records.py # 测试用例
├── database/
│   └── db.py                # 数据库配置
└── main.py                  # 主入口 (已更新)
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/rehab/records` | 提交每日康复数据 |
| GET | `/api/rehab/patients/{patient_id}/records` | 获取患者历史记录 |
| GET | `/api/rehab/patients/{patient_id}/records/latest` | 获取最新一条记录 |
| GET | `/api/rehab/records/{record_id}` | 获取单条记录详情 |
| PUT | `/api/rehab/records/{record_id}` | 更新康复记录 |
| DELETE | `/api/rehab/records/{record_id}` | 删除康复记录 |

## 运行方式

### 方式1: 直接运行 (Python)

```bash
cd /Users/gongzuo/ai-project/backend

# 激活虚拟环境
source myenv/bin/activate

# 启动服务
python main.py
```

服务启动后访问: http://127.0.0.1:8000

### 方式2: 使用 Uvicorn

```bash
cd /Users/gongzuo/ai-project/backend

# 激活虚拟环境
source myenv/bin/activate

# 启动服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 方式3: Docker (如果已配置)

```bash
cd /Users/gongzuo/ai-project/backend
docker build -t rehab-backend .
docker run -p 8000:8000 rehab-backend
```

## 运行测试

```bash
cd /Users/gongzuo/ai-project/backend

# 激活虚拟环境
source myenv/bin/activate

# 安装测试依赖 (如未安装)
pip install pytest pytest-asyncio httpx

# 运行测试
pytest tests/test_rehab_records.py -v
```

## API 使用示例

### 1. 提交康复数据

```bash
curl -X POST "http://127.0.0.1:8000/api/rehab/records" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": 1,
    "record_date": "2026-05-07",
    "pain_score": 3.5,
    "training_completion": 85.0,
    "blood_pressure_systolic": 120,
    "blood_pressure_diastolic": 80,
    "blood_sugar": 5.6,
    "notes": "今日训练完成情况良好"
  }'
```

### 2. 获取患者历史记录

```bash
curl "http://127.0.0.1:8000/api/rehab/patients/1/records?limit=10&offset=0"
```

### 3. 获取最新记录

```bash
curl "http://127.0.0.1:8000/api/rehab/patients/1/records/latest"
```

### 4. 日期范围查询

```bash
curl "http://127.0.0.1:8000/api/rehab/patients/1/records?start_date=2026-01-01&end_date=2026-05-07"
```

## 数据字段说明

| 字段 | 类型 | 范围 | 说明 |
|------|------|------|------|
| pain_score | float | 0-10 | 疼痛评分 |
| training_completion | float | 0-100 | 训练完成度 (%) |
| blood_pressure_systolic | int | 60-250 | 收缩压 (mmHg) |
| blood_pressure_diastolic | int | 40-150 | 舒张压 (mmHg) |
| blood_sugar | float | 1.0-30.0 | 血糖 (mmol/L) |

## 注意事项

1. 数据库使用 SQLite (hospital_rehab.db)
2. 患者ID必须已存在于 patients 表中
3. 同一患者同一天只能创建一条记录
4. 所有字段都有数据验证，超出范围会返回 422 错误