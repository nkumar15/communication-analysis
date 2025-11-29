from fastapi import FastAPI
from services.domains.farming.routers import farmers

app = FastAPI(title="Farming Domain Service", openapi_url="/api/domains/farming/openapi.json", docs_url="/api/domains/farming/docs")

app.include_router(farmers.router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "farming"}
