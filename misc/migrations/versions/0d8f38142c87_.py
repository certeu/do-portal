"""empty message

Revision ID: 0d8f38142c87
Revises: 21367b936165
Create Date: 2017-05-04 10:59:58.940481

"""

# revision identifiers, used by Alembic.
revision = '0d8f38142c87'
down_revision = '21367b936165'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('countries',
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('updated', sa.DateTime(), nullable=True),
    sa.Column('cc', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('deleted', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('organization_memberships', sa.Column('country_id', sa.Integer(), nullable=True))
    op.add_column('organization_memberships', sa.Column('pgp_key', sa.Text(), nullable=True))
    op.add_column('organization_memberships', sa.Column('pgp_key_fingerprint', sa.String(length=255), nullable=True))
    op.add_column('organization_memberships', sa.Column('pgp_key_id', sa.String(length=255), nullable=True))
    op.add_column('organization_memberships', sa.Column('smime', sa.Text(), nullable=True))
    op.create_foreign_key(None, 'organization_memberships', 'countries', ['country_id'], ['id'])
    op.drop_column('organization_memberships', 'country')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('organization_memberships', sa.Column('country', sa.VARCHAR(length=50), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'organization_memberships', type_='foreignkey')
    op.drop_column('organization_memberships', 'smime')
    op.drop_column('organization_memberships', 'pgp_key_id')
    op.drop_column('organization_memberships', 'pgp_key_fingerprint')
    op.drop_column('organization_memberships', 'pgp_key')
    op.drop_column('organization_memberships', 'country_id')
    op.drop_table('countries')
    ### end Alembic commands ###
