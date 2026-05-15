"""add source, review_status, review_comment, auto_gen_prompt fields

Revision ID: 1856928ea2b0
Revises: 4778f800b55b
Create Date: 2026-05-15 10:27:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1856928ea2b0'
down_revision: Union[str, Sequence[str], None] = '4778f800b55b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # patient_rehab_plans - add source, review_status, review_comment, auto_gen_prompt
    op.add_column('patient_rehab_plans', sa.Column('source', sa.String(length=30), nullable=True, comment='来源: manual, auto_generate, template'))
    op.add_column('patient_rehab_plans', sa.Column('review_status', sa.String(length=20), nullable=True, comment='审核状态: pending, approved, rejected'))
    op.add_column('patient_rehab_plans', sa.Column('review_comment', sa.Text(), nullable=True, comment='审核意见'))
    op.add_column('patient_rehab_plans', sa.Column('auto_gen_prompt', sa.Text(), nullable=True, comment='自动生成时使用的提示词'))

    # daily_tasks - add source, review_status
    op.add_column('daily_tasks', sa.Column('source', sa.String(length=30), nullable=True, comment='来源: template, auto_generate, manual'))
    op.add_column('daily_tasks', sa.Column('review_status', sa.String(length=20), nullable=True, comment='审核状态: pending, approved, rejected'))


def downgrade() -> None:
    """Downgrade schema."""
    # daily_tasks - remove columns
    op.drop_column('daily_tasks', 'review_status')
    op.drop_column('daily_tasks', 'source')

    # patient_rehab_plans - remove columns
    op.drop_column('patient_rehab_plans', 'auto_gen_prompt')
    op.drop_column('patient_rehab_plans', 'review_comment')
    op.drop_column('patient_rehab_plans', 'review_status')
    op.drop_column('patient_rehab_plans', 'source')
