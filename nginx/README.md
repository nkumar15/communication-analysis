# API Gateway Quick Reference

## Gateway URL
**http://localhost:8080**

## Routing

| Service | Direct Access (old) | Gateway Access (new) |
|---------|-------------------|-------------------|
| **B2B API** | `localhost:8000/api/b2b/*` | `localhost:8080/api/b2b/*` |
| **Platform API** | `localhost:8001/api/platform/*` | `localhost:8080/api/platform/*` |
| **B2C API** | `localhost:8002/api/b2c/*` | `localhost:8080/api/b2c/*` |
| **Domain API** | `localhost:8003/api/domain/*` | `localhost:8080/api/domain/*` |

## Special Endpoints

### Documentation (Swagger UI)
| Service | URL |
|---------|-----|
| **B2B API** | `http://localhost:8080/docs/b2b` |
| **Platform API** | `http://localhost:8080/docs/platform` |
| **B2C API** | `http://localhost:8080/docs/b2c` |
| **Domain API** | `http://localhost:8080/docs/domain` |

### Health Check
```bash
curl http://localhost:8080/health
# Response: healthy
```

### Gateway Info
```bash
curl http://localhost:8080/gateway/info
# Response: {"gateway":"nginx","version":"1.0","upstreams":["b2b","platform","b2c","domain"]}
```

## Usage

### Start Gateway
```bash
# Start all services including gateway
docker-compose up -d

# Or start gateway only
docker-compose up -d nginx
```

### View Gateway Logs
```bash
docker-compose logs -f nginx
```

### Test Routing
```bash
# Test B2B API through gateway
curl http://localhost:8080/api/b2b/health

# Test Platform API through gateway
curl http://localhost:8080/api/platform/health

# Test with authentication
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8080/api/b2b/projects
```

## Frontend Configuration

### Option 1: Use Gateway (Recommended)
Update `frontend/.env`:
```env
REACT_APP_API_URL=http://localhost:8080
REACT_APP_PLATFORM_API_URL=http://localhost:8080
```

Frontend makes requests to:
- `${API_URL}/api/b2b/*`
- `${API_URL}/api/platform/*`

### Option 2: Keep Direct Access
Keep existing configuration (both work simultaneously):
```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_PLATFORM_API_URL=http://localhost:8001
```

## Features

✅ **CORS** - Handled centrally in nginx  
✅ **Load Balancing** - Ready for multiple instances  
✅ **Logging** - All requests logged via nginx  
✅ **Health Checks** - Gateway health endpoint  
✅ **Production Parity** - Mirrors cloud setup  

## Troubleshooting

**Gateway not starting:**
```bash
# Check nginx configuration
docker-compose exec nginx nginx -t

# View logs
docker-compose logs nginx
```

**504 Gateway Timeout:**
- Check if microservices are running: `docker-compose ps`
- Increase timeout in nginx.conf (current: 300s for b2b)

**CORS errors:**
- Verify CORS headers in nginx.conf
- Check browser console for specific error

## Next Steps

1. ✅ Services work via gateway
2. ✅ Both gateway and direct access work
3. Update frontend to use gateway (optional)
4. Add rate limiting (future)
5. Add request logging to database (future)
