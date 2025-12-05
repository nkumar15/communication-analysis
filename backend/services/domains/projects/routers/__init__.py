"""Routers package"""
from services.domains.projects.routers.projects import router as projects_router
from services.domains.projects.routers.tasks import router as tasks_router
from services.domains.projects.routers.comments import router as comments_router

__all__ = ['projects_router', 'tasks_router', 'comments_router']
