# Manual Test Recording Guide for E2E Browser Tests

## Overview

This guide explains how to record your manual testing sessions so they can be converted into automated Playwright test cases for the B2B portal.

## Recording Methods

### Method 1: Playwright Codegen (Recommended)

**Best for:** Immediate conversion to Playwright code

#### Setup & Recording

1. **Install Playwright browsers (if not already done):**
```bash
cd backend
python -m playwright install chromium
```

2. **Start your B2B application:**
```bash
# In project root
make restart  # Start without E2E profile
```

3. **Start Playwright Code Generator:**
```bash
cd backend

# Option A: Record from login page
python -m playwright codegen http://localhost:3000/login --target python-async

# Option B: Record with authenticated session (after manual login)
python -m playwright codegen http://localhost:3000 --target python-async
```

4. **Perform your manual test actions:**
   - The browser will open with a recorder panel
   - Perform your actions normally (click, type, navigate)
   - Playwright generates code in real-time
   - Copy the generated code when done

5. **Save the recording:**
   - Copy the generated code from the Playwright Inspector
   - Save to a temporary file: `backend/tests/e2e_browser/recordings/my_test_YYYYMMDD.py`

#### Generated Code Example

```python
# This is what Playwright codegen produces:
async def test_example():
    page = await browser.new_page()
    await page.goto("http://localhost:3000/login")
    await page.get_by_label("Email").fill("admin@example.com")
    await page.get_by_label("Password").fill("password123")
    await page.get_by_role("button", name="Sign In").click()
    await page.wait_for_url("**/dashboard")
    await expect(page.get_by_role("heading", name="Dashboard")).to_be_visible()
```

---

## Recording Strategy for Page-Specific Tests

### Problem: Large Test Files from Navigation

When you navigate around, codegen creates one large test with all actions. Instead, **record each page/feature in isolation**.

### Solution: Record with Saved Authentication State

#### Step 1: Save Authentication State Once

```bash
cd backend

# Record login + save state
python -m playwright codegen \
  --save-storage=auth.json \
  http://localhost:3000/login
```

**Actions to perform:**
1. Enter email/password
2. Click login
3. Wait for dashboard to load
4. Close browser (state is saved)

This creates `auth.json` with cookies and localStorage.

---

#### Step 2: Record Each Page Separately

Now you can record each feature **starting from authenticated state**:

**Example: Recording Teams Page**

```bash
# Start directly at Teams page, already logged in
python -m playwright codegen \
  --load-storage=auth.json \
  --target python-async \
  http://localhost:3000/teams
```

**Benefits:**
- ✅ Starts already authenticated
- ✅ No login code in output
- ✅ Focus only on Teams page actions
- ✅ Smaller, focused test code

**What to record:**
1. Click "Add Team" button
2. Fill team name
3. Add members
4. Submit
5. Verify team appears
6. **Stop recording (close browser)**

**Example: Recording Billing Page**

```bash
python -m playwright codegen \
  --load-storage=auth.json \
  --target python-async \
  http://localhost:3000/settings/billing
```

**What to record:**
1. Click "Update Payment Method"
2. (Stripe modal interactions)
3. Verify update
4. **Stop recording**

---

### Quick Recording Workflow

For each test you want to create:

**1. Decide what page/feature to test**
   - Example: "Add new user"

**2. Start codegen at that specific page**
```bash
python -m playwright codegen \
  --load-storage=auth.json \
  http://localhost:3000/users
```

**3. Perform ONLY that one feature**
   - Click "Add User"
   - Fill form
   - Submit
   - Verify user appears

**4. Close browser immediately**
   - Don't navigate elsewhere
   - This keeps the recording focused

**5. Save output to descriptive file**
```bash
# Copy generated code to:
recordings/add_user_20251224.py
```

**6. Repeat for next feature**

---

### Examples of Focused Recordings

#### ✅ Good: Focused on One Feature

```bash
# Record: Create role
python -m playwright codegen --load-storage=auth.json http://localhost:3000/roles
# Actions: Click Add → Fill name → Set permissions → Save → Verify
# Result: Small test focused on role creation
```

#### ❌ Bad: Full Navigation Flow

```bash
# Record: Login → Dashboard → Teams → Create team → Users → Create user → Settings
# Result: One huge test with mixed concerns
```

---

### Page-Specific Recording Checklist

For each page you want to test, record separately:

**Teams Page:**
```bash
python -m playwright codegen --load-storage=auth.json http://localhost:3000/teams
```
- [ ] Add team
- [ ] Edit team name
- [ ] Delete team
- [ ] Add member to team

**Users Page:**
```bash
python -m playwright codegen --load-storage=auth.json http://localhost:3000/users
```
- [ ] Add user
- [ ] Change user role
- [ ] Suspend user
- [ ] Remove user

**Billing Page:**
```bash
python -m playwright codegen --load-storage=auth.json http://localhost:3000/settings/billing
```
- [ ] Update payment method
- [ ] Change plan
- [ ] View invoices

**Roles Page:**
```bash
python -m playwright codegen --load-storage=auth.json http://localhost:3000/roles
```
- [ ] Create custom role
- [ ] Edit role permissions
- [ ] Delete role

---

### Tips for Better Page-Specific Tests

1. **One recording = One user action**
   - "Add user" is one recording
   - "Edit user" is a separate recording
   - Don't mix them

2. **Start at the specific page**
   - Use exact URL: `/users`, `/teams`, `/settings/billing`
   - Don't record navigation from dashboard

3. **Stop immediately after verification**
   - Add item → Verify it appears → **Close browser**
   - Don't continue navigating

4. **Use descriptive filenames**
   ```
   recordings/
   ├── add_user_20251224.py
   ├── edit_user_role_20251224.py
   ├── create_team_20251224.py
   ├── update_billing_20251224.py
   ```

5. **Save state for different user types**
   ```bash
   # Admin user
   --save-storage=auth_admin.json
   
   # Regular user
   --save-storage=auth_user.json
   
   # Owner
   --save-storage=auth_owner.json
   ```

---

### Updated Helper Commands

```bash
# FIRST TIME: Save auth state
python -m playwright codegen --save-storage=auth.json http://localhost:3000/login

# THEN: Record each feature separately

# Teams
python -m playwright codegen --load-storage=auth.json http://localhost:3000/teams

# Users  
python -m playwright codegen --load-storage=auth.json http://localhost:3000/users

# Billing
python -m playwright codegen --load-storage=auth.json http://localhost:3000/settings/billing

# Roles
python -m playwright codegen --load-storage=auth.json http://localhost:3000/roles

# Settings
python -m playwright codegen --load-storage=auth.json http://localhost:3000/settings
```


---

### Method 2: Playwright Trace Viewer (Detailed Analysis)

**Best for:** Understanding complex interactions, debugging failures

#### Setup

After running a test or manual session with tracing enabled:

```bash
cd backend

# Run existing test with tracing
pytest tests/e2e_browser/b2b/test_dashboard.py --tracing=on

# View the trace
playwright show-trace test-results/trace.zip
```

This opens a UI showing:
- Every action taken
- Screenshots at each step  
- Network requests
- Console logs
- Timeline of events

#### Using Traces for Test Creation

1. **Manually create a trace:**
```python
# Add to conftest.py or run manually
import asyncio
from playwright.async_api import async_playwright

async def manual_recording():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        
        # Start tracing
        await context.tracing.start(screenshots=True, snapshots=True)
        
        page = await context.new_page()
        await page.goto("http://localhost:3000")
        
        # Perform manual actions here
        input("Press Enter after completing your manual test...")
        
        # Save trace
        await context.tracing.stop(path="manual_test_trace.zip")
        await browser.close()

# Run with: python -c "import asyncio; from script import manual_recording; asyncio.run(manual_recording())"
```

2. **Analyze trace:**
```bash
playwright show-trace manual_test_trace.zip
```

3. **Extract actions from trace and convert to test code**

---

### Method 3: Screen Recording + Documentation

**Best for:** Complex workflows, sharing with team

#### Recording Tools

**macOS:**
```bash
# Built-in Screen Recording (Cmd+Shift+5)
# or
brew install kap  # Better screen recorder with GIF output
```

**Linux:**
```bash
sudo apt install kazam  # or SimpleScreenRecorder
```

**Windows:**
```
Win+G (Xbox Game Bar)
or OBS Studio
```

#### Create Documentation

While recording, create a markdown file with:

**File:** `backend/tests/e2e_browser/recordings/billing_update_payment_method_20251224.md`

```markdown
# Test Recording: Update Billing Payment Method

**Recorded:** 2024-12-24  
**Recorded by:** Neeraj  
**Browser:** Chrome  
**Video:** billing_update_payment_method.mp4

## Preconditions
- User: test-admin@company.com
- Tenant: Test Tenant (has active subscription)
- Current plan: Pro Plan

## Test Steps

### 1. Navigate to Billing
- **Action:** Click "Settings" in sidebar
- **Expected:** Settings page loads
- **Selector:** `[data-testid="sidebar-settings"]` or `text=Settings`

### 2. Go to Billing Tab
- **Action:** Click "Billing" tab
- **Expected:** Billing information visible
- **Selector:** `[role="tab"][name="Billing"]`

### 3. Click Update Payment Method
- **Action:** Click "Update Payment Method" button
- **Expected:** Stripe modal opens
- **Selector:** `button:has-text("Update Payment Method")`

### 4. Enter New Card Details
- **Action:** Fill in card info in Stripe iframe
  - Card: 4242 4242 4242 4242
  - Expiry: 12/25
  - CVC: 123
- **Expected:** Form accepts input
- **Selector:** Stripe Elements (iframes)

### 5. Submit Update
- **Action:** Click "Update" button
- **Expected:** Success message appears
- **Selector:** `button:has-text("Update")`

### 6. Verify Update
- **Action:** Check updated card ending
- **Expected:** "•••• 4242" visible
- **Selector:** `.card-details` or `text=•••• 4242`

## Actual Results
✅ Payment method updated successfully
✅ New card ending displayed correctly
✅ No errors in console

## Screenshots
- screenshot_01_billing_page.png
- screenshot_02_stripe_modal.png
- screenshot_03_success_message.png

## Notes
- Stripe test mode used
- Modal animation took ~500ms to appear
- Success message auto-dismissed after 3s
```

---

## Converting Recordings to Tests

### Step 1: Identify Test Type

| Recording Contains | Create Test In | Create Page Object In |
|-------------------|----------------|----------------------|
| Login flow | `b2b/test_auth.py` | `pages/b2b/login_page.py` |
| Team management | `b2b/test_teams.py` | `pages/b2b/teams_page.py` |
| User management | `b2b/test_users.py` | `pages/b2b/users_page.py` |
| Billing | `b2b/test_billing.py` | `pages/b2b/billing_page.py` |
| Settings | `b2b/test_settings.py` | `pages/b2b/settings_page.py` |
| Roles | `b2b/test_roles.py` | `pages/b2b/roles_page.py` |

### Step 2: Extract Page Actions

From the codegen output or documentation, identify:

1. **Page-specific actions** → Add to Page Object
2. **Test assertions** → Add to test file
3. **Navigation** → Use in test file

### Step 3: Submit to AI (Me!)

Provide one of these:

#### Option A: Codegen Output
```
File: recordings/my_feature_test.py
<paste full codegen output>

Feature tested: [describe what you tested]
```

#### Option B: Documentation + Screenshots
```
File: recordings/my_feature_test.md
<paste markdown documentation>

Attached screenshots:
- screenshot_01.png
- screenshot_02.png
```

#### Option C: Video + Description
```
Video: recordings/my_feature_test.mp4

Description:
1. [high-level steps]
2. [what was tested]
3. [expected outcomes]

Timestamp notes:
- 0:15 - Clicked Add User button
- 0:30 - Filled form
- 0:45 - Submitted
- 1:00 - Verification
```

### Step 4: Review Generated Test

I will:
1. ✅ Create/update appropriate Page Object methods
2. ✅ Create test case using page objects pattern
3. ✅ Add proper assertions
4. ✅ Add error handling
5. ✅ Follow existing test conventions
6. ✅ Add helpful comments

---

## Quick Reference: Playwright Codegen Commands

```bash
# Basic recording
python -m playwright codegen http://localhost:3000

# With device emulation
python -m playwright codegen --device="iPhone 12" http://localhost:3000

# With specific browser
python -m playwright codegen --browser=firefox http://localhost:3000

# Load with existing state (cookies, localStorage)
python -m playwright codegen --load-storage=auth.json http://localhost:3000

# Save state after recording
python -m playwright codegen --save-storage=auth.json http://localhost:3000

# With viewport size
python -m playwright codegen --viewport-size=1920,1080 http://localhost:3000

# Generate Python async code (our format)
python -m playwright codegen --target python-async http://localhost:3000

# With timezone
python -m playwright codegen --timezone="America/New_York" http://localhost:3000
```

---

## Tips for Better Recordings

### 1. Use Stable Selectors

When possible, use:
- `data-testid` attributes (e.g., `[data-testid="login-button"]`)
- Role + name (e.g., `get_by_role("button", name="Sign In")`)
- Semantic HTML (e.g., `get_by_label("Email")`)

### 2. Add Deliberate Waits

When recording:
- Pause after clicking buttons
- Wait for modals to fully appear
- Let pages fully load

This helps codegen capture proper waiting logic.

### 3. Verify State

After each action:
- Check that the expected element appears
- Look for success messages
- Verify URL changes

### 4. Record Happy Path First

1. Record the successful flow first
2. Then record error cases separately
3. Edge cases can be recorded individually

### 5. Keep Recordings Short

- One feature per recording
- 2-5 minutes maximum
- Focus on specific user journey

---

## Example Workflow

### Recording a "Create New Team" Flow

**1. Start Recording:**
```bash
cd backend
python -m playwright codegen http://localhost:3000 --target python-async
```

**2. Perform Actions:**
- Log in as admin
- Navigate to Teams page
- Click "Add Team"
- Fill team name: "Engineering Team"
- Select members: alice@example.com, bob@example.com
- Click "Create"
- Verify team appears in list

**3. Save Output:**
```bash
# Copy generated code to:
backend/tests/e2e_browser/recordings/create_team_20251224.py
```

**4. Share with me:**
```
Hey, I recorded a test for creating teams. Here's the codegen output:
[paste code]

Feature: User can create a new team with members
Edge cases to handle:
- Empty team name
- Duplicate team name
- No members selected
```

**5. I'll generate:**
- Updated `pages/b2b/teams_page.py` with new methods
- Updated `b2b/test_teams.py` with new test cases
- Proper assertions and error handling

---

## Storage Location

```
backend/tests/e2e_browser/recordings/
├── README.md                          # This file
├── <feature>_<date>.py               # Codegen output
├── <feature>_<date>.md               # Documentation
├── <feature>_<date>.mp4              # Video recording
└── screenshots/
    ├── <feature>_01_<description>.png
    ├── <feature>_02_<description>.png
    └── ...
```

---

## Existing Test Structure Reference

### Page Object Pattern

```python
# pages/b2b/teams_page.py
class TeamsPage:
    def __init__(self, page: Page):
        self.page = page
        self.add_button = page.locator("[data-testid='add-team-button']")
        self.team_name_input = page.locator("[data-testid='team-name-input']")
    
    async def navigate(self):
        await self.page.goto("/teams")
    
    async def create_team(self, name: str):
        await self.add_button.click()
        await self.team_name_input.fill(name)
        await self.page.locator("[data-testid='submit-button']").click()
```

### Test File Pattern

```python
# b2b/test_teams.py
@pytest.mark.asyncio
@pytest.mark.browser
async def test_create_team(authenticated_b2b_page: Page, b2b_test_setup):
    """Test creating a new team"""
    page = authenticated_b2b_page
    teams_page = TeamsPage(page)
    
    await teams_page.navigate()
    await teams_page.create_team("Engineering")
    
    # Assertions
    await expect(page.locator("text=Engineering")).to_be_visible()
```

---

## Questions?

If you're unsure about what to record or how, just ask:
- "Should I record the entire user onboarding flow or break it into steps?"
- "What's the best way to record Stripe payment modal interactions?"
- "How do I handle dropdowns/autocompletes in recordings?"

I'm here to help!
