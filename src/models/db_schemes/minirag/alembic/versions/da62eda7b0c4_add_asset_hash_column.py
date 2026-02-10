"""add asset_hash column

Revision ID: da62eda7b0c4
Revises: d92e1459da51
Create Date: 2026-02-10 13:08:15.784816

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da62eda7b0c4'
down_revision: Union[str, None] = 'd92e1459da51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('assets', sa.Column('asset_hash', sa.String(length=64), nullable=True))
    op.create_index('idx_assets_hash', 'assets', ['asset_project_id', 'asset_hash'], unique=False)

def downgrade() -> None:
    op.drop_index('idx_assets_hash', table_name='assets')
    op.drop_column('assets', 'asset_hash')
