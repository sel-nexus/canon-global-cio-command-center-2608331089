"""Create the identity API and configure its browser origins."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.auth import router
from app.routers.strategic import router as strategic_router
from app.routers.regional import router as regional_router
from app.routers.business import router as business_router
from app.routers.operations import router as operations_router
from app.routers.governance import router as governance_router

app = FastAPI(title="Canon CIO Command Center API", version="1.0.0", description="Identity and session API")
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
app.include_router(strategic_router)
app.include_router(regional_router)
app.include_router(business_router)
app.include_router(operations_router)
app.include_router(governance_router)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    """Report process liveness independently of database availability."""
    return {"status": "ok"}
