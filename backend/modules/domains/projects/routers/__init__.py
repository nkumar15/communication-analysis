"""Routers package"""
from modules.domains.projects.routers.projects import router as projects_router
from modules.domains.projects.routers.tasks import router as tasks_router
from modules.domains.projects.routers.comments import router as comments_router

__all__ = ['projects_router', 'tasks_router', 'comments_router']
