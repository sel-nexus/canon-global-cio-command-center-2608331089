"""Create incident and source-supplied operations history tables."""
from alembic import op
import sqlalchemy as sa

revision = '005_operations'
down_revision = '004_business'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create operations tables with source integrity constraints."""
    op.create_table('operations_incidents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('incident_number', sa.String(50), nullable=False, unique=True),
        sa.Column('severity', sa.String(10), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('mttr_minutes', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint('length(trim(incident_number)) > 0 AND length(trim(title)) > 0', name='ck_incident_nonempty'),
        sa.CheckConstraint("severity IN ('P1', 'P2', 'P3', 'P4')", name='ck_incident_severity'),
        sa.CheckConstraint("status IN ('Open', 'Investigating', 'Resolved')", name='ck_incident_status'),
        sa.CheckConstraint('mttr_minutes IS NULL OR mttr_minutes >= 0', name='ck_incident_mttr'),
        sa.CheckConstraint('resolved_at IS NULL OR resolved_at >= created_at', name='ck_incident_resolution_time'),
        sa.CheckConstraint("(status = 'Resolved' AND resolved_at IS NOT NULL) OR (status <> 'Resolved' AND resolved_at IS NULL)", name='ck_incident_resolution_status'))
    op.create_index('ix_operations_incidents_created_at', 'operations_incidents', ['created_at'])
    op.create_table('operations_history',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('recorded_date', sa.Date(), nullable=False),
        sa.Column('mttr_minutes', sa.Numeric(12, 2)),
        sa.Column('sla_compliance_pct', sa.Numeric(5, 2)),
        sa.Column('uptime_pct', sa.Numeric(5, 2)),
        sa.Column('incident_volume', sa.Integer()),
        sa.Column('resolution_count', sa.Integer()),
        sa.Column('p1_volume', sa.Integer()),
        sa.Column('p2_volume', sa.Integer()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('recorded_date', name='uq_operations_history_date'),
        sa.CheckConstraint('mttr_minutes IS NULL OR mttr_minutes >= 0', name='ck_operations_mttr'),
        sa.CheckConstraint('sla_compliance_pct IS NULL OR sla_compliance_pct BETWEEN 0 AND 100', name='ck_operations_sla'),
        sa.CheckConstraint('uptime_pct IS NULL OR uptime_pct BETWEEN 0 AND 100', name='ck_operations_uptime'),
        sa.CheckConstraint('incident_volume IS NULL OR incident_volume >= 0', name='ck_operations_volume'),
        sa.CheckConstraint('resolution_count IS NULL OR resolution_count >= 0', name='ck_operations_resolutions'),
        sa.CheckConstraint('p1_volume IS NULL OR p1_volume >= 0', name='ck_operations_p1'),
        sa.CheckConstraint('p2_volume IS NULL OR p2_volume >= 0', name='ck_operations_p2'))


def downgrade() -> None:
    """Remove operations tables."""
    op.drop_table('operations_history')
    op.drop_index('ix_operations_incidents_created_at', table_name='operations_incidents')
    op.drop_table('operations_incidents')
