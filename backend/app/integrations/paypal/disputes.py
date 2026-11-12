import logging
from typing import Any, Dict, List, Optional
from app.integrations.paypal.client import PayPalBaseClient

logger = logging.getLogger("paypal_disputes")


class PayPalDisputesClient:
    """Client for the PayPal Customer Disputes API v1.

    Handles listing, retrieving, providing evidence, conceding, and adjudicating disputes.
    """

    def __init__(self, client: Optional[PayPalBaseClient] = None):
        self.client = client or PayPalBaseClient()

    async def list_disputes(
        self,
        dispute_state: Optional[str] = None,
        dispute_life_cycle_stage: Optional[str] = None,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Lists disputes associated with the merchant account.

        Docs: GET /v1/customer/disputes
        """
        params: Dict[str, Any] = {"page_size": page_size}
        if dispute_state:
            params["dispute_state"] = dispute_state
        if dispute_life_cycle_stage:
            params["dispute_life_cycle_stage"] = dispute_life_cycle_stage

        logger.info("Listing PayPal disputes with params: %s", params)
        return await self.client.request(
            method="GET",
            path="/v1/customer/disputes",
            params=params,
        )

    async def get_dispute(self, dispute_id: str) -> Dict[str, Any]:
        """Retrieves full details of a specific dispute.

        Docs: GET /v1/customer/disputes/{dispute_id}
        """
        logger.info("Fetching PayPal dispute details for %s", dispute_id)
        return await self.client.request(
            method="GET",
            path=f"/v1/customer/disputes/{dispute_id}",
        )

    async def provide_evidence(
        self,
        dispute_id: str,
        evidence_type: str,
        notes: str,
        tracking_info: Optional[List[Dict[str, str]]] = None,
        refund_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Submits defense evidence to PayPal Customer Disputes API.

        Docs: POST /v1/customer/disputes/{dispute_id}/provide-evidence
        CRITICAL: PayPal schema requires an 'evidences' array of evidence objects.
        """
        evidence_item: Dict[str, Any] = {
            "evidence_type": evidence_type,
            "notes": notes,
        }

        evidence_info: Dict[str, Any] = {}
        if tracking_info:
            evidence_info["tracking_info"] = tracking_info
        if refund_ids:
            evidence_info["refund_ids"] = refund_ids

        if evidence_info:
            evidence_item["evidence_info"] = evidence_info

        payload: Dict[str, Any] = {
            "evidences": [evidence_item],
        }

        logger.info(
            "Submitting dispute evidence to PayPal for dispute %s (type: %s, payload: %s)",
            dispute_id,
            evidence_type,
            payload,
        )
        return await self.client.request(
            method="POST",
            path=f"/v1/customer/disputes/{dispute_id}/provide-evidence",
            json_data=payload,
        )

    async def accept_claim(self, dispute_id: str, note: str = "Accepting customer claim") -> Dict[str, Any]:
        """Concedes the dispute and agrees to a full/partial refund in buyer's favor.

        Docs: POST /v1/customer/disputes/{dispute_id}/accept-claim
        """
        logger.info("Accepting claim for dispute %s with note: %s", dispute_id, note)
        payload = {"note": note}
        return await self.client.request(
            method="POST",
            path=f"/v1/customer/disputes/{dispute_id}/accept-claim",
            json_data=payload,
        )

    async def adjudicate_sandbox(
        self,
        dispute_id: str,
        adjudication_outcome: str = "SELLER_FAVOUR",
    ) -> Dict[str, Any]:
        """Sandbox-only helper: Force-settles a dispute for automated end-to-end testing.

        Docs: POST /v1/customer/disputes/{dispute_id}/adjudicate
        """
        logger.info("Adjudicating sandbox dispute %s with outcome: %s", dispute_id, adjudication_outcome)
        payload = {"adjudication_outcome": adjudication_outcome}
        return await self.client.request(
            method="POST",
            path=f"/v1/customer/disputes/{dispute_id}/adjudicate",
            json_data=payload,
        )
