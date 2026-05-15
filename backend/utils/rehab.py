"""
康复相关工具函数
"""

import json
import logging
from datetime import date, timedelta

from sqlalchemy import select

from database.db import AsyncSessionLocal
from models import DailyTask, PatientRehabPlan, RehabTemplate

logger = logging.getLogger(__name__)


async def generate_tasks_for_plan(plan_id: int) -> int:
    """
    根据康复计划的 phases 和 start_date 生成 DailyTask 记录。

    流程：
    1. 加载计划和关联的 RehabTemplate（含 phases）
    2. 如果计划已有任务，先删除旧任务
    3. 遍历 phases 展开所有任务日期
    4. 写入 DailyTask 表
    5. 设置 source='auto_generate', review_status='approved'

    Args:
        plan_id: PatientRehabPlan 的 ID

    Returns:
        生成的任务数量

    Raises:
        ValueError: 计划不存在、模板不存在或 phases 为空
    """
    async with AsyncSessionLocal() as db:
        # ── 1. 加载计划 ──
        plan_stmt = select(PatientRehabPlan).where(PatientRehabPlan.id == plan_id)
        plan_result = await db.execute(plan_stmt)
        plan = plan_result.scalar_one_or_none()

        if not plan:
            raise ValueError(f"康复计划不存在: plan_id={plan_id}")

        if not plan.template_id:
            raise ValueError(f"康复计划没有关联模板: plan_id={plan_id}")

        # ── 2. 加载模板获取 phases ──
        tpl_stmt = select(RehabTemplate).where(RehabTemplate.id == plan.template_id)
        tpl_result = await db.execute(tpl_stmt)
        template = tpl_result.scalar_one_or_none()

        if not template:
            raise ValueError(f"康复模板不存在: template_id={plan.template_id}")

        phases = template.phases
        if not phases or not isinstance(phases, list) or len(phases) == 0:
            raise ValueError(f"康复模板 phases 为空: template_id={plan.template_id}")

        start_date = plan.start_date
        if not start_date:
            start_date = date.today()

        # ── 3. 删除已有任务（避免重复生成） ──
        delete_stmt = select(DailyTask).where(DailyTask.plan_id == plan_id)
        delete_result = await db.execute(delete_stmt)
        existing_tasks = delete_result.scalars().all()
        for task in existing_tasks:
            await db.delete(task)

        # ── 4. 生成每日任务 ──
        tasks_created = 0
        cumulative_day_offset = 0

        for phase_idx, phase in enumerate(phases):
            if not isinstance(phase, dict):
                continue

            duration_days = phase.get("duration_days", 7)
            phase_tasks = phase.get("tasks", [])

            if not isinstance(phase_tasks, list):
                continue

            for day_offset in range(duration_days):
                task_date = start_date + timedelta(days=cumulative_day_offset + day_offset)

                for task_def in phase_tasks:
                    if not isinstance(task_def, dict):
                        continue

                    task_type = task_def.get("type", "exercise")
                    task_name = task_def.get("name", "")
                    frequency = task_def.get("frequency", "每天")

                    # 根据频率判断是否需要在这一天生成任务
                    if not _should_create_task(frequency, day_offset):
                        continue

                    # 构建 task_content
                    task_content = {
                        "name": task_name,
                        "frequency": frequency,
                        "phase_index": phase_idx,
                        "phase_name": phase.get("name", f"第{phase_idx+1}阶段"),
                    }
                    # 复制额外的自定义字段
                    for k, v in task_def.items():
                        if k not in ("type", "name", "frequency"):
                            task_content[k] = v

                    new_task = DailyTask(
                        plan_id=plan_id,
                        task_date=task_date,
                        task_type=task_type,
                        task_content=task_content,
                        status="pending",
                        source="auto_generate",
                        review_status="approved",
                    )
                    db.add(new_task)
                    tasks_created += 1

            cumulative_day_offset += duration_days

        await db.commit()
        logger.info(
            f"✅ 为计划 {plan_id} 生成了 {tasks_created} 个每日任务 "
            f"(phases={len(phases)}, start_date={start_date})"
        )

        return tasks_created


def _should_create_task(frequency: str, day_offset: int) -> bool:
    """
    根据频率判断指定偏移的天数是否需要生成任务。
    """
    if not frequency:
        return True

    freq = frequency.strip()

    if freq == "每天" or freq == "每日":
        return True

    if freq.startswith("每") and freq.endswith("天"):
        try:
            interval = int(freq[1:-1])
            return (day_offset % interval) == 0
        except (ValueError, IndexError):
            return True

    if freq.startswith("每") and "天" in freq and "次" in freq:
        try:
            interval = int(freq[1])
            return (day_offset % interval) == 0
        except (ValueError, IndexError):
            return True

    if freq.startswith("每") and freq.endswith("次"):
        try:
            count = int(freq[2])
            week = day_offset % 7
            return week < count
        except (ValueError, IndexError):
            return True

    return True
