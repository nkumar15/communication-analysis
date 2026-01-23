
import pytest
pytestmark = pytest.mark.skip(reason="Requires domain-specific fixtures not currently in foundation scope")

import uuid
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from modules.domains.b2b.bank_surveillance.models.alert import Alert, AlertStatus, AlertSeverity, RiskType
from modules.domains.b2b.bank_surveillance.models.communication import Communication

# Use the b2b_test_setup fixture which creates a tenant and admin user
@pytest.mark.asyncio
async def test_api_list_alerts(api_client: AsyncClient, b2b_test_setup):
    setup = b2b_test_setup
    tenant_id = setup['tenant_id']
    headers = {"Authorization": f"Bearer {setup['token']}"}
    
    # 1. Setup RBAC: Assign surveillance_chief team role to user
    db = setup['session']
    
    # Ensure role exists (or fetch it)
    from modules.b2b.models.team_role_definition import TeamRoleDefinition
    from modules.b2b.models.team import Team
    from modules.b2b.models.team_member import TeamMember
    
    role_stmt = select(TeamRoleDefinition).where(TeamRoleDefinition.name == "surveillance_chief").where(TeamRoleDefinition.tenant_id == tenant_id)
    role = (await db.execute(role_stmt)).scalar_one_or_none()
    
    if not role:
        # Create minimal role if missing (fallback for test isolation)
        role = TeamRoleDefinition(
            tenant_id=tenant_id,
            name="surveillance_chief",
            display_name="Chief Surveillance Officer",
            permissions=[{"resource": "alerts", "actions": ["read", "write", "update"]}] 
        )
        db.add(role)
        await db.flush()

    # Check/Create Team
    team_stmt = select(Team).where(Team.name == "Surveillance HQ").where(Team.tenant_id == tenant_id)
    team = (await db.execute(team_stmt)).scalar_one_or_none()
    if not team:
        team = Team(tenant_id=tenant_id, name="Surveillance HQ")
        db.add(team)
        await db.flush()
    
    # Assign User to Team
    tm_stmt = select(TeamMember).where(TeamMember.user_id == setup['owner'].id).where(TeamMember.team_id == team.id)
    tm = (await db.execute(tm_stmt)).scalar_one_or_none()
    if not tm:
        tm = TeamMember(
            team_id=team.id,
            user_id=setup['owner'].id,
            team_role_id=role.id,
            team_role=role.name
        )
        db.add(tm)
        await db.flush()

    # Create a dummy communication & alert in DB
    comm = Communication(
        tenant_id=tenant_id,
        channel="email",
        sender="tracer@test.com",
        recipients=["target@test.com"],
        timestamp=datetime.utcnow(), 
        message_id=str(uuid.uuid4())
    )
    db.add(comm)
    await db.flush()
    
    alert = Alert(
        tenant_id=tenant_id,
        communication_id=comm.id,
        risk_type=RiskType.INSIDER_TRADING.value,
        severity=AlertSeverity.HIGH.value,
        status=AlertStatus.OPEN.value,
        description="Test Alert"
    )
    db.add(alert)
    await db.commit()
    alert_id = str(alert.id)

    # 2. Call API
    response = await api_client.get(
        "/api/b2b/domain/bank_surveillance/alerts/",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]['id'] == alert_id
    assert data[0]['risk_type'] == RiskType.INSIDER_TRADING.value

@pytest.mark.asyncio
async def test_api_update_alert_status(api_client: AsyncClient, b2b_test_setup):
    setup = b2b_test_setup
    tenant_id = setup['tenant_id']
    headers = {"Authorization": f"Bearer {setup['token']}"}
    
    # 1. Setup RBAC: Assign surveillance_chief team role to user (if not already done)
    db = setup['session']
    
    # Ensure role exists (or fetch it) - duplicated for independence
    from modules.b2b.models.team_role_definition import TeamRoleDefinition
    from modules.b2b.models.team import Team
    from modules.b2b.models.team_member import TeamMember
    
    role_stmt = select(TeamRoleDefinition).where(TeamRoleDefinition.name == "surveillance_chief").where(TeamRoleDefinition.tenant_id == tenant_id)
    role = (await db.execute(role_stmt)).scalar_one_or_none()
    
    if not role:
        role = TeamRoleDefinition(
            tenant_id=tenant_id,
            name="surveillance_chief",
            display_name="Chief Surveillance Officer",
            permissions=[{"resource": "alerts", "actions": ["read", "write", "update", "acknowledge", "escalate", "close"]}] 
        )
        db.add(role)
    else:
        # Update permissions if role exists to ensure 'close' action is present
        role.permissions = [{"resource": "alerts", "actions": ["read", "write", "update", "acknowledge", "escalate", "close"]}]
        db.add(role)
    
    await db.flush()

    # Check/Create Team
    team_stmt = select(Team).where(Team.name == "Surveillance HQ 2").where(Team.tenant_id == tenant_id)
    team = (await db.execute(team_stmt)).scalar_one_or_none()
    if not team:
        team = Team(tenant_id=tenant_id, name="Surveillance HQ 2")
        db.add(team)
        await db.flush()
    
    # Assign User
    tm_stmt = select(TeamMember).where(TeamMember.user_id == setup['owner'].id).where(TeamMember.team_id == team.id)
    tm = (await db.execute(tm_stmt)).scalar_one_or_none()
    if not tm:
        tm = TeamMember(
            team_id=team.id,
            user_id=setup['owner'].id,
            team_role_id=role.id,
            team_role=role.name
        )
        db.add(tm)
        await db.flush()

    # Create alert context
    comm = Communication(
        tenant_id=tenant_id,
        channel="chat",
        sender="trader@test.com",
        recipients=[],
        timestamp=datetime.utcnow(),
        message_id=str(uuid.uuid4())
    )
    db.add(comm)
    await db.flush()
    
    alert = Alert(
        tenant_id=tenant_id,
        communication_id=comm.id,
        risk_type=RiskType.OFF_CHANNEL.value,
        severity=AlertSeverity.MEDIUM.value,
        status=AlertStatus.OPEN.value
    )
    db.add(alert)
    await db.commit()
    alert_id = str(alert.id)

    # 2. Call Escalate endpoint
    response = await api_client.post(
        f"/api/b2b/domain/bank_surveillance/alerts/{alert_id}/escalate",
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()['status'] == AlertStatus.ESCALATED.value

    # 3. Call Close endpoint
    response = await api_client.post(
        f"/api/b2b/domain/bank_surveillance/alerts/{alert_id}/close",
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()['status'] == AlertStatus.CLOSED.value
