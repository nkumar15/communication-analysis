"""
Dashboard Service

Handles dashboard statistics aggregation and role-based visibility.
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.logging import get_logger
from modules.b2b.models import UserModel, Team, TeamMember
from modules.b2b.models.team_role_definition import TeamRoleDefinition

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
            from modules.b2b.models import InvitationModel
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
                "team_role": member.team_role or (role_def.name if role_def else None),
                "team_role_display": role_def.display_name if role_def else None,
                "member_count": member_count
            })
        
        return my_teams, team_ids
    
    def get_quick_actions(self, role: str) -> List[str]:
        """
        Get quick actions based on user role

        Returns list of action keys for frontend to render
        """
        if role == 'owner':
            return ['invite_user', 'create_team', 'view_audit_logs']
        elif role == 'admin':
            return ['invite_user', 'create_team', 'view_audit_logs']
        else:  # member, viewer
            return ['view_teams']
    
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

        # Get quick actions
        quick_actions = self.get_quick_actions(role)

        return {
            "role": role,
            "scope": scope,
            **org_stats,
            "my_teams": my_teams,
            "quick_actions": quick_actions
        }


# Global dashboard service instance
dashboard_service = DashboardService()
