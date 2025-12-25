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
from modules.b2b.models import Team, TeamMember
from modules.b2b.models.team_role_definition import TeamRoleDefinition
from sqlalchemy import select, or_


# ============================================================================
# CORE B2B FIXTURES (for billing and other tests)
# ============================================================================


@pytest_asyncio.fixture
async def b2b_tenant(db_session):
    """Create a standard B2B tenant for testing"""
    tenant = await create_test_tenant(db_session)
    return tenant


@pytest_asyncio.fixture
async def b2b_tenant2(db_session):
    """Create a second B2B tenant for isolation tests"""
    tenant = await create_test_tenant(db_session, domain=f"tenant2-{uuid4().hex[:8]}.test")
    return tenant


@pytest_asyncio.fixture
async def b2b_tenant_owner(db_session, b2b_tenant):
    """Create owner user for b2b_tenant"""
    owner = await create_test_user(
        db_session,
        tenant_id=b2b_tenant.id,
        email=f"owner@{b2b_tenant.domain}",
        role_slug="owner"
    )
    return owner


@pytest_asyncio.fixture
async def b2b_tenant_owner_token(b2b_tenant, b2b_tenant_owner):
    """Create auth token for b2b_tenant owner"""
    return encode_mock_jwt(create_mock_firebase_token(
        uid=b2b_tenant_owner.firebase_uid,
        email=b2b_tenant_owner.email,
        firebase_tenant_id=b2b_tenant.firebase_tenant_id
    ))



# ============================================================================
# DOMAIN TEST DATA FIXTURES
# ============================================================================


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
    
    # Lookup team_contributor role
    contributor_role_result = await db_session.execute(
        select(TeamRoleDefinition).where(
            TeamRoleDefinition.name == "team_contributor",
            or_(TeamRoleDefinition.tenant_id.is_(None), TeamRoleDefinition.tenant_id == tenant.id)
        )
    )
    contributor_role = contributor_role_result.scalars().first()
    
    team_member_assoc = TeamMember(
        team_id=default_team.id,
        user_id=team_member.id,
        team_role="team_contributor",
        team_role_id=contributor_role.id if contributor_role else None
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
        team_role="team_contributor",
        team_role_id=contributor_role.id if contributor_role else None
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
    # Lookup team_reader role
    reader_role_result = await db_session.execute(
        select(TeamRoleDefinition).where(
            TeamRoleDefinition.name == "team_reader",
            or_(TeamRoleDefinition.tenant_id.is_(None), TeamRoleDefinition.tenant_id == tenant.id)
        )
    )
    reader_role = reader_role_result.scalars().first()
    
    viewer_assoc = TeamMember(
        team_id=default_team.id,
        user_id=viewer.id,
        team_role="team_reader",
        team_role_id=reader_role.id if reader_role else None
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
    from modules.domains.projects.models.project import Project
    
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
    from modules.domains.projects.models.project import Project
    
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
    from modules.domains.projects.models.project import Project
    
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
    from modules.domains.projects.models.task import Task
    
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
    from modules.domains.projects.models.comment import Comment
    
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


# ============================================================================
# BILLING FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def professional_subscription(db_session, b2b_tenant):
    """Create a professional tier subscription for testing"""
    from modules.b2b.models import (
        B2BSubscription,
        SubscriptionTier,
        PaymentMode,
        SubscriptionStatus
    )
    from datetime import datetime, timedelta, timezone
    from core.db.rls import rls_service
    
    await rls_service.set_tenant_context(db_session, b2b_tenant.id)
    
    # Always create a fresh subscription for each test
    subscription = B2BSubscription(
        tenant_id=b2b_tenant.id,
        tier=SubscriptionTier.PROFESSIONAL.value,
        payment_mode=PaymentMode.CARD.value,
        status=SubscriptionStatus.ACTIVE.value,
        seat_count=5,
        base_price_cents=5000,  # $50
        per_seat_price_cents=2000,  # $20
        total_amount_cents=15000,  # $50 + ($20 * 5) = $150
        billing_interval='monthly',
        currency='USD',
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30)
    )
    db_session.add(subscription)
    await db_session.flush()
    return subscription


@pytest_asyncio.fixture
async def enterprise_subscription(db_session, b2b_tenant):
    """Create an enterprise tier subscription for testing"""
    from modules.b2b.models import (
        B2BSubscription,
        SubscriptionTier,
        PaymentMode,
        SubscriptionStatus
    )
    from core.db.rls import rls_service
    
    await rls_service.set_tenant_context(db_session, b2b_tenant.id)
    
    # Always create a fresh subscription for each test
    subscription = B2BSubscription(
        tenant_id=b2b_tenant.id,
        tier=SubscriptionTier.ENTERPRISE.value,
        payment_mode=PaymentMode.INVOICE.value,
        status=SubscriptionStatus.ACTIVE.value,
        seat_count=20,
        base_price_cents=20000,  # $200
        per_seat_price_cents=5000,  # $50
        total_amount_cents=120000,  # $200 + ($50 * 20) = $1200
        billing_interval='monthly',
        currency='USD'
    )
    db_session.add(subscription)
    await db_session.flush()
    return subscription


@pytest_asyncio.fixture
async def paid_invoice(db_session, professional_subscription):
    """Create a paid invoice for testing"""
    from modules.b2b.models import B2BInvoice, InvoiceStatus
    from datetime import datetime, timedelta, timezone
    import secrets
    from core.db.rls import rls_service
    
    await rls_service.set_tenant_context(db_session, professional_subscription.tenant_id)
    
    # Generate unique invoice number
    unique_suffix = secrets.token_hex(4).upper()
    
    invoice = B2BInvoice(
        subscription_id=professional_subscription.id,
        tenant_id=professional_subscription.tenant_id,
        invoice_number=f"INV-{datetime.now(timezone.utc).strftime('%Y%m')}-PAID-{unique_suffix}",
        provider='manual',
        status=InvoiceStatus.PAID.value,
        amount_due=15000,
        amount_paid=15000,
        currency='USD',
        seat_count_snapshot=5,
        base_price_snapshot_cents=5000,
        per_seat_price_snapshot_cents=2000,
        billing_period_start=datetime.now(timezone.utc) - timedelta(days=60),
        billing_period_end=datetime.now(timezone.utc) - timedelta(days=30),
        invoice_date=datetime.now(timezone.utc) - timedelta(days=60),
        due_date=datetime.now(timezone.utc) - timedelta(days=30),
        paid_at=datetime.now(timezone.utc) - timedelta(days=25)
    )
    
    db_session.add(invoice)
    await db_session.flush()
    return invoice


@pytest_asyncio.fixture
async def pending_invoice(db_session, professional_subscription):
    """Create a pending (sent but unpaid) invoice for testing"""
    from modules.b2b.models import B2BInvoice, InvoiceStatus
    from datetime import datetime, timedelta, timezone
    import secrets
    from core.db.rls import rls_service
    
    await rls_service.set_tenant_context(db_session, professional_subscription.tenant_id)
    
    # Generate unique invoice number
    unique_suffix = secrets.token_hex(4).upper()
    
    invoice = B2BInvoice(
        subscription_id=professional_subscription.id,
        tenant_id=professional_subscription.tenant_id,
        invoice_number=f"INV-{datetime.now(timezone.utc).strftime('%Y%m')}-PENDING-{unique_suffix}",
        provider='manual',
        status=InvoiceStatus.SENT.value,
        amount_due=15000,
        amount_paid=0,
        currency='USD',
        seat_count_snapshot=5,
        base_price_snapshot_cents=5000,
        per_seat_price_snapshot_cents=2000,
        billing_period_start=datetime.now(timezone.utc) - timedelta(days=30),
        billing_period_end=datetime.now(timezone.utc),
        invoice_date=datetime.now(timezone.utc) - timedelta(days=30),
        due_date=datetime.now(timezone.utc) + timedelta(days=15)
    )
    
    db_session.add(invoice)
    await db_session.flush()
    return invoice


@pytest_asyncio.fixture
async def overdue_invoice(db_session, professional_subscription):
    """Create an overdue invoice for testing"""
    from modules.b2b.models import B2BInvoice, InvoiceStatus
    from datetime import datetime, timedelta, timezone
    import secrets
    from core.db.rls import rls_service
    
    await rls_service.set_tenant_context(db_session, professional_subscription.tenant_id)
    
    # Generate unique invoice number
    unique_suffix = secrets.token_hex(4).upper()
    
    invoice = B2BInvoice(
        subscription_id=professional_subscription.id,
        tenant_id=professional_subscription.tenant_id,
        invoice_number=f"INV-{datetime.now(timezone.utc).strftime('%Y%m')}-OVERDUE-{unique_suffix}",
        provider='manual',
        status=InvoiceStatus.OVERDUE.value,
        amount_due=15000,
        amount_paid=0,
        currency='USD',
        seat_count_snapshot=5,
        base_price_snapshot_cents=5000,
        per_seat_price_snapshot_cents=2000,
        billing_period_start=datetime.now(timezone.utc) - timedelta(days=60),
        billing_period_end=datetime.now(timezone.utc) - timedelta(days=30),
        invoice_date=datetime.now(timezone.utc) - timedelta(days=60),
        due_date=datetime.now(timezone.utc) - timedelta(days=10)
    )
    
    db_session.add(invoice)
    await db_session.flush()
    return invoice


@pytest_asyncio.fixture
async def platform_admin_user(db_session):
    """Create a platform admin user for testing"""
    from modules.platform.models import PlatformUser
    import secrets
    
    # Create platform admin user (no RLS for platform schema)
    unique_suffix = secrets.token_hex(4)
    admin = PlatformUser(
        email=f"admin@platform.test",
        firebase_uid=f"platform_admin_{unique_suffix}",
        display_name="Platform Admin",
        is_active=True
    )
    
    db_session.add(admin)
    await db_session.flush()
    return admin
