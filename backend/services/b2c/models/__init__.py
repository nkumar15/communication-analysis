"""
B2C Models Package

Models for B2C workspace functionality (personal and team workspaces).
"""
from .workspace import Workspace, WorkspaceType
from .user import B2CUser
from .workspace_member import WorkspaceMember

__all__ = ['Workspace', 'WorkspaceType', 'B2CUser', 'WorkspaceMember']
