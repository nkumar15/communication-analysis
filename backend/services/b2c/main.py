"""
B2C Service Main Application (SKELETON)

This is an intentionally incomplete skeleton to demonstrate the B2C pattern.
All endpoints return 501 Not Implemented - extend as needed.
"""
from fastapi import FastAPI

app = FastAPI(
    title="B2C Service",
    description="Personal and team workspace management (SKELETON)",
    version="1.0.0"
)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "b2c", "note": "skeleton implementation"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "B2C Service API (Skeleton)",
        "note": "This is a skeleton implementation. Extend services/b2c/ to add functionality.",
        "docs": "/docs"
    }
