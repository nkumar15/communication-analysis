import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_public_plans(async_client: AsyncClient, test_db_session):
    """Test fetching public subscription plans"""
    # Seed plans first
    from scripts.b2c.seed_subscription_plans import seed_plans
    await seed_plans(test_db_session)
    
    response = await async_client.get("/api/b2c/plans")
    assert response.status_code == 200
    
    plans = response.json()
    assert isinstance(plans, list)
    assert len(plans) >= 1 # Should at least have the seeded plans
    
    # Check structure
    plan = plans[0]
    assert "tier_key" in plan
    assert "name" in plan
    assert "price_monthly" in plan
    assert "features" in plan
    assert "limits" in plan
    
    # Verify we have at least 'free', 'premium', 'ultimate' from seeds
    tiers = [p['tier_key'] for p in plans]
    assert 'free' in tiers
    assert 'premium' in tiers
    assert 'ultimate' in tiers
    
    # Check specific values for free plan
    free_plan = next(p for p in plans if p['tier_key'] == 'free')
    assert free_plan['price_monthly'] == 0
    assert free_plan['price_yearly'] == 0
