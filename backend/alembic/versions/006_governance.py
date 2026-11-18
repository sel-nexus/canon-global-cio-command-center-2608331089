"""Create source-supplied risk and innovation tables."""
from alembic import op
import sqlalchemy as sa

revision = '006_governance'
down_revision = '005_operations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create governance tables and enforce their source integrity."""
    op.create_table('governance_risk_observations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('recorded_date', sa.Date(), nullable=False),
        sa.Column('compliance_pct', sa.Numeric(5, 2)),
        sa.Column('nist_maturity', sa.String(100)),
        sa.Column('privacy_audit_status', sa.String(255)),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('recorded_date', name='uq_governance_risk_date'),
        sa.CheckConstraint('compliance_pct IS NULL OR compliance_pct BETWEEN 0 AND 100', name='ck_governance_compliance'),
        sa.CheckConstraint('nist_maturity IS NULL OR length(trim(nist_maturity)) > 0', name='ck_governance_nist'),
        sa.CheckConstraint('privacy_audit_status IS NULL OR length(trim(privacy_audit_status)) > 0', name='ck_governance_privacy'))
    op.create_table('innovation_quarters',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer(), nullable=False),
        sa.Column('deployed_models', sa.Integer()),
        sa.Column('patent_disclosures', sa.Integer()),
        sa.Column('innovation_index', sa.Numeric(12, 2)),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('year', 'quarter', name='uq_innovation_quarter'),
        sa.CheckConstraint('year BETWEEN 1 AND 9999 AND quarter BETWEEN 1 AND 4', name='ck_innovation_period'),
        sa.CheckConstraint('deployed_models IS NULL OR deployed_models >= 0', name='ck_innovation_models'),
        sa.CheckConstraint('patent_disclosures IS NULL OR patent_disclosures >= 0', name='ck_innovation_patents'))
    op.create_table('innovation_portfolio',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(30), nullable=False),
        sa.Column('amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('unit', sa.String(40), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('year', 'quarter', 'category', name='uq_innovation_portfolio_period_category'),
        sa.CheckConstraint('year BETWEEN 1 AND 9999 AND quarter BETWEEN 1 AND 4', name='ck_portfolio_period'),
        sa.CheckConstraint("category IN ('GenAI', 'Cloud Migration', 'Edge Computing', 'Automation')", name='ck_portfolio_category'),
        sa.CheckConstraint('amount >= 0', name='ck_portfolio_amount'),
        sa.CheckConstraint('length(trim(unit)) > 0', name='ck_portfolio_unit'))


def downgrade() -> None:
    """Remove the innovation and risk tables."""
    op.drop_table('innovation_portfolio')
    op.drop_table('innovation_quarters')
    op.drop_table('governance_risk_observations')
