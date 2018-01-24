"""empty message

Revision ID: 3247be988b6c
Revises: d55a3395296c
Create Date: 2017-04-03 11:27:30.189351

"""

# revision identifiers, used by Alembic.
revision = '3247be988b6c'
down_revision = 'd55a3395296c'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('organization_user_roles',
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.Column('updated', sa.DateTime(), nullable=True),
                    sa.Column('name', sa.String(length=255), nullable=False),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.PrimaryKeyConstraint('id'))
    op.create_table('organizations_users',
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.Column('updated', sa.DateTime(), nullable=True),
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=True),
                    sa.Column('organization_id', sa.Integer(), nullable=True),
                    sa.Column('org_user_role_id', sa.Integer(), nullable=True),
                    sa.Column('street', sa.String(length=255), nullable=True),
                    sa.Column('zip', sa.String(length=25), nullable=True),
                    sa.Column('country', sa.String(length=50), nullable=True),
                    sa.Column('comment', sa.String(length=255), nullable=True),
                    sa.Column('email', sa.String(length=255), nullable=True),
                    sa.Column('phone', sa.String(length=255), nullable=True),
                    sa.Column('deleted', sa.Boolean(), nullable=True),
                    sa.Column('ts_deleted', sa.DateTime(), nullable=True),
                    sa.ForeignKeyConstraint(
                        ['org_user_role_id'],
                        ['organization_user_roles.id'],
                    ),
                    sa.ForeignKeyConstraint(
                        ['organization_id'],
                        ['organizations.id'],
                    ), sa.ForeignKeyConstraint(
                        ['user_id'],
                        ['users.id'],
                    ), sa.PrimaryKeyConstraint('id'))
    op.drop_table('addresses')
    op.add_column('organizations',
                  sa.Column('parent_org_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'organizations', 'organizations',
                          ['parent_org_id'], ['id'])
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'organizations', type_='foreignkey')
    op.drop_column('organizations', 'parent_org_id')
    op.create_table('addresses',
                    sa.Column(
                        'created',
                        postgresql.TIMESTAMP(),
                        autoincrement=False,
                        nullable=True),
                    sa.Column(
                        'updated',
                        postgresql.TIMESTAMP(),
                        autoincrement=False,
                        nullable=True),
                    sa.Column('id', sa.INTEGER(), nullable=False),
                    sa.Column(
                        'user_id',
                        sa.INTEGER(),
                        autoincrement=False,
                        nullable=True),
                    sa.Column(
                        'postal_address',
                        sa.VARCHAR(length=255),
                        autoincrement=False,
                        nullable=True),
                    sa.Column(
                        'zip',
                        sa.VARCHAR(length=25),
                        autoincrement=False,
                        nullable=True),
                    sa.Column(
                        'country',
                        sa.VARCHAR(length=50),
                        autoincrement=False,
                        nullable=True),
                    sa.Column(
                        'comment',
                        sa.VARCHAR(length=250),
                        autoincrement=False,
                        nullable=True),
                    sa.Column(
                        'deleted',
                        sa.INTEGER(),
                        autoincrement=False,
                        nullable=True),
                    sa.ForeignKeyConstraint(
                        ['user_id'], ['users.id'],
                        name='addresses_user_id_fkey'),
                    sa.PrimaryKeyConstraint('id', name='addresses_pkey'))
    op.drop_table('organizations_users')
    op.drop_table('organization_user_roles')
    ### end Alembic commands ###
