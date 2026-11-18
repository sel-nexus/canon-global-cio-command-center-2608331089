"""Create source-provided regional performance records."""
from alembic import op
import sqlalchemy as sa

revision = "003_regional"
down_revision = "002_strategic"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the regional table without seeding metrics."""
    op.create_table(
        "regional_performance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("region", sa.String(50), nullable=False),
        sa.Column("health_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("availability_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("security_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("transformation_index", sa.Numeric(5, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("region", name="uq_regional_performance_region"),
        sa.CheckConstraint("status IN ('Excellent', 'Good', 'Warning', 'Critical')", name="ck_regional_status"),
        sa.CheckConstraint("availability_pct BETWEEN 0 AND 100", name="ck_regional_availability"),
    )


def downgrade() -> None:
    """Remove the regional table."""
    op.drop_table("regional_performance")
