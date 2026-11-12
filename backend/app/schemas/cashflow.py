import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import List
from pydantic import BaseModel, ConfigDict


class FinancialSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    snapshot_date: date
    available_balance: Decimal
    pending_balance: Decimal
    total_dispute_amount: Decimal
    active_dispute_count: int
    dispute_rate_pct: Decimal
    thirty_day_volume: Decimal
    created_at: datetime


class FinancialAlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_type: str
    severity: str
    title: str
    message: str
    is_acknowledged: bool
    created_at: datetime


class CashflowMetricsResponse(BaseModel):
    available_balance: Decimal
    pending_balance: Decimal
    total_dispute_amount: Decimal
    active_dispute_count: int
    dispute_rate_pct: Decimal
    thirty_day_volume: Decimal
    historical_snapshots: List[FinancialSnapshotRead] = []
    active_alerts: List[FinancialAlertRead] = []
    sync_source: str = "SANDBOX_SIMULATION"
    last_synced_at: str | None = None

