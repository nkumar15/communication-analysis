"""
API Tests for Bank Surveillance Alerts

Tests list, escalate, and close alert endpoints.
Uses Layer-2 RBAC (TeamRoleDefinition) to grant alerts permissions since these
are domain-specific roles not present in the foundation seed.
"""
import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import select

from modules.domains.b2b.bank_surveillance.models.alert import Alert, AlertStatus, AlertSeverity, RiskType
from modules.domains.b2b.bank_surveillance.models.communication import Communication


async def setup_alerts_rbac(setup):
    """
    Grant alerts permissions via Layer-2 TeamRoleDefinition.

    Uses raw_db + platform-admin bypass so this works regardless of the
    current RLS context state, matching the pattern used by regulatory/controls tests.
    """
    from sqlalchemy import text
    from modules.b2b.models.team_role_definition import TeamRoleDefinition
    from modules.b2b.models.team import Team
    from modules.b2b.models.team_member import TeamMember

    raw_db = setup["session"]._session
    tenant_id = setup["tenant_id"]
    user = setup["owner"]

    await raw_db.execute(text("SET app.is_platform_admin = 'true'"))

    if user not in raw_db:
        user = await raw_db.merge(user)
    await raw_db.refresh(user)

    # Create or fetch surveillance_chief team role with full alerts permissions
    role = (await raw_db.execute(
        select(TeamRoleDefinition)
        .where(TeamRoleDefinition.name == "surveillance_chief")
        .where(TeamRoleDefinition.tenant_id == tenant_id)
    )).scalar_one_or_none()

    if not role:
        role = TeamRoleDefinition(
            tenant_id=tenant_id,
            name="surveillance_chief",
            display_name="Chief Surveillance Officer",
            permissions=[{
                "resource": "alerts",
                "actions": ["read", "write", "update", "acknowledge", "escalate", "close"]
            }]
        )
        raw_db.add(role)
        await raw_db.flush()

    # Create a team
    team = (await raw_db.execute(
        select(Team)
        .where(Team.name == "Surveillance HQ")
        .where(Team.tenant_id == tenant_id)
    )).scalar_one_or_none()

    if not team:
        team = Team(tenant_id=tenant_id, name="Surveillance HQ")
        raw_db.add(team)
        await raw_db.flush()

    # Assign owner to team with the surveillance_chief role
    tm = (await raw_db.execute(
        select(TeamMember)
        .where(TeamMember.user_id == user.id)
        .where(TeamMember.team_id == team.id)
    )).scalar_one_or_none()

    if not tm:
        raw_db.add(TeamMember(
            team_id=team.id,
            user_id=user.id,
            team_role_id=role.id,
            team_role=role.name,
        ))
        await raw_db.flush()

    await raw_db.execute(text("SET app.is_platform_admin = 'false'"))
    await raw_db.commit()


@pytest.mark.asyncio
async def test_api_list_alerts(api_client, b2b_test_setup):
    """Happy path: List alerts returns at least the one we seeded."""
    setup = b2b_test_setup
    tenant_id = setup["tenant_id"]
    headers = {"Authorization": f"Bearer {setup['token']}"}

    await setup_alerts_rbac(setup)

    # Seed Communication + Alert via TenantAwareSession so _ensure_context()
    # sets current_tenant_id before each INSERT (satisfies RLS without platform admin).
    db = setup["session"]

    comm = Communication(
        tenant_id=tenant_id,
        channel="email",
        sender="tracer@test.com",
        recipients=["target@test.com"],
        timestamp=datetime.now(timezone.utc),
        message_id=str(uuid.uuid4()),
    )
    db.add(comm)
    await db.flush()

    alert = Alert(
        tenant_id=tenant_id,
        communication_id=comm.id,
        risk_type=RiskType.INSIDER_TRADING.value,
        severity=AlertSeverity.HIGH.value,
        status=AlertStatus.OPEN.value,
        description="Test Alert",
    )
    db.add(alert)
    await db.flush()
    await db.commit()

    alert_id = str(alert.id)

    response = await api_client.get(
        "/api/b2b/domain/bank_surveillance/alerts/",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    ids = [a["id"] for a in data]
    assert alert_id in ids
    matched = next(a for a in data if a["id"] == alert_id)
    assert matched["risk_type"] == RiskType.INSIDER_TRADING.value


@pytest.mark.asyncio
async def test_api_update_alert_status(api_client, b2b_test_setup):
    """Happy path: Escalate then close an alert via API."""
    setup = b2b_test_setup
    tenant_id = setup["tenant_id"]
    headers = {"Authorization": f"Bearer {setup['token']}"}

    await setup_alerts_rbac(setup)

    # Seed Communication + Alert via TenantAwareSession (sets current_tenant_id for RLS)
    db = setup["session"]

    comm = Communication(
        tenant_id=tenant_id,
        channel="chat",
        sender="trader@test.com",
        recipients=[],
        timestamp=datetime.now(timezone.utc),
        message_id=str(uuid.uuid4()),
    )
    db.add(comm)
    await db.flush()

    alert = Alert(
        tenant_id=tenant_id,
        communication_id=comm.id,
        risk_type=RiskType.OFF_CHANNEL.value,
        severity=AlertSeverity.MEDIUM.value,
        status=AlertStatus.OPEN.value,
    )
    db.add(alert)
    await db.flush()
    await db.commit()

    alert_id = str(alert.id)

    # Escalate
    resp = await api_client.post(
        f"/api/b2b/domain/bank_surveillance/alerts/{alert_id}/escalate",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == AlertStatus.ESCALATED.value

    # Close
    resp = await api_client.post(
        f"/api/b2b/domain/bank_surveillance/alerts/{alert_id}/close",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == AlertStatus.CLOSED.value
