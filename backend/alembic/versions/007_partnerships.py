"""Create partner assessments and source-reported quarterly history."""
from alembic import op
import sqlalchemy as sa

revision = '007_partnerships'
down_revision = '006_governance'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create partnership tables and enforce source integrity."""
    op.create_table('partner_performance',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('vendor_name', sa.String(100), nullable=False),
        sa.Column('sla_compliance_pct', sa.Numeric(5, 2), nullable=False),
        sa.Column('roi_multiple', sa.Numeric(4, 2), nullable=False),
        sa.Column('delivery_score', sa.Numeric(5, 2), nullable=False),
        sa.Column('annual_spend', sa.Numeric(14, 2), nullable=False),
        sa.Column('currency', sa.String(20), nullable=False),
        sa.Column('contract_status', sa.String(50), nullable=False),
        sa.Column('review_quarter', sa.String(10), nullable=False),
        sa.Column('innovation_output', sa.String(500)),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('vendor_name', name='uq_partner_vendor'),
        sa.CheckConstraint('length(trim(vendor_name)) > 0', name='ck_partner_name'),
        sa.CheckConstraint('sla_compliance_pct BETWEEN 0 AND 100', name='ck_partner_sla'),
        sa.CheckConstraint('annual_spend >= 0', name='ck_partner_spend'),
        sa.CheckConstraint('length(trim(contract_status)) > 0 AND length(trim(review_quarter)) > 0', name='ck_partner_review'),
        sa.CheckConstraint('length(trim(currency)) > 0', name='ck_partner_currency'))
    op.create_table('partner_quarters',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('partner_id', sa.Integer(), sa.ForeignKey('partner_performance.id', ondelete='CASCADE'), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer(), nullable=False),
        sa.Column('spend', sa.Numeric(14, 2)),
        sa.Column('verified_savings', sa.Numeric(14, 2)),
        sa.Column('roi_multiple', sa.Numeric(4, 2)),
        sa.Column('currency', sa.String(20), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('partner_id', 'year', 'quarter', name='uq_partner_quarter'),
        sa.CheckConstraint('year BETWEEN 1 AND 9999 AND quarter BETWEEN 1 AND 4', name='ck_partner_quarter_period'),
        sa.CheckConstraint('spend IS NULL OR spend >= 0', name='ck_partner_quarter_spend'),
        sa.CheckConstraint('length(trim(currency)) > 0', name='ck_partner_quarter_currency'))
    op.create_index('ix_partner_quarters_partner_id', 'partner_quarters', ['partner_id'])


def downgrade() -> None:
    """Remove partnership history and assessments."""
    op.drop_index('ix_partner_quarters_partner_id', table_name='partner_quarters')
    op.drop_table('partner_quarters')
    op.drop_table('partner_performance')
