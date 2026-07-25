import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


@pytest.mark.integration
class TestRBACPlugins:

    @pytest.mark.asyncio
    async def test_plugins_are_active(self, api_client: AsyncClient, b2b_test_setup, db_session):
        """
        Plugin enrichment runs in middleware on every authenticated request.
        Enabling plugins on the tenant should surface clearance_level,
        geographic_scopes, and accessible_teams in /auth/me -> active_features.
        """
        setup = b2b_test_setup
        token = setup["token"]
        session = setup["session"]
        tenant_id = setup["tenant_id"]

        # Enable all three plugins for this test tenant
        from modules.b2b.services.tenant_service import tenant_service
        await tenant_service.update_tenant_features(
            session,
            tenant_id,
            {"plugins": ["data_classification", "geographic_boundaries", "hierarchical_teams"]},
        )
        await session.commit()

        response = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        active_features = data.get("active_features", {})

        assert "clearance_level" in active_features, (
            "clearance_level missing — DataClassificationPlugin.enrich_user_context() not running"
        )
        assert "geographic_scopes" in active_features, (
            "geographic_scopes missing — GeographicBoundariesPlugin.enrich_user_context() not running"
        )
        assert "accessible_teams" in active_features, (
            "accessible_teams missing — HierarchicalTeamsPlugin.enrich_user_context() not running"
        )
        assert active_features.get("context_enriched") is True, (
            "context_enriched flag not set — plugin_registry.enrich_user() did not complete successfully"
        )

    @pytest.mark.asyncio
    async def test_clearance_level_from_team_role(self, api_client: AsyncClient, b2b_test_setup, db_session):
        """
        clearance_level must be an integer derived from the user's highest team role.
        A user with no team membership defaults to 1 (INTERNAL).
        """
        setup = b2b_test_setup
        token = setup["token"]
        session = setup["session"]
        tenant_id = setup["tenant_id"]

        from modules.b2b.services.tenant_service import tenant_service
        await tenant_service.update_tenant_features(
            session, tenant_id, {"plugins": ["data_classification"]}
        )
        await session.commit()

        response = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        active_features = response.json().get("active_features", {})
        assert "clearance_level" in active_features
        assert isinstance(active_features["clearance_level"], int)
        assert 0 <= active_features["clearance_level"] <= 4

    @pytest.mark.asyncio
    async def test_geographic_scopes_is_list(self, api_client: AsyncClient, b2b_test_setup, db_session):
        """
        geographic_scopes must always be a list.
        For a user with no team-region mapping it is an empty list (not null).
        """
        setup = b2b_test_setup
        token = setup["token"]
        session = setup["session"]
        tenant_id = setup["tenant_id"]

        from modules.b2b.services.tenant_service import tenant_service
        await tenant_service.update_tenant_features(
            session, tenant_id, {"plugins": ["geographic_boundaries", "hierarchical_teams"]}
        )
        await session.commit()

        response = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        active_features = response.json().get("active_features", {})
        assert isinstance(active_features.get("geographic_scopes"), list)

    @pytest.mark.asyncio
    async def test_plugin_enrichment_fail_returns_unenriched_flag(
        self, api_client: AsyncClient, b2b_test_setup, db_session, monkeypatch
    ):
        """
        If plugin enrichment raises, the middleware must return context with
        context_enriched=False so the permission checker re-enriches rather
        than trusting an incomplete context.
        """
        setup = b2b_test_setup
        token = setup["token"]
        session = setup["session"]
        tenant_id = setup["tenant_id"]

        from modules.b2b.services.tenant_service import tenant_service
        await tenant_service.update_tenant_features(
            session, tenant_id, {"plugins": ["data_classification"]}
        )
        await session.commit()

        # Force enrich_user to raise
        from core.rbac import plugin_registry as pr_module
        async def broken_enrich(user, db, enabled_plugin_names=None):
            raise RuntimeError("simulated enrichment failure")

        monkeypatch.setattr(pr_module.plugin_registry, "enrich_user", broken_enrich)

        response = await api_client.get(
            "/api/b2b/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Request still succeeds (middleware falls back gracefully)
        assert response.status_code == 200
        active_features = response.json().get("active_features", {})
        assert active_features.get("context_enriched") is False
