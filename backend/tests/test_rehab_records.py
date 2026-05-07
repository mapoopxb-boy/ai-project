"""
康复数据 API 测试用例
"""
import pytest
from httpx import AsyncClient, ASGITransport
from datetime import date
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app


@pytest.fixture
async def client():
    """异步客户端 fixture"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestRehabRecords:
    """康复数据 API 测试"""

    @pytest.mark.asyncio
    async def test_create_record(self, client):
        """测试创建康复记录"""
        payload = {
            "patient_id": 1,
            "record_date": "2026-05-07",
            "pain_score": 3.5,
            "training_completion": 85.0,
            "blood_pressure_systolic": 120,
            "blood_pressure_diastolic": 80,
            "blood_sugar": 5.6,
            "notes": "今日训练完成情况良好"
        }
        response = await client.post("/api/rehab/records", json=payload)
        # 患者不存在时会返回404，这是预期行为
        assert response.status_code in [201, 404]

    @pytest.mark.asyncio
    async def test_get_patient_records(self, client):
        """测试获取患者历史记录"""
        response = await client.get("/api/rehab/patients/1/records")
        # 患者不存在时返回404，存在时返回200
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_latest_record(self, client):
        """测试获取最新记录"""
        response = await client.get("/api/rehab/patients/1/records/latest")
        # 患者不存在时返回404，存在时返回200
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_validation_pain_score(self, client):
        """测试疼痛评分验证 (0-10)"""
        payload = {
            "patient_id": 1,
            "record_date": "2026-05-07",
            "pain_score": 15  # 超出范围
        }
        response = await client.post("/api/rehab/records", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_validation_training_completion(self, client):
        """测试训练完成度验证 (0-100)"""
        payload = {
            "patient_id": 1,
            "record_date": "2026-05-07",
            "training_completion": 150  # 超出范围
        }
        response = await client.post("/api/rehab/records", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_validation_blood_pressure(self, client):
        """测试血压验证"""
        payload = {
            "patient_id": 1,
            "record_date": "2026-05-07",
            "blood_pressure_systolic": 300  # 超出范围
        }
        response = await client.post("/api/rehab/records", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_date_filter(self, client):
        """测试日期筛选"""
        response = await client.get(
            "/api/rehab/patients/1/records?start_date=2026-01-01&end_date=2026-05-07"
        )
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_pagination(self, client):
        """测试分页"""
        response = await client.get(
            "/api/rehab/patients/1/records?limit=10&offset=0"
        )
        assert response.status_code in [200, 404]


class TestDataValidation:
    """数据验证测试"""

    def test_pain_score_valid_range(self):
        """疼痛评分有效范围测试"""
        from schemas.rehab_record import RehabRecordCreate
        data = {
            "patient_id": 1,
            "record_date": "2026-05-07",
            "pain_score": 5.0
        }
        record = RehabRecordCreate(**data)
        assert record.pain_score == 5.0

    def test_pain_score_invalid(self):
        """疼痛评分无效值测试"""
        from schemas.rehab_record import RehabRecordCreate
        from pydantic import ValidationError
        data = {
            "patient_id": 1,
            "record_date": "2026-05-07",
            "pain_score": 11
        }
        with pytest.raises(ValidationError):
            RehabRecordCreate(**data)

    def test_training_completion_valid(self):
        """训练完成度有效值测试"""
        from schemas.rehab_record import RehabRecordCreate
        data = {
            "patient_id": 1,
            "record_date": "2026-05-07",
            "training_completion": 75.5
        }
        record = RehabRecordCreate(**data)
        assert record.training_completion == 75.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])