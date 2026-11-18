"""Create quarterly business impact observations without seeding data."""
from alembic import op
import sqlalchemy as sa

revision = "004_business"
down_revision = "003_regional"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create independent, nullable source measures for each quarter."""
    op.create_table(
        "business_quarters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.Integer(), nullable=False),
        sa.Column("investment_m", sa.Numeric(18, 2)),
        sa.Column("revenue_attribution_m", sa.Numeric(18, 2)),
        sa.Column("cost_avoidance_m", sa.Numeric(18, 2)),
        sa.Column("operational_cost_savings_m", sa.Numeric(18, 2)),
        sa.Column("transformation_roi_pct", sa.Numeric(12, 2)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("year", "quarter", name="uq_business_quarter"),
        sa.CheckConstraint("year BETWEEN 1 AND 9999", name="ck_business_year"),
        sa.CheckConstraint("quarter BETWEEN 1 AND 4", name="ck_business_quarter"),
    )


def downgrade() -> None:
    """Remove business impact observations."""
    op.drop_table("business_quarters")
