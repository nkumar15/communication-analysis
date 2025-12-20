# Functional Specifications

This directory contains detailed functional requirements and acceptance criteria for the system's core features.

## Index

| ID | Feature | Product | File | Status |
|----|---------|---------|------|--------|
| **SPEC-01** | **Tenant Onboarding** | Shared | [`tenant-onboarding.md`](./tenant-onboarding.md) | ✅ Live |
| **SPEC-02** | **Authentication & Identity** | Shared | [`authentication.md`](./authentication.md) | ✅ Live |
| **SPEC-03** | **RBAC & Permissions** | B2B | [`rbac.md`](./rbac.md) | ✅ Live |
| **SPEC-04** | **User Management** | B2B | [`user.md`](./user.md) | ✅ Live |
| **SPEC-05** | **Domain Logic (Projects)** | Shared | [`project.md`](./project.md) | ✅ Live |
| **SPEC-06** | **Platform Administration** | Platform | *Planned* | ❌ Draft |
| **SPEC-07** | **Mobile App Support** | Shared | [`mobile.md`](./mobile.md) | ✅ Live |
| **SPEC-08** | **B2B Subscription & Billing** | B2B | [`b2b/subscription.md`](./b2b/subscription.md) | ✅ Live |

## Guiding Principles
To ensure the system works holistically across **Web** and **Mobile** apps:
1.  **API First**: All logic must reside in the API, not the client.
2.  **Channel Agnostic**: Features must be designed for both desktop (Web) and touch (Mobile) interfaces.
3.  **Deep Linking**: All email workflows (activation, invites) must support Universal Links / App Links.

- **Status**:
    - ✅ Live: Implemented and documented.
    - ⚠️ WIP: In progress.
    - ❌ Draft: Proposed but not written.
