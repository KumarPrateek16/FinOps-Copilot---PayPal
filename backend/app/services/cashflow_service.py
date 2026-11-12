import uuid
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.cashflow import FinancialSnapshot, FinancialAlert, MockOrder
from app.models.dispute import Dispute
from app.integrations.paypal.reporting import PayPalReportingClient

logger = logging.getLogger("cashflow_service")


class CashflowSentinelService:
    """Cashflow Sentinel monitors liquidity, pending reserves, dispute rate velocity,

    and triggers proactive risk alerts to protect merchant PayPal accounts against
    reserve holds and account limitations.
    """

    def __init__(self, reporting_client: Optional[PayPalReportingClient] = None):
        self.reporting_client = reporting_client or PayPalReportingClient()

    async def calculate_and_sync_metrics(
        self,
        db: AsyncSession,
        merchant_id: uuid.UUID,
    ) -> FinancialSnapshot:
        """Aggregates real-time PayPal balances, dispute volume, and transaction velocity

        to compute the current dispute rate and detect reserve risks.
        """
        logger.info("Computing FinOps cashflow metrics for merchant %s", merchant_id)

        # 1. Fetch Balances from PayPal Reporting
        sync_source = "SANDBOX_SIMULATION"
        available_balance = Decimal("24850.00")
        pending_balance = Decimal("1420.50")

        has_credentials = bool(
            self.reporting_client.client.auth_manager.client_id
            and self.reporting_client.client.auth_manager.client_secret
            and not self.reporting_client.client.auth_manager.client_id.startswith("your_")
            and not self.reporting_client.client.auth_manager.client_id.startswith("sandbox_client_id")
        )

        if has_credentials:
            try:
                balance_resp = await self.reporting_client.get_balances()
                balances_list = balance_resp.get("balances", [])
                for bal in balances_list:
                    currency = bal.get("currency")
                    if currency == "USD" or not currency:
                        total_info = bal.get("total_balance", {})
                        avail_info = bal.get("available_balance", {})
                        withheld_info = bal.get("withheld_balance", {})

                        if "value" in avail_info:
                            available_balance = Decimal(str(avail_info["value"]))
                        elif "value" in total_info:
                            available_balance = Decimal(str(total_info["value"]))

                        if "value" in withheld_info:
                            pending_balance = Decimal(str(withheld_info["value"]))
                        sync_source = "LIVE_PAYPAL_SANDBOX"
                        break
            except Exception as e:
                logger.warning("Could not fetch live PayPal balances (using fallback): %s", str(e))
        else:
            logger.info("No live PayPal credentials configured; using sandbox simulation ledger.")

        # 2. Query Active Disputes
        # Active statuses: not SUBMITTED, CONCEDED, or CLOSED
        active_defense_statuses = ["INGESTED", "EVIDENCE_GATHERED", "IN_HITL_REVIEW"]
        dispute_stmt = select(
            func.count(Dispute.id),
            func.coalesce(func.sum(Dispute.dispute_amount), Decimal("0.00")),
        ).where(
            Dispute.merchant_id == merchant_id,
            Dispute.defense_status.in_(active_defense_statuses),
        )
        disp_res = await db.execute(dispute_stmt)
        active_dispute_count, total_dispute_amount = disp_res.first()
        active_dispute_count = active_dispute_count or 0
        total_dispute_amount = Decimal(str(total_dispute_amount or 0.00))

        # 3. Query 30-Day Transactions / Orders
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        order_count_stmt = select(func.count(MockOrder.id)).where(
            MockOrder.merchant_id == merchant_id,
            MockOrder.created_at >= thirty_days_ago,
        )
        order_res = await db.execute(order_count_stmt)
        total_orders_30d = order_res.scalar_one_or_none() or 0

        # Baseline volume estimate: assume minimum baseline of 100 orders or orders * average ticket
        total_transactions = max(total_orders_30d, 120)
        thirty_day_volume = Decimal(str(total_transactions * 65.0))

        # 4. Compute Dispute Rate Percentage
        # Dispute Rate = (Disputes / Transactions) * 100
        if total_transactions > 0:
            dispute_rate = (Decimal(str(active_dispute_count)) / Decimal(str(total_transactions))) * Decimal("100.00")
            dispute_rate_pct = dispute_rate.quantize(Decimal("0.01"))
        else:
            dispute_rate_pct = Decimal("0.00")

        # 5. Evaluate Risk Guardrails & Generate Alerts
        await self._evaluate_risk_alerts(
            db=db,
            merchant_id=merchant_id,
            available_balance=available_balance,
            total_dispute_amount=total_dispute_amount,
            dispute_rate_pct=dispute_rate_pct,
        )

        # 6. Save Snapshot
        today = date.today()
        # Check if today's snapshot already exists
        snap_stmt = select(FinancialSnapshot).where(
            FinancialSnapshot.merchant_id == merchant_id,
            FinancialSnapshot.snapshot_date == today,
        )
        snap_res = await db.execute(snap_stmt)
        snapshot = snap_res.scalar_one_or_none()

        if snapshot:
            snapshot.available_balance = available_balance
            snapshot.pending_balance = pending_balance
            snapshot.total_dispute_amount = total_dispute_amount
            snapshot.active_dispute_count = active_dispute_count
            snapshot.dispute_rate_pct = dispute_rate_pct
            snapshot.thirty_day_volume = thirty_day_volume
        else:
            snapshot = FinancialSnapshot(
                merchant_id=merchant_id,
                snapshot_date=today,
                available_balance=available_balance,
                pending_balance=pending_balance,
                total_dispute_amount=total_dispute_amount,
                active_dispute_count=active_dispute_count,
                dispute_rate_pct=dispute_rate_pct,
                thirty_day_volume=thirty_day_volume,
            )
            db.add(snapshot)

        await db.commit()
        await db.refresh(snapshot)
        snapshot.sync_source = sync_source
        logger.info("FinOps snapshot saved: Dispute Rate %s%%, Available $%s", dispute_rate_pct, available_balance)
        return snapshot

    async def _evaluate_risk_alerts(
        self,
        db: AsyncSession,
        merchant_id: uuid.UUID,
        available_balance: Decimal,
        total_dispute_amount: Decimal,
        dispute_rate_pct: Decimal,
    ) -> None:
        """Generates proactive notifications if dispute rates or hold liabilities breach risk policies."""

        async def create_alert_if_not_exists(alert_type: str, severity: str, title: str, message: str):
            existing_stmt = select(FinancialAlert).where(
                FinancialAlert.merchant_id == merchant_id,
                FinancialAlert.alert_type == alert_type,
                FinancialAlert.is_acknowledged == False,
            )
            existing_res = await db.execute(existing_stmt)
            if not existing_res.first():
                alert = FinancialAlert(
                    merchant_id=merchant_id,
                    alert_type=alert_type,
                    severity=severity,
                    title=title,
                    message=message,
                    is_acknowledged=False,
                )
                db.add(alert)
                logger.warning("FinancialAlert created: [%s] %s", severity, title)

        # 1. PayPal Dispute Rate Thresholds
        if dispute_rate_pct >= Decimal("1.00"):
            await create_alert_if_not_exists(
                alert_type="DISPUTE_RATE_CRITICAL",
                severity="CRITICAL",
                title="Critical: PayPal Dispute Rate Breach",
                message=(
                    f"Your 30-day dispute rate is {dispute_rate_pct}%, which exceeds PayPal's 1.00% standard program threshold. "
                    "Your account is at imminent risk of rolling reserves, hold percentages, and elevated dispute fees. "
                    "Expedite resolution of open claims immediately."
                ),
            )
        elif dispute_rate_pct >= Decimal("0.65"):
            await create_alert_if_not_exists(
                alert_type="DISPUTE_RATE_WARNING",
                severity="WARNING",
                title="Warning: Elevated Dispute Velocity",
                message=(
                    f"Your current dispute rate of {dispute_rate_pct}% is nearing the 1.00% threshold. "
                    "Monitor fulfillment accuracy and review pending claims in the HITL queue."
                ),
            )

        # 2. Liquidity / Reserve Liability
        if total_dispute_amount > available_balance and available_balance > Decimal("0.00"):
            await create_alert_if_not_exists(
                alert_type="LIQUIDITY_DEFICIT",
                severity="WARNING",
                title="Liquidity Warning: High Dispute Exposure",
                message=(
                    f"Active dispute exposure (${total_dispute_amount}) exceeds current available PayPal balance (${available_balance}). "
                    "Additional claims may result in temporary account hold or overdraft."
                ),
            )


cashflow_service = CashflowSentinelService()

