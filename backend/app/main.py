from fastapi import FastAPI

from app.api.routes import analysis, etfs, recommendations
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.include_router(etfs.router, prefix="/etfs", tags=["ETFs"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(
    recommendations.router,
    prefix="/recommendations",
    tags=["Recommendations"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
