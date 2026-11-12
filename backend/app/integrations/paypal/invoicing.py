import logging
from typing import Any, Dict, List, Optional
from app.integrations.paypal.client import PayPalBaseClient

logger = logging.getLogger("paypal_invoicing")


class PayPalInvoicingClient:
    """Client for the PayPal Invoicing V2 REST API.

    Handles sequential invoice number generation, draft creation, dispatch, and status tracking.
    """

    def __init__(self, client: Optional[PayPalBaseClient] = None):
        self.client = client or PayPalBaseClient()

    async def generate_next_invoice_number(self) -> str:
        """Generates the next sequential invoice number from PayPal.

        Docs: POST /v2/invoicing/generate-next-invoice-number
        """
        response = await self.client.request(
            method="POST",
            path="/v2/invoicing/generate-next-invoice-number",
            json_data={},
        )
        invoice_number = response.get("invoice_number", "")
        logger.info("Generated next PayPal invoice number: %s", invoice_number)
        return invoice_number

    async def create_draft_invoice(
        self,
        invoice_number: str,
        recipient_email: str,
        recipient_name: str,
        currency_code: str,
        items: List[Dict[str, Any]],
        payment_term: str = "DUE_ON_RECEIPT",
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a draft invoice in PayPal Invoicing V2.

        Docs: POST /v2/invoicing/invoices
        """
        payload: Dict[str, Any] = {
            "detail": {
                "invoice_number": invoice_number,
                "currency_code": currency_code,
                "payment_term": {
                    "term_type": payment_term,
                },
            },
            "primary_recipients": [
                {
                    "billing_info": {
                        "name": {
                            "full_name": recipient_name,
                        },
                        "email_address": recipient_email,
                    }
                }
            ],
            "items": items,
        }

        if note:
            payload["detail"]["note"] = note

        logger.info("Creating PayPal draft invoice #%s for %s", invoice_number, recipient_email)
        return await self.client.request(
            method="POST",
            path="/v2/invoicing/invoices",
            json_data=payload,
        )

    async def send_invoice(
        self,
        invoice_id: str,
        send_to_recipient: bool = True,
        send_to_invoicer: bool = False,
    ) -> Dict[str, Any]:
        """Dispatches a draft invoice to the recipient email via PayPal.

        Docs: POST /v2/invoicing/invoices/{id}/send
        """
        payload = {
            "send_to_recipient": send_to_recipient,
            "send_to_invoicer": send_to_invoicer,
        }
        logger.info("Sending PayPal invoice %s to recipient", invoice_id)
        return await self.client.request(
            method="POST",
            path=f"/v2/invoicing/invoices/{invoice_id}/send",
            json_data=payload,
        )

    async def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Retrieves details of a specific invoice.

        Docs: GET /v2/invoicing/invoices/{id}
        """
        return await self.client.request(
            method="GET",
            path=f"/v2/invoicing/invoices/{invoice_id}",
        )

    async def list_invoices(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Lists invoices for the merchant.

        Docs: GET /v2/invoicing/invoices
        """
        params = {"page": page, "page_size": page_size, "total_required": True}
        return await self.client.request(
            method="GET",
            path="/v2/invoicing/invoices",
            params=params,
        )
