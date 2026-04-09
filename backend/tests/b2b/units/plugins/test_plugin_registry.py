"""
Unit Tests for RBAC Plugin Registry

Tests the plugin registration, initialization, and permission check flow.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from core.rbac.plugin_registry import PluginRegistry
from core.rbac.plugin_system import RBACPlugin, PermissionContext


pytestmark = pytest.mark.asyncio


class MockPlugin(RBACPlugin):
    """Mock plugin for testing registry"""

    def __init__(self, name: str = "mock_plugin"):
        self._name = name
        self._initialized = False
        self._before_result = None  # None = no short-circuit
        self._after_result = None  # None = pass through

    def get_metadata(self):
        return {
            "name": self._name,
            "version": "1.0.0",
            "description": f"Mock plugin: {self._name}"
        }

    async def initialize(self, db, config):
        self._initialized = True
        self._config = config
        return True

    async def before_permission_check(self, context, db):
        return self._before_result

    async def after_permission_check(self, context, core_result, db):
        if self._after_result is not None:
            return self._after_result
        return core_result

    async def enrich_user_context(self, user, db):
        return {f"{self._name}_enriched": True}


class FailingPlugin(RBACPlugin):
    """Mock plugin that raises exceptions for fail-safe testing."""

    def __init__(
        self,
        name: str = "failing_plugin",
        fail_before: bool = False,
        fail_after: bool = False,
        fail_enrich: bool = False,
    ):
        self._name = name
        self.fail_before = fail_before
        self.fail_after = fail_after
        self.fail_enrich = fail_enrich

    def get_metadata(self):
        return {"name": self._name, "version": "1.0.0"}

    async def initialize(self, db, config):
        return True

    async def before_permission_check(self, context, db):
        if self.fail_before:
            raise RuntimeError("simulated before_check failure")
        return None

    async def after_permission_check(self, context, core_result, db):
        if self.fail_after:
            raise RuntimeError("simulated after_check failure")
        return core_result

    async def enrich_user_context(self, user, db):
        if self.fail_enrich:
            raise RuntimeError("simulated enrichment failure")
        return {"test_enriched": True}


class TestPluginRegistration:
    """Tests for plugin registration"""
    
    async def test_register_plugin(self):
        """Test registering a new plugin"""
        registry = PluginRegistry()
        plugin = MockPlugin("test_plugin")
        
        registry.register(plugin)
        
        fetched = registry.get_plugin("test_plugin")
        assert fetched is not None
        assert fetched._name == "test_plugin"
    
    async def test_register_duplicate_overwrites(self):
        """Test that registering duplicate name overwrites"""
        registry = PluginRegistry()
        plugin1 = MockPlugin("dup_plugin")
        plugin1._config = {"version": 1}
        
        plugin2 = MockPlugin("dup_plugin")
        plugin2._config = {"version": 2}
        
        registry.register(plugin1)
        registry.register(plugin2)
        
        fetched = registry.get_plugin("dup_plugin")
        assert fetched is plugin2
    
    async def test_get_nonexistent_plugin_returns_none(self):
        """Test that getting unregistered plugin returns None"""
        registry = PluginRegistry()
        
        result = registry.get_plugin("nonexistent")
        assert result is None


class TestPluginInitialization:
    """Tests for plugin initialization"""
    
    async def test_initialize_all_plugins(self):
        """Test initializing all registered plugins"""
        registry = PluginRegistry()
        plugin1 = MockPlugin("plugin1")
        plugin2 = MockPlugin("plugin2")
        
        registry.register(plugin1)
        registry.register(plugin2)
        
        config = {
            "plugin1": {"setting": "value1"},
            "plugin2": {"setting": "value2"}
        }
        
        await registry.initialize_all(None, config)
        
        assert plugin1._initialized is True
        assert plugin2._initialized is True
        assert plugin1._config == {"setting": "value1"}
        assert plugin2._config == {"setting": "value2"}


class TestPermissionCheckFlow:
    """Tests for permission check flow through plugins"""
    
    async def test_core_checker_called(self):
        """Test that core checker is called in the flow"""
        registry = PluginRegistry()
        
        core_checker = AsyncMock(return_value=True)
        
        ctx = PermissionContext(
            user_id="u1",
            user={"id": "u1"},
            resource_type="data",
            resource_id="r1",
            resource=None,
            action="read",
            tenant_id="t1",
            extra_context={}
        )
        
        result = await registry.check_permission(ctx, core_checker, None)
        
        core_checker.assert_called_once()
        assert result is True
    
    async def test_before_check_short_circuit_allow(self):
        """Test that before_check can short-circuit with ALLOW"""
        registry = PluginRegistry()
        plugin = MockPlugin("short_circuit")
        plugin._before_result = True  # Short-circuit ALLOW
        registry.register(plugin)
        
        core_checker = AsyncMock(return_value=False)  # Core would deny
        
        ctx = PermissionContext(
            user_id="u1",
            user={"id": "u1"},
            resource_type="data",
            resource_id="r1",
            resource=None,
            action="read",
            tenant_id="t1",
            extra_context={}
        )
        
        result = await registry.check_permission(ctx, core_checker, None)
        
        # Plugin short-circuited before core_checker
        core_checker.assert_not_called()
        assert result is True
    
    async def test_before_check_short_circuit_deny(self):
        """Test that before_check can short-circuit with DENY"""
        registry = PluginRegistry()
        plugin = MockPlugin("short_circuit")
        plugin._before_result = False  # Short-circuit DENY
        registry.register(plugin)
        
        core_checker = AsyncMock(return_value=True)  # Core would allow
        
        ctx = PermissionContext(
            user_id="u1",
            user={"id": "u1"},
            resource_type="data",
            resource_id="r1",
            resource=None,
            action="read",
            tenant_id="t1",
            extra_context={}
        )
        
        result = await registry.check_permission(ctx, core_checker, None)
        
        core_checker.assert_not_called()
        assert result is False
    
    async def test_after_check_can_override_core_result(self):
        """Test that after_check can override core result"""
        registry = PluginRegistry()
        plugin = MockPlugin("veto")
        plugin._after_result = False  # Override to DENY
        registry.register(plugin)
        
        core_checker = AsyncMock(return_value=True)  # Core allows
        
        ctx = PermissionContext(
            user_id="u1",
            user={"id": "u1"},
            resource_type="data",
            resource_id="r1",
            resource=None,
            action="read",
            tenant_id="t1",
            extra_context={}
        )
        
        result = await registry.check_permission(ctx, core_checker, None)
        
        assert result is False
    
    async def test_plugin_filter_by_enabled_names(self):
        """Test that only specified plugins run when names provided"""
        registry = PluginRegistry()
        
        plugin1 = MockPlugin("plugin1")
        plugin1._after_result = False
        
        plugin2 = MockPlugin("plugin2")
        plugin2._after_result = True
        
        registry.register(plugin1)
        registry.register(plugin2)
        
        core_checker = AsyncMock(return_value=True)
        
        ctx = PermissionContext(
            user_id="u1",
            user={"id": "u1"},
            resource_type="data",
            resource_id="r1",
            resource=None,
            action="read",
            tenant_id="t1",
            extra_context={}
        )
        
        # Only enable plugin2 (which allows)
        result = await registry.check_permission(
            ctx, core_checker, None, 
            enabled_plugin_names=["plugin2"]
        )
        
        # plugin1 was skipped, so result should be True (plugin2's result)
        assert result is True


class TestUserEnrichment:
    """Tests for user context enrichment"""
    
    async def test_enrich_user_aggregates_all_plugins(self):
        """Test that enrichment aggregates data from all plugins"""
        registry = PluginRegistry()
        
        registry.register(MockPlugin("plugin1"))
        registry.register(MockPlugin("plugin2"))
        
        user = {"id": "u1"}
        
        enriched = await registry.enrich_user(user, None)
        
        assert enriched["id"] == "u1"
        assert enriched["plugin1_enriched"] is True
        assert enriched["plugin2_enriched"] is True
    
    async def test_enrich_user_filters_by_enabled(self):
        """Test that enrichment respects enabled_plugin_names"""
        registry = PluginRegistry()

        registry.register(MockPlugin("plugin1"))
        registry.register(MockPlugin("plugin2"))

        user = {"id": "u1"}

        enriched = await registry.enrich_user(
            user, None,
            enabled_plugin_names=["plugin1"]
        )

        assert enriched["plugin1_enriched"] is True
        assert "plugin2_enriched" not in enriched


class TestFailSafeBehavior:
    """Fail-safe: plugin exceptions must DENY access, never silently pass."""

    async def test_before_check_exception_denies_access(self):
        """Plugin raising in before_permission_check must DENY — not pass to core check."""
        registry = PluginRegistry()
        registry.register(FailingPlugin("failing", fail_before=True))

        core_checker = AsyncMock(return_value=True)  # core would allow

        ctx = PermissionContext(
            user_id="u1", user={"id": "u1"}, resource_type="data",
            resource_id="r1", resource=None, action="read",
            tenant_id="t1", extra_context={}
        )

        result = await registry.check_permission(ctx, core_checker, None)

        assert result is False
        core_checker.assert_not_called()

    async def test_after_check_exception_denies_access(self):
        """Plugin raising in after_permission_check must DENY — not leave core result unchanged."""
        registry = PluginRegistry()
        registry.register(FailingPlugin("failing", fail_after=True))

        core_checker = AsyncMock(return_value=True)  # core allows

        ctx = PermissionContext(
            user_id="u1", user={"id": "u1"}, resource_type="data",
            resource_id="r1", resource=None, action="read",
            tenant_id="t1", extra_context={}
        )

        result = await registry.check_permission(ctx, core_checker, None)

        core_checker.assert_called_once()
        assert result is False

    async def test_healthy_plugins_still_run_if_failing_plugin_is_disabled(self):
        """A failing plugin that is disabled must not affect enabled plugins."""
        registry = PluginRegistry()
        failing = FailingPlugin("bad", fail_after=True)
        healthy = MockPlugin("good")
        healthy._after_result = True

        registry.register(failing)
        registry.register(healthy)

        core_checker = AsyncMock(return_value=True)

        ctx = PermissionContext(
            user_id="u1", user={"id": "u1"}, resource_type="data",
            resource_id="r1", resource=None, action="read",
            tenant_id="t1", extra_context={}
        )

        # Only 'good' is enabled
        result = await registry.check_permission(
            ctx, core_checker, None, enabled_plugin_names=["good"]
        )

        assert result is True


class TestEnrichmentFlags:
    """context_enriched flag must accurately reflect whether enrichment completed."""

    async def test_context_enriched_true_after_all_plugins_succeed(self):
        registry = PluginRegistry()
        registry.register(MockPlugin("p1"))
        registry.register(MockPlugin("p2"))

        enriched = await registry.enrich_user({"id": "u1"}, None)

        assert enriched.get("context_enriched") is True

    async def test_context_enriched_true_when_no_plugins_registered(self):
        """An empty registry still sets context_enriched=True (no failures)."""
        registry = PluginRegistry()

        enriched = await registry.enrich_user({"id": "u1"}, None)

        assert enriched.get("context_enriched") is True

    async def test_context_enriched_false_when_plugin_raises(self):
        """Any plugin exception must set context_enriched=False and return early."""
        registry = PluginRegistry()
        registry.register(MockPlugin("healthy"))
        registry.register(FailingPlugin("broken", fail_enrich=True))

        enriched = await registry.enrich_user({"id": "u1"}, None)

        assert enriched.get("context_enriched") is False

    async def test_enrichment_halts_after_first_exception(self):
        """Remaining plugins must not run after one raises."""
        registry = PluginRegistry()

        failing = FailingPlugin("first", fail_enrich=True)
        second = MockPlugin("second")
        second.enrich_user_context = AsyncMock(return_value={"second_key": True})

        registry.register(failing)
        registry.register(second)

        await registry.enrich_user({"id": "u1"}, None)

        second.enrich_user_context.assert_not_called()


class TestCheckDependencies:
    """check_dependencies() must be called for each active plugin during enrichment."""

    async def test_called_for_each_active_plugin(self):
        registry = PluginRegistry()
        p1 = MockPlugin("p1")
        p2 = MockPlugin("p2")
        p1.check_dependencies = MagicMock()
        p2.check_dependencies = MagicMock()
        registry.register(p1)
        registry.register(p2)

        await registry.enrich_user({"id": "u1"}, None, enabled_plugin_names=["p1", "p2"])

        p1.check_dependencies.assert_called_once_with(["p1", "p2"])
        p2.check_dependencies.assert_called_once_with(["p1", "p2"])

    async def test_not_called_without_enabled_names(self):
        """When enabled_plugin_names is None, skip the dependency check loop."""
        registry = PluginRegistry()
        p1 = MockPlugin("p1")
        p1.check_dependencies = MagicMock()
        registry.register(p1)

        await registry.enrich_user({"id": "u1"}, None)

        p1.check_dependencies.assert_not_called()

    async def test_only_called_for_enabled_subset(self):
        """Disabled plugins must not have check_dependencies called."""
        registry = PluginRegistry()
        p1 = MockPlugin("p1")
        p2 = MockPlugin("p2")
        p1.check_dependencies = MagicMock()
        p2.check_dependencies = MagicMock()
        registry.register(p1)
        registry.register(p2)

        await registry.enrich_user({"id": "u1"}, None, enabled_plugin_names=["p1"])

        p1.check_dependencies.assert_called_once()
        p2.check_dependencies.assert_not_called()
