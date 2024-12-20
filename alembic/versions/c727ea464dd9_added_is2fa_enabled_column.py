"""added is2FA_enabled column

Revision ID: c727ea464dd9
Revises: 52582b707c52
Create Date: 2024-11-30 15:51:45.353715

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c727ea464dd9'
down_revision: Union[str, None] = '52582b707c52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('is_2fa_enabled', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'is_2fa_enabled')
    # ### end Alembic commands ###
