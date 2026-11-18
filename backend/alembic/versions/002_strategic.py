"""Create persisted strategic observations and budget comparisons."""
from alembic import op
import sqlalchemy as sa

revision = "002_strategic"
down_revision = "001_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the strategic tables without seeding data."""
    op.create_table("strategic_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("metric_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit", sa.String(20)), sa.Column("trend", sa.String(20)),
        sa.Column("change_pct", sa.Numeric(5, 2)), sa.Column("insight", sa.Text()),
        sa.Column("recorded_date", sa.Date(), nullable=False),
        sa.CheckConstraint("category IN ('business', 'risk', 'innovation', 'operations')", name="ck_strategic_category"),
        sa.CheckConstraint("trend IS NULL OR trend IN ('up', 'down', 'neutral')", name="ck_strategic_trend"),
        sa.UniqueConstraint("category", "metric_name", "recorded_date", name="uq_strategic_observation"))
    op.create_index("ix_strategic_metric_date", "strategic_metrics", ["recorded_date"])
    op.create_table("strategic_budgets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False), sa.Column("month", sa.Date(), nullable=False),
        sa.Column("unit", sa.String(20)), sa.Column("budget", sa.Numeric(14, 2), nullable=False),
        sa.Column("actual", sa.Numeric(14, 2), nullable=False),
        sa.CheckConstraint("EXTRACT(DAY FROM month) = 1", name="ck_strategic_budget_month"),
        sa.UniqueConstraint("name", "month", name="uq_strategic_budget_month"))
    op.create_index("ix_strategic_budget_month", "strategic_budgets", ["month"])


def downgrade() -> None:
    """Remove only the strategic tables and their indexes."""
    op.drop_index("ix_strategic_budget_month", table_name="strategic_budgets")
    op.drop_table("strategic_budgets")
    op.drop_index("ix_strategic_metric_date", table_name="strategic_metrics")
    op.drop_table("strategic_metrics")
