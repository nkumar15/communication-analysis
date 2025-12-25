"""
Workspace tests configuration

This conftest provides model imports needed by tests in this directory.
Fixtures are inherited from parent b2c/conftest.py.
"""
# Make Workspace model available to all tests in this directory
from modules.b2c.models.workspace import Workspace, WorkspaceType
from modules.b2c.models.workspace_member import WorkspaceMember
from modules.b2c.models.workspace_invitation import WorkspaceInvitation
