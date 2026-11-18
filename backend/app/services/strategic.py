"""Read source-provided strategic observations and serialize exports."""
import csv
import datetime
import io

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.strategic import StrategicBudget, StrategicMetric
from app.schemas.strategic import Budget, Metric, StrategicDashboard


def dashboard(db: Session, today: datetime.date | None = None) -> StrategicDashboard:
    """Return latest metrics and observations in the trailing 12 calendar months."""
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    month_number = today.year * 12 + today.month - 1 - 11
    start = datetime.date(month_number // 12, month_number % 12 + 1, 1)
    observations = db.scalars(select(StrategicMetric).where(StrategicMetric.recorded_date >= start, StrategicMetric.recorded_date <= today).order_by(StrategicMetric.recorded_date.desc(), StrategicMetric.id.desc())).all()
    latest = {}
    for item in observations:
        latest.setdefault((item.category, item.metric_name), item)
    budgets = db.scalars(select(StrategicBudget).where(StrategicBudget.month >= start, StrategicBudget.month <= today).order_by(StrategicBudget.month, StrategicBudget.name)).all()
    return StrategicDashboard(
        window_start=start, window_end=today,
        metrics=[Metric.model_validate(row) for row in latest.values()],
        trends=[Metric.model_validate(row) for row in reversed(observations)],
        budgets=[Budget.model_validate(row) for row in budgets],
        insights=[Metric.model_validate(row) for row in latest.values() if row.insight],
    )


def csv_export(data: StrategicDashboard) -> str:
    """Serialize observations and comparisons, guarding spreadsheet formulas."""
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["record_type", "date", "category", "name", "value", "unit", "trend", "change_pct", "insight", "budget", "actual"])

    def safe(value: object) -> str:
        """Prevent text values from being interpreted as spreadsheet formulas."""
        text = "" if value is None else str(value)
        return "'" + text if isinstance(value, str) and (text.startswith(("\t", "\r", "\n")) or text.lstrip().startswith(("=", "+", "-", "@"))) else text

    for item in data.trends:
        writer.writerow([safe(v) for v in ("metric", item.recorded_date, item.category, item.metric_name, item.metric_value, item.unit, item.trend, item.change_pct, item.insight, None, None)])
    for item in data.budgets:
        writer.writerow([safe(v) for v in ("budget", item.month, None, item.name, None, item.unit, None, None, None, item.budget, item.actual)])
    return output.getvalue()
