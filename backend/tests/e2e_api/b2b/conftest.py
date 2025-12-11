"""
Fixtures for domain API tests (projects, tasks, comments)
"""
import pytest
import pytest_asyncio
from uuid import uuid4

from tests.conftest import (
    create_test_user,
    create_test_tenant,
    create_mock_firebase_token,
    encode_mock_jwt
)
from services.b2b.models import Team, TeamMember
from sqlalchemy import select


@pytest_asyncio.fixture
async def domain_test_data(db_session):
    """Setup tenant, teams, and users for domain tests.
    
    Note: Domain resources and role template updates are now handled by 
    create_test_tenant() in the main conftest.py.
    """
    # Create tenant (this seeds domain resources and updates templates)
    tenant = await create_test_tenant(db_session)
    
    # Create owner user
    owner = await create_test_user(
        db_session,
        tenant_id=tenant.id,
        email=f"owner@{tenant.domain}",
        role_slug="owner"
    )
    owner_token = encode_mock_jwt(create_mock_firebase_token(
        uid=owner.firebase_uid,
        email=owner.email,
        firebase_tenant_id=tenant.firebase_tenant_id
    ))
    
    # Get default team
    result = await db_session.execute(
        select(Team).where(
            Team.tenant_id == tenant.id,
            Team.is_default == True
        )
    )
    default_team = result.scalar_one()
    
    # Create another team
    other_team = Team(
        tenant_id=tenant.id,
        name="Other Team",
        is_default=False
    )
    db_session.add(other_team)
    from sqlalchemy import text
    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant.id}'"))
    await db_session.flush()
    
    # Create team member for default team
    team_member = await create_test_user(
        db_session,
        tenant_id=tenant.id,
        email=f"member@{tenant.domain}",
        role_slug="member"
    )
    team_member_assoc = TeamMember(
        team_id=default_team.id,
        user_id=team_member.id,
        team_role="team_member"
    )
    db_session.add(team_member_assoc)
    
    team_member_token = encode_mock_jwt(create_mock_firebase_token(
        uid=team_member.firebase_uid,
        email=team_member.email,
        firebase_tenant_id=tenant.firebase_tenant_id
    ))
    
    # Create member for other team
    other_team_member = await create_test_user(
        db_session,
        tenant_id=tenant.id,
        email=f"othermember@{tenant.domain}",
        role_slug="member"
    )
    other_team_assoc = TeamMember(
        team_id=other_team.id,
        user_id=other_team_member.id,
        team_role="team_member"
    )
    db_session.add(other_team_assoc)
    
    other_team_member_token = encode_mock_jwt(create_mock_firebase_token(
        uid=other_team_member.firebase_uid,
        email=other_team_member.email,
        firebase_tenant_id=tenant.firebase_tenant_id
    ))
    
    # Create second tenant for isolation tests
    tenant2 = await create_test_tenant(db_session, domain=f"tenant2-{uuid4().hex[:8]}.test")
    tenant2_owner = await create_test_user(
        db_session,
        tenant_id=tenant2.id,
        email=f"owner@{tenant2.domain}",
        role_slug="owner"
    )
    tenant2_owner_token = encode_mock_jwt(create_mock_firebase_token(
        uid=tenant2_owner.firebase_uid,
        email=tenant2_owner.email,
        firebase_tenant_id=tenant2.firebase_tenant_id
    ))
    
    # Get tenant2 default team
    result = await db_session.execute(
        select(Team).where(
            Team.tenant_id == tenant2.id,
            Team.is_default == True
        )
    )
    tenant2_team = result.scalar_one()
    
    # Create viewer user (read-only role) in default team
    viewer = await create_test_user(
        db_session,
        tenant_id=tenant.id,
        email=f"viewer@{tenant.domain}",
        role_slug="viewer"
    )
    viewer_assoc = TeamMember(
        team_id=default_team.id,
        user_id=viewer.id,
        team_role="team_viewer"
    )
    db_session.add(viewer_assoc)
    
    viewer_token = encode_mock_jwt(create_mock_firebase_token(
        uid=viewer.firebase_uid,
        email=viewer.email,
        firebase_tenant_id=tenant.firebase_tenant_id
    ))
    
    await db_session.commit()
    
    return {
        "tenant": tenant,
        "owner": owner,
        "owner_token": owner_token,
        "default_team": default_team,
        "other_team": other_team,
        "team_member": team_member,
        "team_member_token": team_member_token,
        "other_team_member": other_team_member,
        "other_team_member_token": other_team_member_token,
        "viewer": viewer,
        "viewer_token": viewer_token,
        "tenant2": tenant2,
        "tenant2_owner": tenant2_owner,
        "tenant2_owner_token": tenant2_owner_token,
        "tenant2_team": tenant2_team
    }


@pytest_asyncio.fixture
async def team_project(db_session, domain_test_data):
    """Create a test project in default team"""
    from services.domains.projects.models.project import Project
    
    project = Project(
        tenant_id=domain_test_data["tenant"].id,
        team_id=domain_test_data["default_team"].id,
        name="Test Project",
        description="Test project description",
        created_by=domain_test_data["owner"].id
    )
    db_session.add(project)
    from sqlalchemy import text
    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{domain_test_data['tenant'].id}'"))
    await db_session.flush()
    await db_session.refresh(project)
    return project.id


@pytest_asyncio.fixture
async def other_team_project(db_session, domain_test_data):
    """Create a test project in another team"""
    from services.domains.projects.models.project import Project
    
    project = Project(
        tenant_id=domain_test_data["tenant"].id,
        team_id=domain_test_data["other_team"].id,
        name="Other Team Project",
        description="Project for another team",
        created_by=domain_test_data["owner"].id
    )
    db_session.add(project)
    from sqlalchemy import text
    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{domain_test_data['tenant'].id}'"))
    await db_session.flush()
    await db_session.refresh(project)
    return project.id


@pytest_asyncio.fixture
async def tenant2_project(db_session, domain_test_data):
    """Create a project for tenant 2"""
    from services.domains.projects.models.project import Project
    
    project = Project(
        tenant_id=domain_test_data["tenant2"].id,
        team_id=domain_test_data["tenant2_team"].id,
        name="Tenant 2 Project",
        description="Project for tenant 2",
        created_by=domain_test_data["tenant2_owner"].id
    )
    db_session.add(project)
    from sqlalchemy import text
    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{domain_test_data['tenant2'].id}'"))
    await db_session.flush()
    await db_session.refresh(project)
    return project.id


@pytest_asyncio.fixture
async def team_task(db_session, team_project, domain_test_data):
    """Create a test task in team project"""
    from services.domains.projects.models.task import Task
    
    task = Task(
        tenant_id=domain_test_data["tenant"].id,
        project_id=team_project,
        title="Test Task",
        description="Test task description",
        status="todo",
        created_by=domain_test_data["owner"].id
    )
    db_session.add(task)
    from sqlalchemy import text
    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{domain_test_data['tenant'].id}'"))
    await db_session.flush()
    await db_session.refresh(task)
    return task.id


@pytest_asyncio.fixture
async def team_comment(db_session, team_task, domain_test_data):
    """Create a test comment on task"""
    from services.domains.projects.models.comment import Comment
    
    comment = Comment(
        tenant_id=domain_test_data["tenant"].id,
        task_id=team_task,
        content="Test comment content",
        created_by=domain_test_data["owner"].id
    )
    db_session.add(comment)
    from sqlalchemy import text
    await db_session.execute(text(f"SET LOCAL app.current_tenant_id = '{domain_test_data['tenant'].id}'"))
    await db_session.flush()
    await db_session.refresh(comment)
    return comment.id
