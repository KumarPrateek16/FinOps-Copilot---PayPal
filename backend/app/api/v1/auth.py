import base64
import logging
from datetime import datetime, timezone
from typing import Literal
import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.config import get_settings

logger = logging.getLogger("auth_api")
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication & PayPal Connect"])


class ConnectRequest(BaseModel):
    client_id: str | None = Field(default=None, description="PayPal REST App Client ID")
    client_secret: str | None = Field(default=None, description="PayPal REST App Secret")
    environment: Literal["sandbox", "production"] = Field(default="sandbox", description="Target PayPal environment")
    merchant_name: str | None = Field(default="Acme Electronics", description="Display name for merchant store")


class ConnectResponse(BaseModel):
    success: bool
    merchant_name: str
    environment: str
    app_id: str | None
    client_id_masked: str
    scopes: list[str]
    expires_in: int
    token_type: str
    connected_at: str
    message: str


@router.post("/connect", response_model=ConnectResponse)
async def connect_paypal(request: ConnectRequest):
    """Authenticates with PayPal OAuth 2.0 API using client credentials.

    Validates credentials live against PayPal's servers, returning verified App ID and granted API scopes.
    """
    client_id = (request.client_id or settings.PAYPAL_CLIENT_ID or "").strip()
    client_secret = (request.client_secret or settings.PAYPAL_CLIENT_SECRET or "").strip()

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing PayPal Client ID or Client Secret. Please configure .env or enter credentials.",
        )

    base_url = "https://api-m.sandbox.paypal.com" if request.environment == "sandbox" else "https://api-m.paypal.com"
    token_url = f"{base_url}/v1/oauth2/token"

    # Encode credentials for HTTP Basic Auth
    credentials = f"{client_id}:{client_secret}"
    encoded = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    data = {"grant_type": "client_credentials"}

    logger.info("Attempting live PayPal OAuth2 connection against %s for client %s...", base_url, client_id[:8])

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(token_url, headers=headers, data=data)
        except Exception as e:
            logger.error("Network error reaching PayPal API: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Unable to reach PayPal API servers: {str(e)}",
            )

        if response.status_code != 200:
            try:
                err_json = response.json()
                err_desc = err_json.get("error_description") or err_json.get("error") or response.text
            except Exception:
                err_desc = response.text
            logger.warning("PayPal OAuth2 rejection (HTTP %s): %s", response.status_code, err_desc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"PayPal Authentication Failed: {err_desc}",
            )

        payload = response.json()
        app_id = payload.get("app_id")
        raw_scopes = payload.get("scope", "")
        scopes_list = [s.strip() for s in raw_scopes.split(" ") if s.strip()]
        expires_in = int(payload.get("expires_in", 32400))
        token_type = payload.get("token_type", "Bearer")

        # Mask client id for display
        masked = f"{client_id[:8]}...{client_id[-6:]}" if len(client_id) > 16 else client_id

        merchant_name = request.merchant_name or "Acme Electronics"

        logger.info("PayPal authentication successful for merchant %s (App ID: %s)", merchant_name, app_id)

        return ConnectResponse(
            success=True,
            merchant_name=merchant_name,
            environment=request.environment,
            app_id=app_id,
            client_id_masked=masked,
            scopes=scopes_list,
            expires_in=expires_in,
            token_type=token_type,
            connected_at=datetime.now(timezone.utc).isoformat(),
            message="Successfully authenticated and verified live with PayPal OAuth 2.0 API",
        )


@router.get("/status")
async def check_auth_status():
    """Checks the current default PayPal connection status and environment."""
    return {
        "environment": settings.PAYPAL_ENVIRONMENT,
        "base_url": settings.PAYPAL_API_BASE_URL,
        "configured": bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET),
        "client_id_masked": f"{settings.PAYPAL_CLIENT_ID[:8]}...{settings.PAYPAL_CLIENT_ID[-6:]}" if settings.PAYPAL_CLIENT_ID else None,
    }
