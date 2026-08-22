from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analysis, dss, etfs, recommendations
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(etfs.router, prefix="/api/etfs", tags=["ETFs"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(dss.router, prefix="/api/dss", tags=["DSS"])
app.include_router(
    recommendations.router,
    prefix="/recommendations",
    tags=["Recommendations"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
