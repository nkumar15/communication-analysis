"""Routers package"""
from modules.domains.b2b.task_management.routers.projects import router as projects_router
from modules.domains.b2b.task_management.routers.tasks import router as tasks_router
from modules.domains.b2b.task_management.routers.comments import router as comments_router

__all__ = ['projects_router', 'tasks_router', 'comments_router']
