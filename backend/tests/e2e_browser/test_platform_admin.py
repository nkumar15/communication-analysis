"""
E2E Browser Test - Platform Admin Flow (ONB-01)

This test verifies the platform admin login and tenant creation workflow.
Requirement: ONB-01 (Platform Admin Invite)
"""
import pytest
import secrets
import time
from playwright.sync_api import Page, expect
from .e2e_helpers import create_platform_admin_token

# Helper to generate unique tenant data
def generate_tenant_data():
    suffix = secrets.token_hex(4)
    return {
        "name": f"Test Corp {suffix}",
        "domain": f"test-corp-{suffix}.com",
        "email": f"owner-{suffix}@example.com"
    }

@pytest.mark.asyncio
async def test_platform_admin_create_tenant_flow(page: Page):
    """
    Test ONB-01: Platform Admin can invite/create a new tenant.
    
    Steps:
    1. Login as Platform Admin (via custom token backdoor).
    2. Navigate to Tenant List.
    3. Create new Tenant.
    4. Verify Tenant appears in list with PENDING status.
    """
    # 1. Prepare Data & Token
    admin_email = "admin@platform.com"
    token = await create_platform_admin_token(admin_email)
    tenant_data = generate_tenant_data()
    
    # 2. Inject Token & Login
    page.goto("/")  # Load app first
    
    # Inject token into localStorage for the App.js backdoor
    page.evaluate(f"localStorage.setItem('custom_token', '{token}')")
    
    # Reload to trigger initAuth with the token
    page.reload()
    
    # Wait for dashboard to load (protected route)
    # The app should redirect to /dashboard or /super-admin/dashboard depending on role
    # Platform admins usually go to /super-admin/dashboard
    expect(page.get_by_text("Initializing")).to_be_hidden(timeout=10000)
    
    # Navigate explicitly to Super Admin Tenants page
    page.goto("/super-admin/tenants")
    
    # Verify we are on the tenant list page
    expect(page.get_by_role("heading", name="Tenants")).to_be_visible()
    
    # 3. Create Tenant
    # Click "Create Tenant" button
    page.get_by_role("button", name="Create Tenant").click()
    
    # Fill Form
    page.get_by_label("Company Name").fill(tenant_data["name"])
    page.get_by_label("Domain").fill(tenant_data["domain"])
    page.get_by_label("Owner Email").fill(tenant_data["email"])
    
    # Select OIDC Provider (assuming default exists or dropdown handles it)
    # If the dropdown is for "Auth Provider", we might need to select one.
    # Assuming 'Generic OIDC' is default or selectable. 
    # Try creating without selecting first if it defaults.
    # Actually, the form usually requires an OIDC provider config or select existing.
    # Let's check for "OIDC Provider" input.
    # For now, let's assume simple inputs. If this fails, we debug the form.
    
    page.get_by_role("button", name="Create Tenant").click()
    
    # 4. Verify Success
    # Should see success toast or redirect
    expect(page.get_by_text("Tenant created successfully")).to_be_visible()
    
    # 5. Verify List
    # Search for the new tenant
    page.get_by_placeholder("Search tenants...").fill(tenant_data["name"])
    
    # Expect row to exist
    expect(page.get_by_role("cell", name=tenant_data["name"])).to_be_visible()
    expect(page.get_by_role("cell", name="pending")).to_be_visible()
