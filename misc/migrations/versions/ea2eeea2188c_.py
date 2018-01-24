"""empty message

Revision ID: ea2eeea2188c
Revises: 0d8f38142c87
Create Date: 2017-05-08 10:54:59.334788

"""

# revision identifiers, used by Alembic.
revision = 'ea2eeea2188c'
down_revision = '0d8f38142c87'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users',
                  sa.Column('origin', sa.String(length=255), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'origin')
    ### end Alembic commands ###
