"""empty message

Revision ID: 4c4c7189593e
Revises: 4b4e6d96c630
Create Date: 2017-04-04 12:37:27.512719

"""

# revision identifiers, used by Alembic.
revision = '4c4c7189593e'
down_revision = '4b4e6d96c630'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        'organization_user_roles_name_german_key',
        'organization_user_roles',
        type_='unique')
    op.drop_constraint(
        'organization_user_roles_name_key',
        'organization_user_roles',
        type_='unique')
    op.drop_column('organization_user_roles', 'deleted')
    op.drop_column('organization_user_roles', 'name_german')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('organization_user_roles',
                  sa.Column(
                      'name_german',
                      sa.VARCHAR(length=255),
                      autoincrement=False,
                      nullable=False))
    op.add_column('organization_user_roles',
                  sa.Column(
                      'deleted',
                      sa.BOOLEAN(),
                      autoincrement=False,
                      nullable=True))
    op.create_unique_constraint('organization_user_roles_name_key',
                                'organization_user_roles', ['name'])
    op.create_unique_constraint('organization_user_roles_name_german_key',
                                'organization_user_roles', ['name_german'])
    ### end Alembic commands ###
