"""
Fixtures for B2C workspace and invitation tests
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from tests.conftest import (
    create_b2c_user,
    create_b2c_workspace,
    create_b2c_mock_token,
    encode_mock_jwt
)
from services.b2c.models.workspace import Workspace, WorkspaceType
from services.b2c.models.workspace_member import WorkspaceMember
from services.b2c.models.workspace_invitation import WorkspaceInvitation
from core.rls import rls_service


@pytest_asyncio.fixture
async def workspace_owner(db_session):
    """Create a B2C user with personal workspace (free tier)"""
    email = f"owner-{uuid4().hex[:8]}@example.com"
    firebase_uid = f"firebase-{uuid4().hex[:12]}"
    
    user = await create_b2c_user(db_session, email, firebase_uid, "Workspace Owner")
    workspace = await create_b2c_workspace(db_session, user.id, "Owner's Personal Workspace", 'personal')
    user.default_workspace_id = workspace.id
    
    await db_session.flush()
    
    # Create auth token
    mock_token_data = create_b2c_mock_token(firebase_uid, email)
    auth_token = encode_mock_jwt(mock_token_data)
    
    return {
        "user": user,
        "workspace": workspace,
        "auth_token": auth_token,
        "firebase_uid": firebase_uid,
        "email": email,
        "mock_token_data": mock_token_data
    }


@pytest_asyncio.fixture
async def premium_workspace_owner(db_session):
    """Create a B2C user with Premium subscription for team workspace creation"""
    email = f"premium-owner-{uuid4().hex[:8]}@example.com"
    firebase_uid = f"firebase-{uuid4().hex[:12]}"
    
    user = await create_b2c_user(db_session, email, firebase_uid, "Premium Owner")
    # Create personal workspace with premium tier
    workspace = await create_b2c_workspace(
        db_session, user.id, "Premium Personal Workspace", 'personal', subscription_tier='premium'
    )
    user.default_workspace_id = workspace.id

    
    # Set Admin context to bypass RLS for seeding
    await rls_service.set_platform_admin_context(db_session)
    
    # Create active subscription record so WorkspaceService recognizes it
    from services.b2c.models.subscription import Subscription
    from services.b2c.models.subscription_plan import SubscriptionPlan
    from sqlalchemy import select

    # Lookup plan
    plan_res = await db_session.execute(select(SubscriptionPlan).where(SubscriptionPlan.tier_key == 'premium'))
    plan = plan_res.scalar_one_or_none()
    
    # If not found (should be seeded), create it
    if not plan:
        plan = SubscriptionPlan(
            tier_key='premium', 
            name='Premium Plan', 
            price_monthly=1900,
            limits={}, features={}
        )
        db_session.add(plan)
        await db_session.flush()

    subscription = Subscription(
        workspace_id=workspace.id,
        status="active",
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        plan_id=plan.id,
        user_id=user.id
    )
    db_session.add(subscription)
    
    await db_session.flush()
    
    mock_token_data = create_b2c_mock_token(firebase_uid, email)
    auth_token = encode_mock_jwt(mock_token_data)
    
    return {
        "user": user,
        "workspace": workspace,
        "auth_token": auth_token,
        "firebase_uid": firebase_uid,
        "email": email
    }


@pytest_asyncio.fixture
async def team_workspace(db_session, premium_workspace_owner):
    """Create a team workspace with owner as member"""
    await rls_service.set_user_context(db_session, premium_workspace_owner['user'].id)
    
    workspace = Workspace(
        name="Test Team Workspace",
        type=WorkspaceType.team,
        owner_id=premium_workspace_owner['user'].id,
        subscription_tier='premium'
    )
    db_session.add(workspace)
    await db_session.flush()
    
    # Add owner as member
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=premium_workspace_owner['user'].id,
        role='owner'
    )
    db_session.add(member)
    await db_session.flush()
    await db_session.refresh(workspace)
    
    return workspace


@pytest_asyncio.fixture
async def team_member_user(db_session):
    """Create a regular user (will be invited to workspace)"""
    email = f"member-{uuid4().hex[:8]}@example.com"
    firebase_uid = f"firebase-{uuid4().hex[:12]}"
    
    user = await create_b2c_user(db_session, email, firebase_uid, "Team Member")
    workspace = await create_b2c_workspace(db_session, user.id, "Member's Personal Workspace", 'personal')
    user.default_workspace_id = workspace.id
    
    await db_session.flush()
    
    mock_token_data = create_b2c_mock_token(firebase_uid, email)
    auth_token = encode_mock_jwt(mock_token_data)
    
    return {
        "user": user,
        "workspace": workspace,
        "auth_token": auth_token,
        "firebase_uid": firebase_uid,
        "email": email
    }


@pytest_asyncio.fixture
async def workspace_with_members(db_session, premium_workspace_owner, team_member_user):
    """Create a team workspace with multiple members"""
    await rls_service.set_user_context(db_session, premium_workspace_owner['user'].id)
    
    workspace = Workspace(
        name="Multi-Member Workspace",
        type=WorkspaceType.team,
        owner_id=premium_workspace_owner['user'].id,
        subscription_tier='premium'
    )
    db_session.add(workspace)
    await db_session.flush()
    
    # Add owner
    owner_member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=premium_workspace_owner['user'].id,
        role='owner'
    )
    db_session.add(owner_member)
    await db_session.flush()
    
    # Set RLS context for team member to allow adding them
    await rls_service.set_user_context(db_session, team_member_user['user'].id)
    
    # Add team member
    team_member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=team_member_user['user'].id,
        role='member'
    )
    db_session.add(team_member)
    await db_session.flush()
    
    # Reset context back to owner
    await rls_service.set_user_context(db_session, premium_workspace_owner['user'].id)
    await db_session.refresh(workspace)
    
    return {
        "workspace": workspace,
        "owner": premium_workspace_owner,
        "member": team_member_user
    }


@pytest_asyncio.fixture
async def workspace_invitation(db_session, team_workspace, premium_workspace_owner):
    """Create a pending workspace invitation"""
    await rls_service.set_user_context(db_session, premium_workspace_owner['user'].id)
    
    invitee_email = f"invitee-{uuid4().hex[:8]}@example.com"
    
    invitation = WorkspaceInvitation(
        workspace_id=team_workspace.id,
        email=invitee_email,
        role='member',
        invitation_token=f"token_{uuid4().hex}",
        invited_by=premium_workspace_owner['user'].id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    db_session.add(invitation)
    await db_session.flush()
    await db_session.refresh(invitation)
    
    return {
        "invitation": invitation,
        "workspace": team_workspace,
        "inviter": premium_workspace_owner,
        "invitee_email": invitee_email
    }
