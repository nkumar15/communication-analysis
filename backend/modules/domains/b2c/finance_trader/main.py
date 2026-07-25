from fastapi import FastAPI
from modules.domains.b2c.finance_trader.routers.rag import router as rag_router

app = FastAPI(title="Finance Trader API")

app.include_router(rag_router)
