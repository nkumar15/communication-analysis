# Bank Surveillance Use Case (Enterprise)

Complete RBAC configuration for Global Bank Surveillance operations, demonstrating **"Multi-Dimensional"** Attribute-Based Access Control (ABAC).

## 1. Target Organization Structure

We are modeling **Worldwide Bank**, a regulated financial institution with a hierarchical structure designed to enforce compliance and data segregation.

```mermaid
graph TD
    Global[Global HQ - New York] --> APAC[APAC Regional Hub - Singapore]
    APAC --> SG_Desk[SG Trading Desk - Bonds]
    APAC --> MY_Desk[MY Wealth Desk - Private Banking]
    
    style Global fill:#f9f,stroke:#333,color:#000
    style APAC fill:#bbf,stroke:#333,color:#000
    style SG_Desk fill:#c3e6cb,stroke:#333,color:#000
    style MY_Desk fill:#c3e6cb,stroke:#333,color:#000
```

*   **Global HQ:** Oversight of all regions (CSO).
*   **APAC Hub:** Management of Asian markets (Regional Director).
*   **Trading Desks:** Isolated operational units (Singapore & Malaysia).

---

## 2. Role Portfolio

We define specific roles to match the bank's operational and compliance needs.

| S.No. | Category | Role Name | Type | Description |
| :---: | :--- | :--- | :--- | :--- |
| 1 | **Leadership** | `surveillance_chief` | **Tenant** | C-Suite executive (CSO) with global oversight. |
| 2 | **Leadership** | `regional_director` | **Tenant** | Senior management for a specific region. |
| 3 | **Leadership** | `head_compliance` | **Tenant** | Global oversight (Head of Compliance). |
| 4 | **Desk** | `surveillance_lead` | **Team** | Runs a specific desk (e.g., Head of SG). |
| 5 | **Desk** | `surveillance_analyst` | **Team** | Standard investigator. |
| 6 | **Operations** | `operations_maker` | **Team** | Can create cases but **cannot approve**. |
| 7 | **Operations** | `operations_checker` | **Team** | Can approve cases but **cannot create**. |
| 8 | **Support** | `surveillance_ops` | **Team** | Surveillance Operations (SurvOps) - Monitors pipelines and stats. |
| 9 | **Audit** | `compliance_officer` | **Team** | Read-only regulatory oversight. |
| 10 | **External** | `guest_analyst` | **Team** | Limited read-only access for auditors. |
| 11 | **Base** | `member` | **Tenant** | **Safe Default.** Read-only listing of Users/Teams. **NO** access to surveillance data. |

---

## 3. Organizational Fit (Hybrid RBAC)

We use a **Hybrid Model** to map these roles to the organization. This distinguishes between *who you are* (Tenant Role) and *what you do* (Team Role).

### The "Access Pyramid"

```mermaid
graph TD
    %% Nodes with Clearance Levels
    CSO["CSO: Global Oversight<br/>Clearance: L4 (Top Secret)<br/>Geo: Global Bypass"] 
    -->|Manages| Dir["Director: Regional Oversight<br/>Clearance: L3 (Confidential)<br/>Geo: Regional Scope"]
    
    Dir -->|Manages| SG["SG Head<br/>Clearance: L2<br/>Geo: SG Only"]
    Dir -->|Manages| MY["MY Head<br/>Clearance: L2<br/>Geo: MY Only"]

    %% Plugin Boundary
    subgraph "Geo-Fenced Zone (Strict Data Isolation)"
    SG
    MY
    end

    %% Styles
    style CSO fill:#ffcccc,stroke:#333,color:#000
    style Dir fill:#fff2cc,stroke:#333,color:#000
    style SG fill:#d4edda,stroke:#333,color:#000
    style MY fill:#d4edda,stroke:#333,color:#000
```

*   **Global Leaders (CSO/Director):** Have **Tenant-Level Roles** that grant visibility across all teams.
*   **Desk Heads:** Have the **Member** tenant role (no special power) but the **Surveillance Lead** team role. This restricts their power *strictly* to their assigned desk (Singapore vs Malaysia).

---

## 4. User Roster & Configuration

The `bank_surveillance_bulk_invite.csv` provisions **10 Users** ensuring 100% role coverage.

### A. Leadership (Global Scope)
| User | Email | **Team Role** | Scope | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Susan Martinez** | `cso@...` | - | **NULL** | *Manually assign 'Surveillance Chief' after invite* |
| **APAC Director** | `director.apac...` | - | **NULL** | *Manually assign 'Regional Director' after invite* |

> **Note:** All users are invited as **Member**. Use the Admin UI to assign special Tenant Roles like `Surveillance Chief`.

### B. Desk Operations (Restricted Scope)
| User | Email | Team Role | Scope |
| :--- | :--- | :--- | :--- |
| **SG Head** | `head.sg.surv@...` | `surveillance_lead` | **SG Team Only** |
| **MY Head** | `head.my.surv@...` | `surveillance_lead` | **MY Team Only** |
| **MY Analyst** | `analyst.my.wealth@...` | `surveillance_analyst` | **MY Team Only** |

### C. Separation of Duties (SoD)
*These users work in the "Special Investigations" team.*

| User | Email | Team Permission |
| :--- | :--- | :--- |
| **Maker** | `analyst.global.forensic@...` | Can **Create**, Cannot Approve |
| **Checker** | `checker.global.forensic@...` | Can **Approve**, Cannot Create |

---

### D. Auxiliary & Support Staff
| User | Email | Team Role | Scope |
| :--- | :--- | :--- | :--- |
| **SurvOps** | `surv.ops.apac@...` | `surveillance_ops` | **SG & MY Teams** |
| **MAS Liaison** | `liaison.sg.mas@...` | `compliance_officer` | **SG Team Only** |
| **Ext. Auditor** | `guest.auditor@...` | `guest_analyst` | **SG Team Only** |

---

## 5. Auxiliary Roles Mapping

Special configurations for non-business users.

### Surveillance Operations (`surv.ops.apac@...`)
*   **Mapping:** Appointed to both SG or/and MY teams.
*   **Invitation Tenant Role:** **Member**
*   **Function:** Monitoring data pipeline health, processing volumes, and failure statistics.
*   **Constraint:** Can **Manage Team Members** (for support access) and **Train Models** but strictly **No Access** to sensitive business data content (Comms, Investigations, Alerts). They focus on the **Data Ingestion Pipelines** dashboard.

### External Auditors (`guest.auditor@...` / `liaison.sg.mas@...`)
*   **Mapping:** `guest.auditor` is assigned `guest_analyst` role. `liaison.sg.mas` is `compliance_officer`.
*   **Invitation Tenant Role:** **Member** (for Liaison) or **Viewer** (for Guest).
*   **Function:** Regulatory review.
*   **Constraint:** "Least Privilege". They can see reports and case details but cannot see raw sensitive comms or PII unless explicitly authorized.

---

## 6. Permissions Matrix

### A. Surveillance Mission Operations (Business)

| Role | Comms | Investigations | Alerts | Subjects (Watchlist) | Reports | Analytics | AI Models |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Chief (CSO)** | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| **Director** | ✅ Full | ✅ Full | ✅ Full | ✅ Approve | ✅ Full | ✅ Full | 👁️ Read |
| **Lead (STL)** | 👁️ Read | ✅ Full | ✅ Full | ✅ Approve | ✅ Full | ✅ Full | 👁️ Read |
| **Analyst (SA)** | 👁️ Read | ➕ Create | 👁️ Read | ❌ | 👁️ Read | ❌ | ❌ |
| **Maker** | 👁️ Read | ➕ Create | 👁️ Read | ➕ Create | ❌ | ❌ | ❌ |
| **Checker** | ❌ | ✅ Approve | 👁️ Read | ✅ Approve | ❌ | ❌ | ❌ |

### B. Platform & Technical Support (Separation of Duties)

| Role | Users/Teams | Roles/RBAC | Settings | Data Pipelines | AI Models | Billing | Audit Logs |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Owner (IT)** | ✅ Full | ✅ Full | ✅ Full | ❌ | ❌ | ✅ Full | ✅ Full |
| **Admin (IT)** | ✅ Full | ✅ Full | ✅ Full | ❌ | ❌ | ❌ | ✅ Full |
| **SurvOps** | ✅ Manage | ❌ | ✅ Manage | ✅ Full | ✅ Full | ❌ | 👁️ Read |
| **Chief (CSO)** | 👁️ Read | ❌ | ❌ | ✅ Full | ✅ Full | ❌ | 👁️ Read |
| **Member** | 👁️ Read | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

*Legend: ✅ Full Access, 👁️ Read Only, ➕ Create/Update Only, ❌ No Access*

---

## 7. Configuration Architecture (Base + Overlay)

The RBAC seeding system uses a **Modular "Base + Overlay" Pattern** to keep core definitions clean while allowing domain-specific customizations.

### How it works
1.  **Core Layer (Universal):** The platform loads immutable base roles (`Owner`, `Admin`, `Member`) from the core system.
2.  **Domain Layer (Specific):** The use case loads its unique roles (e.g., `Surveillance Chief`) from `tenant_roles.yaml`.
3.  **Overlay Layer (Patching):** *Optional.* The use case can inject new permissions into existing Core roles without modifying the core files.

### Why use Overlays?
Instead of redefining the `Member` role from scratch (which breaks updates), we can "patch" it.

**Example (Not used in this demo):**
If we wanted every standard **Member** to view High Priority Alerts, we would create a `tenant_permissions.yaml` overlay:
```yaml
tenant_permissions:
  member:              # Target existing Core role
    - resource: alerts # Inject new resource access
      actions: [read]
```

*Note: This specific demo relies entirely on distinct roles defined in `tenant_roles.yaml` and does not currently use overlays, hence the "No tenant permission overlays to apply" message during seeding.*

---

## 8. Specifications: Bulk Invitation Logic

Details on how the `bank_surveillance_bulk_invite.csv` is processed by the system.

### A. CSV Format
The loader expects the following columns:
| Column | Description | Mandatory? |
| :--- | :--- | :--- |
| `email` | User's email address (Must match tenant domain). | **Yes** |
| `name` | Full name (e.g., "Susan Martinez"). | No |
| `team_name`| Name of the team to join.<br>**Strict Check:** Team **MUST exist** in the system. | **Yes** |
| `team_role`| **Team Role** (Context Role). Defines "What you do".<br>Values: `surveillance_lead`, `surveillance_analyst`, etc.<br>Default: `team_contributor` | **Yes** |

### B. Logic Rules
1.  **System Role Default:** All bulk invited users are automatically assigned the **Member** system role. To elevate someone to **Admin** or **Tenant Role** (e.g. `surveillance_chief`), you must edit them in the UI after invitation.
2.  **Team Assignment:**
3.  **Strict Validation:** The system **validates** that the team exists. If "New Ops Team" is not found in the DB, the row **FAILS**.
    *   *Pre-Requisite:* Admins must create Teams (and configure Regions) via API/UI **before** running the bulk invite.

### C. Multi-Team Assignment
*   **Limitation:** A user cannot be assigned to multiple teams (e.g., SG *and* MY) in a single CSV row.
*   **Workflow:**
    1.  Invite user to their **Primary Team** (e.g., SG) via CSV.
    2.  After they join, an Admin uses the **Team Members UI** to add them to secondary teams (e.g., MY).

---

## 9. FAQ

**Q: Why do we have two layers of roles (Tenant vs. Team)?**
This "2-Layer RBAC" model is crucial for enterprise banking:
1.  **Tenant Roles (The Badge):** Define *who you are* (e.g., Regional Director). These are broad, organization-wide badges.
2.  **Team Roles (The Job):** Define *what you do in a specific context* (e.g., Surveillance Lead for SG Desk).
*   *Benefit:* A "Member" (standard employee) can be a "Lead" in Singapore but have no access to Malaysia, enforcing **Chinese Walls**.

**Q: What is the difference between `owner` and `surveillance_chief`?**
*   **`owner` (IT Platform Role):** Has technical control (billing, inviting users) but **NO** access to sensitive surveillance data.
*   **`surveillance_chief` (Business Role):** Has full view of all investigations and alerts but cannot modify billing or delete the tenant.
*   *Benefit:* Enforces **Separation of Duties** (IT admins shouldn't see insider trading investigations).

**Q: What can auditors and compliance officers see?**
*   They can *create* nothing and *approve* nothing, only *audit* existing records.

**Q: Is the team structure structurally hierarchical (Nested Teams)?**
*   **Current State:** It is **Structurally Flat** but **Logically Hierarchical**. "SG Desk" and "APAC Hub" are sibling records in the database. Hierarchy is enforced by *who* is assigned *where* (e.g., Director gets "Tenant Role" visibility, Desk Head gets "Team Role" restriction).
*   **Future (Plugin Extension):** Yes! The `teams` table includes a `config_data` JSONB column. A future **"Hierarchy Plugin"** will use `config_data['parent_id']` to enable recursive permissions (e.g., "Grant access to Team X and all its children").

**Q: Why do we have `compliance_officer` in Team Roles if we have a Head of Compliance?**
*   **Head of Compliance (`head_compliance`):** A **Tenant Role** with global power. They oversee the entire bank.
*   **Compliance Liaison (`compliance_officer`):** A **Team Role** for local oversight. This corresponds to an officer physically sitting at the desk (e.g., "Singapore Desk Liaison"). They need access ONLY to that specific team's investigations, not the whole bank.

---

## 10. Technical Implementation: Policy Plugins
The system uses a **Plugin Architecture** to enforce specific compliance rules at runtime. These are Python checks that run *after* standard RBAC.

### A. Data Classification Plugin (Clearance)
*   **Mechanism:** `User.Role.clearance_level` vs `Resource.confidentiality_level`.
*   **Logic:**
    1.  User makes a request (e.g., `GET /investigations/123`).
    2.  Plugin fetches the user's **Tenant Role** from the DB (e.g., `surveillance_chief`).
    3.  Plugin reads the role's `clearance_level` integer (Runtime Column).
    4.  **Rule:** If `User.Clearance < Resource.Level`, access is **DENIED** even if RBAC says "Allow".
*   **Source:** `b2b.roles` table has a `clearance_level` column.

### B. Geographic Boundaries Plugin (Geo-Fencing)
*   **Mechanism:** `User.geographic_scopes` vs `Resource.data_region_id`.
*   **Logic:**
    1.  **Enrichment:** On login, the system calculates the user's `geographic_scopes`. This is typically derived from their **Team's configuration** (stored in `Team.config_data['region_id']`).
    2.  **Plugin Check:** The plugin inspects this enriched scope list.
    3.  **Rule:** If `Resource.data_region_id` is NOT in `User.geographic_scopes`, access is **DENIED**.
    *   *Bypass:* Global roles (CSO) are skipped via the `global_roles` config or `bypass_geographic_restrictions` context flag.

### C. Hierarchical Teams Plugin (Manager Access)
*   **Mechanism:** Recursive visibility.
*   **Logic:** Allows a "Regional Director" (Who is in the **APAC Hub** team) to see resources owned by **Child Teams** (SG Desk, MY Desk) without being a direct member of those desks.

---

## 11. Usage

```bash
# 1. Reset DB and seed RBAC with bank surveillance use case
make reset-db
make b2b-seed-roles USE_CASE=bank_surveillance

# 2. Create demo tenant
make b2b-invite f=scripts/b2b/use_cases/bank_surveillance/bank_surveillance_demo.json

# 3. Log in as CSO
# Email: cso@worldwidebank.com
```

**Fixed Tenant ID:** `b5e1fa40-89f4-50c2-a3f4-4c122000beef`
 