"""Add initial tables

Revision ID: 923a44238cd9
Revises: None
Create Date: 2016-02-08 11:08:50.951551

"""

# revision identifiers, used by Alembic.
revision = '923a44238cd9'
down_revision = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


def upgrade():
    op.create_table(
        'ah_bot_types',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=30), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'deliverables',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('deleted', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'emails',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('deleted', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'organization_groups',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('deleted', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'report_types',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'roles',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=True),
        sa.Column('default', sa.Boolean(), nullable=True),
        sa.Column('permissions', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(
        op.f('ix_roles_default'),
        'roles',
        ['default'],
        unique=False
    )

    op.create_table(
        'tags',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table(
        'tasks_groupmeta',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('taskset_id', sa.String(length=60), nullable=True),
        sa.Column('result', sa.BLOB(), nullable=True),
        sa.Column('date_done', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('taskset_id')
    )
    op.create_table(
        'tasks_taskmeta',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('result', sa.BLOB(), nullable=True),
        sa.Column('date_done', sa.DateTime(), nullable=True),
        sa.Column('traceback', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id')
    )
    op.create_table(
        'ah_bots',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bot_type_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=30), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['bot_type_id'], ['ah_bot_types.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'deliverable_files',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('deliverable_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_sla', mysql.TINYINT(display_width=1), nullable=True),
        sa.Column('deleted', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['deliverable_id'], ['deliverables.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'organizations',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_group_id', sa.Integer(), nullable=True),
        sa.Column('is_sla', mysql.TINYINT(display_width=1), nullable=True),
        sa.Column('abbreviation', sa.String(length=255), nullable=True),
        sa.Column('old_ID', sa.String(length=5), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('mail_template', sa.String(length=50), nullable=True),
        sa.Column('mail_times', sa.Integer(), nullable=True),
        sa.Column('deleted', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['organization_group_id'],
                                ['organization_groups.id'],
                                name='fk_org_group_id'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(
        op.f('ix_organizations_abbreviation'),
        'organizations',
        ['abbreviation'],
        unique=False
    )

    op.create_table(
        'ah_runtime_configs',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alias', sa.String(length=2), nullable=True),
        sa.Column('ah_bot_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['ah_bot_id'], ['ah_bots.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'ah_startup_configs',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ah_bot_id', sa.Integer(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('module', sa.String(length=255), nullable=True),
        sa.Column('state', sa.Boolean(), nullable=True),
        sa.Column('pid', sa.Integer(), nullable=True),
        sa.Column('started', sa.DateTime(), nullable=True),
        sa.Column('stopped', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ah_bot_id'], ['ah_bots.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'asn',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('asn', sa.Integer(), nullable=True),
        sa.Column('as_name', sa.String(length=255), nullable=True),
        sa.Column('deleted', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'contactemails_organizations',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email_id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('cp_access', sa.Boolean(), nullable=True),
        sa.Column('fmb', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['email_id'], ['emails.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id', 'email_id', 'organization_id')
    )
    op.create_table(
        'contacts',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('position', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('deleted', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'emails_organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email_id', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['email_id'], ['emails.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'fqdns',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('fqdn', sa.String(length=255), nullable=True),
        sa.Column('deleted', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'ip_ranges',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('ip_range', sa.String(length=255), nullable=True),
        sa.Column('deleted', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'users',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('password', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('api_key', sa.String(length=64), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True),
        sa.Column('deleted', sa.Integer(), nullable=True),
        sa.Column('otp_secret', sa.String(length=16), nullable=True),
        sa.Column('otp_enabled', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_table(
        'ah_runtime_config_params',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ah_runtime_config_id', sa.Integer(), nullable=True),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['ah_runtime_config_id'],
                                ['ah_runtime_configs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'ah_startup_config_params',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ah_startup_config_id', sa.Integer(), nullable=True),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['ah_startup_config_id'],
                                ['ah_startup_configs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'fqdns_typosquats',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fqdn_id', sa.Integer(), nullable=True),
        sa.Column('fqdn', sa.String(length=255), nullable=True),
        sa.Column('dns_a', sa.String(length=255), nullable=True),
        sa.Column('dns_ns', sa.String(length=255), nullable=True),
        sa.Column('dns_mx', sa.String(length=255), nullable=True),
        sa.Column('raw', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['fqdn_id'], ['fqdns.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'samples',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('filename', sa.Text(), nullable=False),
        sa.Column('md5', sa.String(length=32), nullable=False),
        sa.Column('sha1', sa.String(length=40), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('sha512', sa.String(length=128), nullable=False),
        sa.Column('ctph', sa.Text(), nullable=False),
        sa.Column('infected', sa.Integer(), nullable=True),
        sa.Column('deleted', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['samples.id'], ),
        sa.ForeignKeyConstraint(['user_id'],
                                ['users.id'],
                                name='fk_sample_user_id'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'vulnerabilities',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('organization_id', sa.Integer(), nullable=True),
        sa.Column('incident_id', sa.Integer(), nullable=True),
        sa.Column('check_string', sa.Text(), nullable=True),
        sa.Column('reporter_name', sa.String(length=255), nullable=True),
        sa.Column('reporter_email', sa.String(length=255), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('request_method',
                  sa.Enum('GET', 'POST', 'PUT'),
                  nullable=True),
        sa.Column('request_data', sa.Text(), nullable=True),
        sa.Column('request_response_code', sa.Integer(), nullable=True),
        sa.Column('tested', sa.DateTime(), nullable=True),
        sa.Column('reported', sa.DateTime(), nullable=True),
        sa.Column('patched', sa.DateTime(), nullable=True),
        sa.Column('published', sa.Boolean(), nullable=True),
        sa.Column('scanable', sa.Boolean(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('deleted', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'reports',
        sa.Column('created', sa.DateTime(), nullable=True),
        sa.Column('updated', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type_id', sa.Integer(), nullable=True),
        sa.Column('sample_id', sa.Integer(), nullable=True),
        sa.Column('report', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['sample_id'], ['samples.id'], ),
        sa.ForeignKeyConstraint(['type_id'], ['report_types.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table(
        'tags_vulnerabilities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=True),
        sa.Column('vulnerability_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ),
        sa.ForeignKeyConstraint(['vulnerability_id'],
                                ['vulnerabilities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('tags_vulnerabilities')
    op.drop_table('reports')
    op.drop_table('vulnerabilities')
    op.drop_table('samples')
    op.drop_table('fqdns_typosquats')
    op.drop_table('ah_startup_config_params')
    op.drop_table('ah_runtime_config_params')
    op.drop_table('users')
    op.drop_table('ip_ranges')
    op.drop_table('fqdns')
    op.drop_table('emails_organizations')
    op.drop_table('contacts')
    op.drop_table('contactemails_organizations')
    op.drop_table('asn')
    op.drop_table('ah_startup_configs')
    op.drop_table('ah_runtime_configs')
    op.drop_index(op.f('ix_organizations_abbreviation'),
                  table_name='organizations')
    op.drop_table('organizations')
    op.drop_table('deliverable_files')
    op.drop_table('ah_bots')
    op.drop_table('tasks_taskmeta')
    op.drop_table('tasks_groupmeta')
    op.drop_table('tags')
    op.drop_index(op.f('ix_roles_default'), table_name='roles')
    op.drop_table('roles')
    op.drop_table('report_types')
    op.drop_table('organization_groups')
    op.drop_table('emails')
    op.drop_table('deliverables')
    op.drop_table('ah_bot_types')
