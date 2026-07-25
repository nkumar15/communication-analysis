"""
RBAC Authorization Tests for Bank Surveillance

Tests Layer-2 (team-role) based access control and the geographic-boundaries
plugin enforcement, including:
  - CSO can access the communications endpoint (Layer-2 permission)
  - Geographic plugin correctly bypasses for global roles (plugin layer)
  - Analyst is denied cross-region analysis submission (plugin + handler check)
"""
import pytest
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from modules.b2b.models.team import Team
from modules.b2b.models.team_member import TeamMember
from modules.b2b.models.team_role_definition import TeamRoleDefinition
from modules.b2b.rbac.permission_checker import has_permission_with_plugins
from tests.conftest import create_auth_headers, create_test_user

import pytest_asyncio


@pytest_asyncio.fixture
async def bank_setup(db_session, b2b_test_setup):
    """
    Seed bank surveillance roles, teams, and two users (CSO + Analyst).

    Commits at the end so the HTTP request layer (which uses the same db_session
    via override_get_db) can see the data through RLS-protected queries.
    """
    setup = b2b_test_setup
    tenant_id = setup["tenant_id"]

    # 1. Surveillance Chief role — can access comms + investigations globally
    chief_role = (await db_session.execute(
        select(TeamRoleDefinition)
        .where(TeamRoleDefinition.name == "surveillance_chief")
        .where(TeamRoleDefinition.tenant_id == tenant_id)
    )).scalar_one_or_none()

    if not chief_role:
        chief_role = TeamRoleDefinition(
            tenant_id=tenant_id,
            name="surveillance_chief",
            display_name="Chief Surveillance Officer",
            permissions=[
                {"resource": "communications", "actions": ["read"]},
                {"resource": "investigations", "actions": ["read"]},
            ],
        )
        db_session.add(chief_role)
        await db_session.flush()

    # 2. Analyst role — can read comms and investigations (limited region)
    analyst_role = (await db_session.execute(
        select(TeamRoleDefinition)
        .where(TeamRoleDefinition.name == "surveillance_analyst")
        .where(TeamRoleDefinition.tenant_id == tenant_id)
    )).scalar_one_or_none()

    if not analyst_role:
        analyst_role = TeamRoleDefinition(
            tenant_id=tenant_id,
            name="surveillance_analyst",
            display_name="Surveillance Analyst",
            permissions=[
                {"resource": "communications", "actions": ["read"]},
                {"resource": "investigations", "actions": ["read"]},
            ],
        )
        db_session.add(analyst_role)
        await db_session.flush()

    # 3. Teams
    global_team = Team(name=f"Global Surveillance {uuid4().hex[:6]}", tenant_id=tenant_id)
    eu_desk = Team(name=f"EU Desk {uuid4().hex[:6]}", tenant_id=tenant_id)
    db_session.add_all([global_team, eu_desk])
    await db_session.flush()

    # 4. CSO user
    cso_user = await create_test_user(
        db_session,
        tenant_id=tenant_id,
        email=f"cso-{uuid4().hex[:6]}@{setup['tenant'].domain}",
        role_slug="member",
    )
    db_session.add(TeamMember(
        team_id=global_team.id,
        user_id=cso_user.id,
        team_role_id=chief_role.id,
        team_role=chief_role.name,
    ))
    await db_session.flush()

    # 5. Analyst user
    analyst_user = await create_test_user(
        db_session,
        tenant_id=tenant_id,
        email=f"analyst-{uuid4().hex[:6]}@{setup['tenant'].domain}",
        role_slug="member",
    )
    db_session.add(TeamMember(
        team_id=eu_desk.id,
        user_id=analyst_user.id,
        team_role_id=analyst_role.id,
        team_role=analyst_role.name,
    ))
    await db_session.flush()

    # 6. Enable geographic_boundaries plugin for this tenant
    tenant = setup["tenant"]
    tenant.features = {"plugins": ["geographic_boundaries"]}
    db_session.add(tenant)
    await db_session.flush()

    # Commit so HTTP requests (using the same db_session) see the data
    await db_session.commit()

    return {
        **setup,
        "chief_role": chief_role,
        "analyst_role": analyst_role,
        "cso_user": cso_user,
        "analyst_user": analyst_user,
        "global_team": global_team,
        "eu_desk": eu_desk,
    }


@pytest.mark.asyncio
async def test_surveillance_chief_api_access(api_client, bank_setup):
    """
    CSO with Layer-2 'communications:read' team permission gets 200 on the
    communications list endpoint (no specific resource region → plugin allows).
    """
    cso = bank_setup["cso_user"]
    headers = create_auth_headers(cso, bank_setup["tenant"])

    response = await api_client.get(
        "/api/b2b/domain/bank_surveillance/communications",
        headers=headers,
    )

    assert response.status_code == 200, f"CSO denied: {response.text}"
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_global_role_bypass_logic(db_session, bank_setup):
    """
    Geographic plugin: a role listed in global_roles bypasses region checks.

    We configure the registered GeographicBoundariesPlugin instance directly
    (test-scoped, no production side-effects after the test session ends) so that
    'surveillance_chief' is treated as a global role.
    """
    from core.rbac.plugin_registry import plugin_registry
    from plugins.geographic_boundaries.plugin import GeographicBoundariesPlugin

    # Locate the registered geographic plugin and apply test config
    geo_plugin = next(
        (p for p in plugin_registry._plugins.values() if isinstance(p, GeographicBoundariesPlugin)),
        None,
    )
    assert geo_plugin is not None, "GeographicBoundariesPlugin not registered"

    original_config = geo_plugin.config
    geo_plugin.config = {
        "global_roles": ["surveillance_chief"],
        "enforce_strict": True,
    }

    try:
        cso = bank_setup["cso_user"]
        analyst = bank_setup["analyst_user"]
        tenant_id = str(bank_setup["tenant_id"])

        # Restore tenant RLS context (bank_setup committed, clearing SET LOCAL)
        from core.db.rls import rls_service
        await rls_service.set_tenant_context(db_session, bank_setup["tenant_id"])

        # Random region that neither user's scope covers
        class FakeResource:
            data_region_id = uuid4()

        resource = FakeResource()

        # Build pre-enriched user contexts (context_enriched=True) so
        # has_permission_with_plugins uses the cached path and the team_roles
        # field is available to the geographic plugin without a DB fetch.
        # This also avoids RLS issues — after bank_setup commits, the tenant
        # context (SET LOCAL) is gone, so DB fallback queries would return 0 rows.
        def _enriched(user, team_role_name):
            return {
                "id": str(user.id),
                "tenant_id": tenant_id,
                "role_id": str(user.role_id) if user.role_id else None,
                "role": "member",
                "team_roles": [team_role_name],
                "geographic_scopes": [],
                "enabled_plugins": ["geographic_boundaries"],
                "context_enriched": True,
            }

        # Analyst: Layer-2 grants 'communications:read', but geographic plugin
        # denies because the region is not in the analyst's empty scopes
        allowed_analyst = await has_permission_with_plugins(
            str(analyst.id),
            "communications",
            "read",
            db_session,
            extra_context={
                "user": _enriched(analyst, "surveillance_analyst"),
                "resource": resource,
            },
        )
        assert not allowed_analyst, "Analyst should be denied by geographic plugin"

        # CSO: 'surveillance_chief' is in global_roles → bypass region check
        allowed_cso = await has_permission_with_plugins(
            str(cso.id),
            "communications",
            "read",
            db_session,
            extra_context={
                "user": _enriched(cso, "surveillance_chief"),
                "resource": resource,
            },
        )
        assert allowed_cso, "CSO should bypass geographic restriction"

    finally:
        # Restore original plugin config so other tests are not affected
        geo_plugin.config = original_config


@pytest.mark.asyncio
async def test_cross_region_analysis_submission(api_client, bank_setup):
    """
    Analyst submitting analysis for a region outside their geographic scopes
    receives 403 Forbidden (geographic plugin enforces the restriction inside
    the /analyze handler before any LLM call is made).
    """
    analyst = bank_setup["analyst_user"]
    headers = create_auth_headers(analyst, bank_setup["tenant"])

    # Random region UUID — analyst has no scopes so any non-None region is denied
    payload = {
        "text": "Suspicious conversation about LIBOR manipulation.",
        "metadata": {
            "data_region_id": str(uuid4()),
            "sender": "trader@bank.com",
        },
    }

    response = await api_client.post(
        "/api/b2b/domain/bank_surveillance/analyze",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 403, (
        f"Expected 403 (geographic denial), got {response.status_code}: {response.text}"
    )
