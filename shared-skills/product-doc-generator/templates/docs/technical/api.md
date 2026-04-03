# API Reference

**Base Path**: `/api/[module]/[feature]`

## [Resource 1]

| Method | Path | Description | Permission |
|--------|------|-------------|------------|
| `GET` | `/` | List items | `[scope]:read` |
| `POST` | `/` | Create item | `[scope]:write` |
| `GET` | `/{id}` | Get item | `[scope]:read` |
| `PUT` | `/{id}` | Update item | `[scope]:write` |
| `DELETE` | `/{id}` | Delete item | `[scope]:delete` |

### Request/Response Examples

#### Create Item
```json
// POST /api/[module]/[feature]
{
  "name": "Example",
  "description": "..."
}
```

#### Response
```json
{
  "id": "uuid",
  "name": "Example",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

## [Resource 2]

*(Repeat structure)*

---

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Validation error |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not found |
