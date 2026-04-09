from fastapi import FastAPI
from modules.domains.b2b.task_management.routers.projects import router as projects_router
from modules.domains.b2b.task_management.routers.tasks import router as tasks_router
from modules.domains.b2b.task_management.routers.comments import router as comments_router

app = FastAPI(title="Task Management API")

app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(comments_router)
