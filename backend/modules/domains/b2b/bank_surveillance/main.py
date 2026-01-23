from fastapi import FastAPI
from modules.domains.b2b.bank_surveillance.routers.communications import router as communications_router
from modules.domains.b2b.bank_surveillance.routers.analysis import router as analysis_router
from modules.domains.b2b.bank_surveillance.routers.cases import router as cases_router
from modules.domains.b2b.bank_surveillance.routers.graph import router as graph_router
from modules.domains.b2b.bank_surveillance.routers.ingestion import router as ingestion_router
from modules.domains.b2b.bank_surveillance.routers.alerts import router as alerts_router
from modules.domains.b2b.bank_surveillance.routers.regulatory import router as regulatory_router
from modules.domains.b2b.bank_surveillance.routers.controls import router as controls_router

app = FastAPI(title="Bank Surveillance API")

# Include all surveillance routers
app.include_router(communications_router)
app.include_router(analysis_router)
app.include_router(cases_router)
app.include_router(graph_router)
app.include_router(ingestion_router)
app.include_router(alerts_router)
app.include_router(regulatory_router)
app.include_router(controls_router)
