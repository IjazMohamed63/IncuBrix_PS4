"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-19 21:08:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. destinations table
    op.create_table(
        'destinations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=1024), nullable=False),
        sa.Column('platform_key', sa.String(length=64), nullable=False),
        sa.Column('surface', sa.String(length=64), nullable=False, server_default='default'),
        sa.Column('category', sa.String(length=64), nullable=False, server_default='general'),
        sa.Column('audience_tags', sa.JSON(), nullable=False),
        sa.Column('language', sa.String(length=16), nullable=False, server_default='en'),
        sa.Column('geo', sa.String(length=32), nullable=False, server_default='global'),
        sa.Column('est_audience', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rules_url', sa.String(length=1024), nullable=True),
        sa.Column('frequency_cap', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('self_promo_allowed', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('link_policy', sa.String(length=32), nullable=False, server_default='allowed'),
        sa.Column('disclosure_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('automation_allowed', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('connector_key', sa.String(length=64), nullable=False),
        sa.Column('relevance_score', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('relevance_reason', sa.Text(), nullable=False, server_default=''),
        sa.Column('level', sa.String(length=8), nullable=False, server_default='L0'),
        sa.Column('last_certified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_destinations_url', 'destinations', ['url'])
    op.create_index('ix_destinations_platform_key', 'destinations', ['platform_key'])
    op.create_index('ix_destinations_connector_key', 'destinations', ['connector_key'])

    # 2. connections table
    op.create_table(
        'connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('destination_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('auth_type', sa.String(length=32), nullable=False, server_default='none'),
        sa.Column('encrypted_credentials', sa.Text(), nullable=True),
        sa.Column('base_url', sa.String(length=1024), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 3. publish_jobs table
    op.create_table(
        'publish_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('idempotency_key', sa.String(length=255), unique=True, nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='queued'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('callback_url', sa.String(length=1024), nullable=True),
        sa.Column('correlation_id', sa.String(length=64), nullable=True),
        sa.Column('manifest_json', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_publish_jobs_idempotency_key', 'publish_jobs', ['idempotency_key'])
    op.create_index('ix_publish_jobs_status', 'publish_jobs', ['status'])

    # 4. publish_records table
    op.create_table(
        'publish_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('publish_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('destination_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('platform_post_id', sa.String(length=255), nullable=True),
        sa.Column('live_url', sa.String(length=1024), nullable=True),
        sa.Column('tailored_rendition', sa.JSON(), nullable=True),
        sa.Column('evidence_s3_url', sa.String(length=1024), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 5. posting_rules table
    op.create_table(
        'posting_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('destination_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rule_type', sa.String(length=64), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=False),
        sa.Column('is_enforced', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_human_confirmed', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 6. rule_decision_audits table
    op.create_table(
        'rule_decision_audits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('destination_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('decision', sa.String(length=32), nullable=False),
        sa.Column('rule_violated', sa.String(length=64), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('next_allowed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('human_action_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 7. certification_runs table
    op.create_table(
        'certification_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('destination_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('connector_key', sa.String(length=64), nullable=False),
        sa.Column('is_mock', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='running'),
        sa.Column('target_level', sa.String(length=8), nullable=False, server_default='L3'),
        sa.Column('assigned_level', sa.String(length=8), nullable=True),
        sa.Column('step_results', sa.JSON(), nullable=False),
        sa.Column('evidence_s3_url', sa.String(length=1024), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 8. deletion_watchdogs table
    op.create_table(
        'deletion_watchdogs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('certification_run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('certification_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('platform_post_id', sa.String(length=255), nullable=False),
        sa.Column('destination_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('destinations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('deletion_watchdogs')
    op.drop_table('certification_runs')
    op.drop_table('rule_decision_audits')
    op.drop_table('posting_rules')
    op.drop_table('publish_records')
    op.drop_table('publish_jobs')
    op.drop_table('connections')
    op.drop_table('destinations')
