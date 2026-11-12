import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from app.integrations.paypal.client import PayPalBaseClient

logger = logging.getLogger("paypal_reporting")


class PayPalReportingClient:
    """Client for PayPal Reporting and Transaction Search APIs.

    Handles balance retrieval and transaction search with automatic 31-day window chunking.
    """

    def __init__(self, client: Optional[PayPalBaseClient] = None):
        self.client = client or PayPalBaseClient()

    async def get_balances(
        self,
        as_of_time: Optional[datetime] = None,
        currency_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieves available and pending balances per currency.

        Docs: GET /v1/reporting/balances
        Scope: https://uri.paypal.com/services/reporting/balances/read
        """
        params: Dict[str, Any] = {}
        if as_of_time:
            params["as_of_time"] = as_of_time.isoformat()
        if currency_code:
            params["currency_code"] = currency_code

        logger.info("Fetching PayPal balances (params: %s)", params)
        return await self.client.request(
            method="GET",
            path="/v1/reporting/balances",
            params=params,
        )

    async def search_transactions(
        self,
        start_date: datetime,
        end_date: datetime,
        transaction_status: Optional[str] = None,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """Searches transaction history over an arbitrary date range.

        PayPal enforces a hard 31-day limit per query. This method automatically
        partitions longer date ranges into sequential <=31-day chunks and aggregates the results.

        Docs: GET /v1/reporting/transactions
        Scope: https://uri.paypal.com/services/reporting/search/read
        """
        all_transactions: List[Dict[str, Any]] = []
        max_chunk = timedelta(days=30)  # Safe 30-day window

        curr_start = start_date
        while curr_start < end_date:
            curr_end = min(curr_start + max_chunk, end_date)

            params: Dict[str, Any] = {
                "start_date": curr_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end_date": curr_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fields": "all",
                "page_size": page_size,
            }
            if transaction_status:
                params["transaction_status"] = transaction_status

            logger.info("Querying PayPal transactions from %s to %s", params["start_date"], params["end_date"])
            try:
                response = await self.client.request(
                    method="GET",
                    path="/v1/reporting/transactions",
                    params=params,
                )
                details = response.get("transaction_details", [])
                all_transactions.extend(details)
            except Exception as e:
                logger.error("Error fetching transactions for window %s-%s: %s", curr_start, curr_end, str(e))
                break

            curr_start = curr_end + timedelta(seconds=1)

        logger.info("Total transactions retrieved across all chunks: %d", len(all_transactions))
        return all_transactions

