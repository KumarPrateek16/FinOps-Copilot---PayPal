import uuid
import logging
from typing import List, Optional
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database.session import get_db
from app.models.cashflow import FinancialSnapshot, FinancialAlert
from app.schemas.cashflow import (
    CashflowMetricsResponse,
    FinancialSnapshotRead,
    FinancialAlertRead,
)
from app.services.cashflow_service import cashflow_service

logger = logging.getLogger("cashflow_router")
router = APIRouter(prefix="/cashflow", tags=["Cashflow Sentinel"])

DEFAULT_MERCHANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


@router.get("/metrics", response_model=CashflowMetricsResponse)
async def get_cashflow_metrics(db: AsyncSession = Depends(get_db)):
    """Retrieves current liquidity, active dispute exposure, calculated dispute rate,

    historical financial snapshots, and active risk alerts.
    """
    # Fetch most recent snapshot
    snap_stmt = (
        select(FinancialSnapshot)
        .where(FinancialSnapshot.merchant_id == DEFAULT_MERCHANT_ID)
        .order_by(desc(FinancialSnapshot.snapshot_date))
    )
    res = await db.execute(snap_stmt)
    latest_snapshot = res.scalars().first()

    # If no snapshot exists, generate one now
    if not latest_snapshot:
        latest_snapshot = await cashflow_service.calculate_and_sync_metrics(db, DEFAULT_MERCHANT_ID)

    # Fetch 30-day historical snapshots
    history_stmt = (
        select(FinancialSnapshot)
        .where(FinancialSnapshot.merchant_id == DEFAULT_MERCHANT_ID)
        .order_by(desc(FinancialSnapshot.snapshot_date))
        .limit(30)
    )
    hist_res = await db.execute(history_stmt)
    historical_snapshots = hist_res.scalars().all()

    # Fetch active unacknowledged alerts
    alerts_stmt = (
        select(FinancialAlert)
        .where(
            FinancialAlert.merchant_id == DEFAULT_MERCHANT_ID,
            FinancialAlert.is_acknowledged == False,
        )
        .order_by(desc(FinancialAlert.created_at))
    )
    alerts_res = await db.execute(alerts_stmt)
    active_alerts = alerts_res.scalars().all()

    return CashflowMetricsResponse(
        available_balance=latest_snapshot.available_balance,
        pending_balance=latest_snapshot.pending_balance,
        total_dispute_amount=latest_snapshot.total_dispute_amount,
        active_dispute_count=latest_snapshot.active_dispute_count,
        dispute_rate_pct=latest_snapshot.dispute_rate_pct,
        thirty_day_volume=latest_snapshot.thirty_day_volume,
        historical_snapshots=historical_snapshots,
        active_alerts=active_alerts,
        sync_source=getattr(latest_snapshot, "sync_source", "SANDBOX_SIMULATION"),
        last_synced_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/sync", response_model=CashflowMetricsResponse)
async def sync_cashflow_metrics(db: AsyncSession = Depends(get_db)):
    """Forces an immediate synchronization with PayPal reporting and recalculates dispute metrics."""
    latest_snapshot = await cashflow_service.calculate_and_sync_metrics(db, DEFAULT_MERCHANT_ID)

    # Historical
    hist_res = await db.execute(
        select(FinancialSnapshot)
        .where(FinancialSnapshot.merchant_id == DEFAULT_MERCHANT_ID)
        .order_by(desc(FinancialSnapshot.snapshot_date))
        .limit(30)
    )
    historical_snapshots = hist_res.scalars().all()

    # Alerts
    alerts_res = await db.execute(
        select(FinancialAlert)
        .where(
            FinancialAlert.merchant_id == DEFAULT_MERCHANT_ID,
            FinancialAlert.is_acknowledged == False,
        )
        .order_by(desc(FinancialAlert.created_at))
    )
    active_alerts = alerts_res.scalars().all()

    return CashflowMetricsResponse(
        available_balance=latest_snapshot.available_balance,
        pending_balance=latest_snapshot.pending_balance,
        total_dispute_amount=latest_snapshot.total_dispute_amount,
        active_dispute_count=latest_snapshot.active_dispute_count,
        dispute_rate_pct=latest_snapshot.dispute_rate_pct,
        thirty_day_volume=latest_snapshot.thirty_day_volume,
        historical_snapshots=historical_snapshots,
        active_alerts=active_alerts,
        sync_source=getattr(latest_snapshot, "sync_source", "SANDBOX_SIMULATION"),
        last_synced_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/alerts", response_model=List[FinancialAlertRead])
async def list_financial_alerts(
    include_acknowledged: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """Lists proactive risk alerts with severity classifications."""
    query = (
        select(FinancialAlert)
        .where(FinancialAlert.merchant_id == DEFAULT_MERCHANT_ID)
        .order_by(desc(FinancialAlert.created_at))
    )
    if not include_acknowledged:
        query = query.where(FinancialAlert.is_acknowledged == False)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/alerts/{alert_id}/acknowledge", response_model=FinancialAlertRead)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Marks a risk alert as acknowledged by the merchant."""
    stmt = select(FinancialAlert).where(
        FinancialAlert.id == alert_id,
        FinancialAlert.merchant_id == DEFAULT_MERCHANT_ID,
    )
    result = await db.execute(stmt)
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_acknowledged = True
    await db.commit()
    await db.refresh(alert)
    return alert

