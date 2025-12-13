"""
Dashboard Service

Handles dashboard statistics aggregation and role-based visibility.
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from services.b2b.models import UserModel, Team, TeamMember
from services.b2b.models.team_role_definition import TeamRoleDefinition

logger = get_logger(__name__)


class DashboardService:
    """Service for dashboard statistics"""
    
    async def get_org_stats(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        is_admin_scope: bool
    ) -> dict:
        """
        Get organization-wide statistics
        
        Returns dict with total_users, active_users, total_teams, pending_invitations
        """
        # Total users
        total_users_result = await db.execute(
            select(func.count(UserModel.id)).where(UserModel.tenant_id == tenant_id)
        )
        total_users = total_users_result.scalar() or 0
        
        # Active users
        active_users_result = await db.execute(
            select(func.count(UserModel.id)).where(
                UserModel.tenant_id == tenant_id,
                UserModel.is_active == True
            )
        )
        active_users = active_users_result.scalar() or 0
        
        # Total teams
        total_teams_result = await db.execute(
            select(func.count(Team.id)).where(Team.tenant_id == tenant_id)
        )
        total_teams = total_teams_result.scalar() or 0
        
        # Pending invitations (admin/owner see all, others see 0)
        pending_invitations = 0
        if is_admin_scope:
            from services.b2b.models import InvitationModel
            pending_result = await db.execute(
                select(func.count(InvitationModel.id)).where(
                    InvitationModel.tenant_id == tenant_id,
                    InvitationModel.accepted_at.is_(None)
                )
            )
            pending_invitations = pending_result.scalar() or 0
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_teams": total_teams,
            "pending_invitations": pending_invitations
        }
    
    async def get_user_teams(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        user_id: UUID
    ) -> tuple[List[dict], List[UUID]]:
        """
        Get user's teams with member counts
        
        Returns tuple of (team_summaries, team_ids)
        """
        teams_result = await db.execute(
            select(Team, TeamMember, TeamRoleDefinition)
            .join(TeamMember, Team.id == TeamMember.team_id)
            .outerjoin(TeamRoleDefinition, TeamMember.team_role_id == TeamRoleDefinition.id)
            .where(
                Team.tenant_id == tenant_id,
                TeamMember.user_id == user_id
            )
        )
        
        my_teams = []
        team_ids = []
        
        for team, member, role_def in teams_result:
            team_ids.append(team.id)
            
            # Get member count for each team
            member_count_result = await db.execute(
                select(func.count(TeamMember.id)).where(TeamMember.team_id == team.id)
            )
            member_count = member_count_result.scalar() or 0
            
            my_teams.append({
                "id": str(team.id),
                "name": team.name,
                "team_role": member.team_role or (role_def.name if role_def else 'team_contributor'),
                "team_role_display": role_def.display_name if role_def else None,
                "member_count": member_count
            })
        
        return my_teams, team_ids
    
    async def get_domain_stats(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        is_admin_scope: bool,
        team_ids: List[UUID]
    ) -> dict:
        """
        Get domain statistics (projects, tasks)
        
        Returns dict with my_projects_count, my_tasks_count, overdue_tasks_count
        Scoped based on role: admin sees all, member/viewer sees team-scoped
        """
        my_projects_count = 0
        my_tasks_count = 0
        overdue_tasks_count = 0
        
        try:
            from services.domains.projects.models import Project, Task
            from datetime import datetime, timezone
            
            if is_admin_scope:
                # Admin/owner see all org projects
                projects_result = await db.execute(
                    select(func.count(Project.id)).where(Project.tenant_id == tenant_id)
                )
                tasks_result = await db.execute(
                    select(func.count(Task.id)).where(Task.tenant_id == tenant_id)
                )
                overdue_result = await db.execute(
                    select(func.count(Task.id)).where(
                        Task.tenant_id == tenant_id,
                        Task.due_date < datetime.now(timezone.utc),
                        Task.status != 'done'
                    )
                )
            else:
                # Member/viewer see only their teams' projects
                if team_ids:
                    projects_result = await db.execute(
                        select(func.count(Project.id)).where(
                            Project.tenant_id == tenant_id,
                            Project.team_id.in_(team_ids)
                        )
                    )
                    # Tasks need to go through Project to filter by team
                    tasks_result = await db.execute(
                        select(func.count(Task.id))
                        .join(Project, Task.project_id == Project.id)
                        .where(
                            Task.tenant_id == tenant_id,
                            Project.team_id.in_(team_ids)
                        )
                    )
                    overdue_result = await db.execute(
                        select(func.count(Task.id))
                        .join(Project, Task.project_id == Project.id)
                        .where(
                            Task.tenant_id == tenant_id,
                            Project.team_id.in_(team_ids),
                            Task.due_date < datetime.now(timezone.utc),
                            Task.status != 'done'
                        )
                    )
                else:
                    projects_result = tasks_result = overdue_result = None
            
            if projects_result:
                my_projects_count = projects_result.scalar() or 0
            if tasks_result:
                my_tasks_count = tasks_result.scalar() or 0
            if overdue_result:
                overdue_tasks_count = overdue_result.scalar() or 0
                
        except ImportError:
            # Domain service not available
            logger.debug("domain_stats_unavailable", reason="projects module not imported")
            pass
        
        return {
            "my_projects_count": my_projects_count,
            "my_tasks_count": my_tasks_count,
            "overdue_tasks_count": overdue_tasks_count
        }
    
    def get_quick_actions(self, role: str) -> List[str]:
        """
        Get quick actions based on user role
        
        Returns list of action keys for frontend to render
        """
        if role == 'owner':
            return ['invite_user', 'create_team', 'manage_billing', 'view_audit_logs']
        elif role == 'admin':
            return ['invite_user', 'create_team', 'view_audit_logs']
        elif role == 'member':
            return ['view_projects', 'create_task', 'view_teams']
        else:  # viewer
            return ['view_projects', 'view_teams']
    
    async def get_dashboard_stats(
        self,
        db: AsyncSession,
        user_id: UUID,
        tenant_id: UUID,
        role: str
    ) -> dict:
        """
        Get comprehensive dashboard statistics for user
        
        Combines org stats, user teams, domain stats, and quick actions
        Returns dict ready for DashboardStats schema
        """
        # Determine scope
        is_admin_scope = role in ['owner', 'admin']
        scope = 'org' if is_admin_scope else 'team'
        
        # Get org-wide stats
        org_stats = await self.get_org_stats(db, tenant_id, is_admin_scope)
        
        # Get user's teams
        my_teams, team_ids = await self.get_user_teams(db, tenant_id, user_id)
        
        # Get domain stats
        domain_stats = await self.get_domain_stats(db, tenant_id, is_admin_scope, team_ids)
        
        # Get quick actions
        quick_actions = self.get_quick_actions(role)
        
        return {
            "role": role,
            "scope": scope,
            **org_stats,
            "my_teams": my_teams,
            **domain_stats,
            "quick_actions": quick_actions
        }


# Global dashboard service instance
dashboard_service = DashboardService()
