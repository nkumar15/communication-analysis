from fastapi import FastAPI
from services.b2b.routers import auth, users, invitations, roles, activation

app = FastAPI(title="B2B Service", openapi_url="/api/b2b/openapi.json", docs_url="/api/b2b/docs")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(invitations.router)
app.include_router(roles.router)
app.include_router(activation.router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "b2b"}
