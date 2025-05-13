from fastapi import APIRouter
from app.api.v2.endpoints import agents, knowledge, test, leads

# Create API router for v2
v2_router = APIRouter(prefix="/v2")

# Include routers for different functionalities
v2_router.include_router(agents.router, prefix="/agents", tags=["agents"])
v2_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
v2_router.include_router(test.router, prefix="/test", tags=["test"])
v2_router.include_router(leads.router, prefix="/leads", tags=["leads"])