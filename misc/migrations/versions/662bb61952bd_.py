"""Add test_type first to vulnerabilities table

Revision ID: 662bb61952bd
Revises: 923a44238cd9
Create Date: 2017-03-19 14:07:15.055824

"""

# revision identifiers, used by Alembic.
revision = '662bb61952bd'
down_revision = '923a44238cd9'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(
        'vulnerabilities',
        sa.Column('test_type', sa.Enum('request'), nullable=True)
    )


def downgrade():
    op.drop_column('vulnerabilities', 'test_type')
