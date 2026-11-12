import time
import base64
import asyncio
import logging
import httpx
from app.config import get_settings

logger = logging.getLogger("paypal_auth")
settings = get_settings()


class PayPalAuthManager:
    """Manages PayPal OAuth 2.0 Client Credentials token lifecycle with in-memory caching and automatic pre-expiry refresh."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        base_url: str | None = None,
    ):
        self.client_id = client_id or settings.PAYPAL_CLIENT_ID
        self.client_secret = client_secret or settings.PAYPAL_CLIENT_SECRET
        self.base_url = (base_url or settings.PAYPAL_API_BASE_URL).rstrip("/")
        self._access_token: str | None = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    def _get_basic_auth_header(self) -> str:
        """Encodes client_id:client_secret to Base64 for token exchange."""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    async def get_access_token(self, force_refresh: bool = False) -> str:
        """Retrieves a valid PayPal access token, fetching a new one if expired or forced."""
        # Check if current cached token is still valid (with a 2-minute buffer)
        now = time.time()
        if not force_refresh and self._access_token and now < (self._expires_at - 120):
            return self._access_token

        async with self._lock:
            # Double-check inside lock
            now = time.time()
            if not force_refresh and self._access_token and now < (self._expires_at - 120):
                return self._access_token

            token_url = f"{self.base_url}/v1/oauth2/token"
            headers = {
                "Authorization": self._get_basic_auth_header(),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }
            data = {"grant_type": "client_credentials"}

            logger.info("Requesting new PayPal OAuth2 access token from %s", token_url)
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.post(token_url, headers=headers, data=data)
                    response.raise_for_status()
                    payload = response.json()

                    self._access_token = payload["access_token"]
                    expires_in = int(payload.get("expires_in", 32400))  # Default 9 hours
                    self._expires_at = time.time() + expires_in

                    logger.info("Successfully acquired PayPal access token, valid for %d seconds", expires_in)
                    return self._access_token
                except httpx.HTTPStatusError as e:
                    logger.error("PayPal token acquisition failed: HTTP %s - %s", e.response.status_code, e.response.text)
                    raise RuntimeError(f"PayPal OAuth error: {e.response.status_code} - {e.response.text}") from e
                except Exception as e:
                    logger.error("PayPal token acquisition unexpected error: %s", str(e))
                    raise RuntimeError(f"PayPal OAuth unexpected error: {str(e)}") from e

    async def get_auth_headers(self) -> dict[str, str]:
        """Returns standard Authorization and Content-Type headers for PayPal REST API calls."""
        token = await self.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
