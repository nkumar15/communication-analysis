from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class BillingProfileSearchItem(BaseModel):
    id: UUID
    type: str # 'tenant' or 'user'
    name: str
    email: Optional[str] = None
    domain: Optional[str] = None
    status: str
    
class BillingProfileSearchResponse(BaseModel):
    items: List[BillingProfileSearchItem]
    
class SubscriptionDetail(BaseModel):
    id: UUID
    status: str
    plan_name: Optional[str] = None
    tier: Optional[str] = None
    amount_cents: int
    currency: str
    billing_interval: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    trial_ends_at: Optional[datetime] = None
    cancel_at_period_end: bool
    provider: str
    seat_count: Optional[int] = None # B2B specific

class InvoiceItem(BaseModel):
    id: UUID
    provider_invoice_id: Optional[str] = None
    amount_due: int
    amount_paid: int
    currency: str
    status: str
    created_at: datetime
    paid_at: Optional[datetime] = None
    invoice_pdf_url: Optional[str] = None

class BillingProfileDetail(BaseModel):
    id: UUID
    type: str
    name: str
    email: Optional[str] = None
    tax_id: Optional[str] = None
    billing_address: Optional[Dict[str, Any]] = None
    compliance_settings: Optional[Dict[str, Any]] = None
    subscription: Optional[SubscriptionDetail] = None
    invoices: List[InvoiceItem] = []
    
class TrialExtendRequest(BaseModel):
    days: int = Field(..., gt=0)
    
class SubscriptionCancelRequest(BaseModel):
    reason: Optional[str] = None
    immediate: bool = False

class CouponCreateRequest(BaseModel):
    code: str
    discount_type: str # 'percentage' or 'fixed_amount'
    discount_percent: Optional[int] = None
    discount_amount_cents: Optional[int] = None
    currency: str = 'USD'
    max_redemptions: Optional[int] = None
    valid_until: Optional[datetime] = None
    applicable_tiers: Optional[List[str]] = None
    description: Optional[str] = None

class CouponResponse(BaseModel):
    id: UUID
    code: str
    discount_type: str
    discount_percent: Optional[int]
    discount_amount_cents: Optional[int]
    is_active: bool
    times_redeemed: int
    provider_coupon_id: Optional[str]
