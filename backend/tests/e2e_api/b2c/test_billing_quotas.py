"""
E2E Tests for B2C Billing - Quota Constants and Tier Definitions

These tests verify the quota tier limit constants are correctly defined.
Note: QuotaService uses sync SQLAlchemy patterns - runtime tests should
use the API endpoints instead when testing enforcement.
"""
import pytest

from services.b2c.services.quota_service import TIER_LIMITS


@pytest.mark.asyncio
async def test_tier_limits_free_tier_defined():
    """Test free tier limits are correctly defined"""
    assert "free" in TIER_LIMITS
    assert "max_projects" in TIER_LIMITS["free"]
    assert "max_team_workspaces" in TIER_LIMITS["free"]
    assert "max_team_members" in TIER_LIMITS["free"]


@pytest.mark.asyncio
async def test_tier_limits_premium_tier_defined():
    """Test premium tier limits are correctly defined"""
    assert "premium" in TIER_LIMITS
    assert "max_projects" in TIER_LIMITS["premium"]
    # Premium has unlimited projects (None means unlimited)
    assert TIER_LIMITS["premium"]["max_projects"] is None


@pytest.mark.asyncio
async def test_tier_limits_ultimate_tier_defined():
    """Test ultimate tier limits are correctly defined"""
    assert "ultimate" in TIER_LIMITS
    # Ultimate has unlimited team members (None means unlimited)
    assert TIER_LIMITS["ultimate"]["max_team_members"] is None


@pytest.mark.asyncio
async def test_free_tier_has_limited_projects():
    """Test free tier has a project limit"""
    max_projects = TIER_LIMITS["free"]["max_projects"]
    assert max_projects is not None  # Not unlimited
    assert max_projects > 0
    assert max_projects <= 10  # Reasonable limit


@pytest.mark.asyncio
async def test_free_tier_cannot_create_team_workspaces():
    """Test free tier cannot create team workspaces"""
    assert TIER_LIMITS["free"]["max_team_workspaces"] == 0


@pytest.mark.asyncio
async def test_premium_tier_allows_team_workspaces():
    """Test premium tier allows team workspaces"""
    max_team = TIER_LIMITS["premium"]["max_team_workspaces"]
    assert max_team is None or max_team > 0


@pytest.mark.asyncio
async def test_team_member_limits_scale_with_tier():
    """Test team member limits increase with tier"""
    free_members = TIER_LIMITS["free"]["max_team_members"]
    premium_members = TIER_LIMITS["premium"]["max_team_members"]
    ultimate_members = TIER_LIMITS["ultimate"]["max_team_members"]
    
    # Free is always limited
    assert free_members is not None and free_members > 0
    
    # Premium > Free (or unlimited)
    assert premium_members is None or premium_members > free_members
    
    # Ultimate is unlimited
    assert ultimate_members is None


@pytest.mark.asyncio
async def test_enforce_quota_decorator_exists():
    """Test @enforce_quota decorator exists and is callable"""
    from services.b2c.services.quota_service import enforce_quota
    assert callable(enforce_quota)


@pytest.mark.asyncio  
async def test_require_feature_decorator_exists():
    """Test @require_feature decorator exists and is callable"""
    from services.b2c.services.quota_service import require_feature
    assert callable(require_feature)
