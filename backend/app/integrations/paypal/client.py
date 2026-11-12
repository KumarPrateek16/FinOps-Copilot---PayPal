import uuid
import logging
from typing import Any, Dict, Optional
import httpx
from app.config import get_settings
from app.integrations.paypal.auth import PayPalAuthManager

logger = logging.getLogger("paypal_client")
settings = get_settings()


class PayPalAPIError(Exception):
    """Exception raised when PayPal REST API returns an error."""
    def __init__(self, status_code: int, message: str, details: Optional[Dict[str, Any]] = None):
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(f"PayPal API Error {status_code}: {message}")


class PayPalBaseClient:
    """Core asynchronous HTTP client for PayPal REST APIs with automatic token injection, idempotency support, and retry on 401."""

    def __init__(
        self,
        auth_manager: Optional[PayPalAuthManager] = None,
        base_url: Optional[str] = None,
        timeout: float = 15.0,
    ):
        self.auth_manager = auth_manager or PayPalAuthManager()
        self.base_url = (base_url or settings.PAYPAL_API_BASE_URL).rstrip("/")
        self.timeout = timeout

    async def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        idempotency_key: Optional[str] = None,
        files: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Executes an authenticated HTTP request against PayPal REST API endpoints."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        auth_headers = await self.auth_manager.get_auth_headers()

        req_headers = {**auth_headers, **(headers or {})}

        # Provide idempotency key for state-changing requests if provided or required
        if idempotency_key:
            req_headers["PayPal-Request-Id"] = idempotency_key
        elif method.upper() in ["POST", "PUT", "PATCH"] and "PayPal-Request-Id" not in req_headers:
            req_headers["PayPal-Request-Id"] = str(uuid.uuid4())

        # If uploading multipart files, let HTTPX handle Content-Type
        if files is not None:
            req_headers.pop("Content-Type", None)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json_data if files is None else None,
                data=json_data if files is not None else None,
                files=files,
                headers=req_headers,
            )

            # If 401 Unauthorized, refresh token once and retry
            if response.status_code == 401:
                logger.warning("Received HTTP 401 from PayPal API. Refreshing token and retrying...")
                new_token = await self.auth_manager.get_access_token(force_refresh=True)
                req_headers["Authorization"] = f"Bearer {new_token}"
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=json_data if files is None else None,
                    data=json_data if files is not None else None,
                    files=files,
                    headers=req_headers,
                )

            if response.status_code >= 400:
                try:
                    err_json = response.json()
                    msg = err_json.get("message") or err_json.get("error_description") or response.text
                except Exception:
                    err_json = {}
                    msg = response.text
                logger.error("PayPal API Error [%s %s]: HTTP %d - %s", method, path, response.status_code, msg)
                raise PayPalAPIError(status_code=response.status_code, message=msg, details=err_json)

            if response.status_code == 204 or not response.content:
                return {}

            try:
                return response.json()
            except Exception:
                return {"text": response.text}
