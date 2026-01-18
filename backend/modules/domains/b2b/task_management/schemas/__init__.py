"""Schemas package"""
from modules.domains.b2b.task_management.schemas.projects import ProjectCreate, ProjectUpdate, ProjectResponse
from modules.domains.b2b.task_management.schemas.tasks import TaskCreate, TaskUpdate, TaskResponse
from modules.domains.b2b.task_management.schemas.comments import CommentCreate, CommentUpdate, CommentResponse

__all__ = [
    'ProjectCreate', 'ProjectUpdate', 'ProjectResponse',
    'TaskCreate', 'TaskUpdate', 'TaskResponse',
    'CommentCreate', 'CommentUpdate', 'CommentResponse'
]
