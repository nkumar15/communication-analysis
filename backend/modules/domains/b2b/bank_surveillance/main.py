from fastapi import FastAPI
from modules.domains.b2b.bank_surveillance.routers.communications import router as communications_router
from modules.domains.b2b.bank_surveillance.routers.cases import router as cases_router
from modules.domains.b2b.bank_surveillance.routers.graph import router as graph_router
from modules.domains.b2b.bank_surveillance.routers.ingestion import router as ingestion_router
from modules.domains.b2b.bank_surveillance.routers.alerts import router as alerts_router
from modules.domains.b2b.bank_surveillance.routers.regulatory import router as regulatory_router
from modules.domains.b2b.bank_surveillance.routers.controls import router as controls_router
from modules.domains.b2b.bank_surveillance.routers.risk_events import router as risk_events_router
from modules.domains.b2b.bank_surveillance.routers.incidents import router as incidents_router
from infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(title="Bank Surveillance API")

# Include all surveillance routers
app.include_router(communications_router)
app.include_router(cases_router)
app.include_router(graph_router)
app.include_router(ingestion_router)
app.include_router(alerts_router)
app.include_router(regulatory_router)
app.include_router(controls_router)
app.include_router(risk_events_router)
app.include_router(incidents_router)

# analysis_router pulls in the langchain/langgraph agent chain
# (agents/intent_agent.py etc.), which currently has an unpinned
# langgraph-prebuilt/langgraph-core version mismatch upstream
# (ImportError: ExecutionInfo/ServerInfo missing from langgraph.runtime).
# Isolated here so a broken ML dependency doesn't take down the rest of
# the API — fix the pin in requirements-ai-api.txt, then this loads normally.
try:
    from modules.domains.b2b.bank_surveillance.routers.analysis import router as analysis_router
    app.include_router(analysis_router)
except ImportError as e:
    logger.warning("analysis_router_unavailable", reason=str(e))
