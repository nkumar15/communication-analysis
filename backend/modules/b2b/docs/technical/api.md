# B2B API Reference

**Base Path**: `/api/b2b`

## Authentication

| Method | Endpoint | Description | Permission |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/sync-user` | Link Firebase User to DB User | Public (Auth Token req) |
| `POST` | `/auth/mobile-login` | Exchange IDP Token for Custom Token | Public |
| `POST` | `/auth/sso-config` | Resolve Tenant SSO Config | Public |

## Users and Invitations

| Method | Endpoint | Description | Permission |
| :--- | :--- | :--- | :--- |
| `GET` | `/users` | List tenant users | `users:read` |
| `POST` | `/invitations` | Invite user (Single) | `users:invite` |
| `POST` | `/invitations/bulk` | Upload CSV for processing | `users:invite` |
| `GET` | `/invitations/bulk/{job_id}` | Get bulk job status | `users:invite` |
| `PUT` | `/users/{id}/role` | Update role | `users:write` |
| `DELETE` | `/users/{id}` | Remove user | `users:delete` |
| `GET` | `/roles` | List available roles | `roles:read` |

## Billing

| Method | Endpoint | Description | Permission |
| :--- | :--- | :--- | :--- |
| `GET` | `/billing/subscription` | Get status | `billing:read` |
| `POST` | `/billing/checkout` | Start Stripe flow | `billing:write` |
| `GET` | `/billing/invoices` | List invoices | `billing:read` |

## Dashboard

| Method | Endpoint | Description | Permission |
| :--- | :--- | :--- | :--- |
| `GET` | `/dashboard/stats` | Get Dynamic Stats | `dashboard:read` |

## Tenant Onboarding (Platform)

**Base Path**: `/api/platform`

| Method | Endpoint | Description | Permission |
| :--- | :--- | :--- | :--- |
| `POST` | `/tenants` | Create & Invite Tenant | `platform:admin` |
| `GET` | `/billing/profiles` | Search tenants | `platform:admin` |
| `POST` | `/billing/invoices/{id}/send` | Email invoice | `platform:admin` |

## Public Activation

| Method | Endpoint | Description | Permission |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/b2b/activate/validate/{token}` | Validate Token | Public |
| `POST` | `/api/b2b/activate` | Complete Activation | Public (Auth req) |
