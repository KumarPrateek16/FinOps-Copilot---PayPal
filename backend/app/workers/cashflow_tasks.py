import asyncio
import logging
import uuid
from typing import List
from sqlalchemy import select

from app.celery_app import celery_app
import app.database.session as db_session
from app.models.merchant import Merchant
from app.services.cashflow_service import cashflow_service

logger = logging.getLogger("cashflow_worker")


async def _async_sync_all_merchants():
    """Iterates through all active merchants and triggers Cashflow Sentinel sync."""
    async with db_session.AsyncSessionLocal() as session:
        result = await session.execute(select(Merchant))
        merchants = result.scalars().all()
        logger.info("Cashflow Sentinel syncing metrics for %d merchants", len(merchants))

        for merchant in merchants:
            try:
                await cashflow_service.calculate_and_sync_metrics(session, merchant.id)
            except Exception as e:
                logger.error("Failed cashflow sync for merchant %s: %s", merchant.id, str(e))


@celery_app.task(name="app.workers.cashflow_tasks.sync_all_merchants_cashflow")
def sync_all_merchants_cashflow():
    """Hourly periodic beat task syncing cashflow metrics and checking dispute thresholds."""
    logger.info("Executing scheduled Cashflow Sentinel sync")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_async_sync_all_merchants())
    finally:
        loop.close()

