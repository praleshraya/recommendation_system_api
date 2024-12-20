"""Add active column to Recommendation

Revision ID: d830859ccb25
Revises: 715b9c23b0b4
Create Date: 2024-11-10 10:57:35.799122

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd830859ccb25'
down_revision: Union[str, None] = '715b9c23b0b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('recommendations', sa.Column('active', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('recommendations', 'active')
    # ### end Alembic commands ###
