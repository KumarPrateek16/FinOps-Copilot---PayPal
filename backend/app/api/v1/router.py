from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.disputes import router as disputes_router
from app.api.v1.invoices import router as invoices_router
from app.api.v1.cashflow import router as cashflow_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(webhooks_router)
api_router.include_router(disputes_router)
api_router.include_router(invoices_router)
api_router.include_router(cashflow_router)
