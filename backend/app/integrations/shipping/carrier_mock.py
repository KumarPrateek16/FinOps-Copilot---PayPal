import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger("carrier_service")


class CarrierTrackingService:
    """Simulates real-time carrier tracking verification across FedEx, UPS, and USPS for dispute evidence."""

    def __init__(self):
        # In-memory tracking lookup registry for realistic testing
        self._tracking_registry: Dict[str, Dict[str, Any]] = {}

    def register_tracking(
        self,
        tracking_number: str,
        carrier: str,
        status: str = "DELIVERED",
        recipient_name: str = "Jane Customer",
        delivery_days_ago: int = 5,
        destination_city: str = "Austin",
        destination_state: str = "TX",
    ) -> None:
        """Registers a verified tracking event for simulation."""
        now = datetime.now(timezone.utc)
        delivery_time = now - timedelta(days=delivery_days_ago)
        shipped_time = delivery_time - timedelta(days=2)

        self._tracking_registry[tracking_number] = {
            "tracking_number": tracking_number,
            "carrier": carrier.upper(),
            "status": status.upper(),
            "delivery_timestamp": delivery_time.isoformat(),
            "signed_by": recipient_name,
            "destination": {
                "city": destination_city,
                "state": destination_state,
                "country": "US",
            },
            "events": [
                {
                    "timestamp": shipped_time.isoformat(),
                    "status": "PICKED_UP",
                    "location": "Origin Distribution Center",
                    "details": "Package received from merchant warehouse",
                },
                {
                    "timestamp": (shipped_time + timedelta(days=1)).isoformat(),
                    "status": "IN_TRANSIT",
                    "location": f"{destination_city} Regional Hub",
                    "details": "Arrived at sorting facility",
                },
                {
                    "timestamp": delivery_time.isoformat(),
                    "status": "DELIVERED",
                    "location": f"{destination_city}, {destination_state}",
                    "details": f"Delivered to porch/front door. Signed by: {recipient_name}",
                },
            ],
        }

    async def get_tracking_info(self, tracking_number: str, carrier: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Queries delivery status and checkpoint history for a given tracking number."""
        logger.info("Looking up carrier tracking info for %s (%s)", tracking_number, carrier or "AUTO")

        if tracking_number in self._tracking_registry:
            return self._tracking_registry[tracking_number]

        # Dynamic fallback for test tracking numbers
        if tracking_number.startswith("TRK-") or "DELIV" in tracking_number.upper():
            return {
                "tracking_number": tracking_number,
                "carrier": (carrier or "FEDEX").upper(),
                "status": "DELIVERED",
                "delivery_timestamp": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
                "signed_by": "Customer Signature on File",
                "destination": {"city": "Seattle", "state": "WA", "country": "US"},
                "events": [
                    {
                        "timestamp": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
                        "status": "DELIVERED",
                        "location": "Seattle, WA",
                        "details": "Left at front door. Signature confirmed.",
                    }
                ],
            }

        logger.warning("No tracking records found for %s", tracking_number)
        return None


# Global singleton instance
carrier_service = CarrierTrackingService()

