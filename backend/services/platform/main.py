from fastapi import FastAPI
from services.platform.routers import platform

app = FastAPI(title="Platform Service", openapi_url="/api/platform/openapi.json", docs_url="/api/platform/docs")

app.include_router(platform.router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "platform"}
