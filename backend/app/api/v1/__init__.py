from fastapi import APIRouter

from app.api.v1 import analysis, favorites, health, ingest, policies, subscriptions

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(policies.router, tags=["policies"])
api_router.include_router(analysis.router, tags=["analysis"])
api_router.include_router(favorites.router, tags=["favorites"])
api_router.include_router(subscriptions.router, tags=["subscriptions"])
api_router.include_router(ingest.router, tags=["ingest"])
