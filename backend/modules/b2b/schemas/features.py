"""
Pydantic schemas for subscription plan and tenant JSONB columns.

These models validate the shape of data written into:
  - b2b.subscription_plans.limits   → PlanLimits
  - b2b.subscription_plans.features → PlanFeatures
  - b2b.tenants.features            → TenantFeatures

Why typed schemas matter here:
  - JSONB columns accept any dict; without guards a bad seed or typo silently
    skips limit enforcement at runtime.
  - Validates on write (subscription service, seed scripts) rather than
    discovering problems at read time.
  - Unlimited sentinel is consistently -1 (never null).
"""

from pydantic import BaseModel, Field
from typing import List


# ---------------------------------------------------------------------------
# Plan-side schemas (what lives in b2b.subscription_plans)
# ---------------------------------------------------------------------------

class PlanLimits(BaseModel):
    """Resource quotas defined on a subscription plan.

    -1 means unlimited for all integer fields.
    Services that enforce limits must treat -1 as no cap.
    """
    max_users: int = Field(default=-1, ge=-1)
    max_teams: int = Field(default=-1, ge=-1)
    storage_gb: int = Field(default=-1, ge=-1)

    def is_unlimited(self, field: str) -> bool:
        return getattr(self, field, -1) == -1


class PlanFeatures(BaseModel):
    """Feature flags and plugin list defined on a subscription plan.

    Plugins are the only list field; everything else is a boolean flag.
    Limits are NOT stored here — they live in PlanLimits.
    """
    sso: bool = False
    audit_logs: bool = False
    bulk_invite: bool = False
    dedicated_support: bool = False
    custom_branding: bool = False
    plugins: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Tenant-side schema (what lives in b2b.tenants.features)
# ---------------------------------------------------------------------------

class TenantFeatures(BaseModel):
    """Active features for a tenant after a subscription is applied.

    Deliberately does NOT contain limits. Limits are always read live from
    the active subscription → plan row, so they can never go stale.
    Only feature flags (booleans) and the active plugin list live here.
    """
    sso: bool = False
    audit_logs: bool = False
    bulk_invite: bool = False
    dedicated_support: bool = False
    custom_branding: bool = False
    plugins: List[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}  # permit future flags without a migration
