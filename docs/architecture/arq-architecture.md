# Where Email Code Runs - ARQ Architecture

## Answer: Email Code Runs in the ARQ Worker Container

```
┌──────────────────────────────────────────────────────────────────┐
│                        YOUR REQUEST FLOW                          │
└──────────────────────────────────────────────────────────────────┘

1. USER UPLOADS CSV
   ↓
   
2. NGINX (port 8080)
   ↓
   
3. B2B-API Container (port 8000)
   - Receives upload
   - Parses CSV
   - Validates rows
   - Creates invitation records in DB
   - **Commits to database**
   - Enqueues task to Redis: "send_bulk_invitation_emails"
   - Returns response immediately ✅
   
   Code Location: backend/services/b2b/routers/invitations.py
   ↓
   
4. REDIS Container (port 6379)
   - Stores task in queue
   - Task: {name: "send_bulk_invitation_emails", args: [invitation_ids]}
   
   ↓
   
5. ARQ-WORKER Container (separate container!)
   - Picks up task from Redis queue
   - **Creates its OWN database session**
   - Fetches invitation records
   - **SENDS EMAILS HERE** ← EMAIL CODE RUNS HERE!
   - Updates email_sent_at timestamp
   - Commits changes
   - Task complete
   
   Code Location: backend/core/tasks/worker.py
```

## Container Details

### b2b-api Container
- **Purpose**: Handle HTTP requests
- **Runs**: FastAPI application
- **Port**: 8000
- **Does**: 
  - Accept CSV upload
  - Validate data
  - Create DB records
  - **Enqueue tasks** (puts job in Redis)
  - Return response

### arq-worker Container  
- **Purpose**: Process background tasks
- **Runs**: ARQ worker process
- **Port**: None (not a web server)
- **Does**:
  - Watch Redis for new tasks
  - **Execute email sending** ← YOUR EMAIL CODE RUNS HERE
  - Execute audit log persistence
  - Execute any other async tasks
  - Has its own DB connection pool

### redis Container
- **Purpose**: Message broker/queue
- **Runs**: Redis server
- **Port**: 6379
- **Does**:
  - Store task queue
  - Enable communication between b2b-api and arq-worker

## File Structure

```
backend/
├── services/b2b/
│   └── routers/
│       └── invitations.py          # Enqueues tasks (runs in b2b-api)
│
└── core/
    ├── tasks/
    │   ├── worker.py                # Task definitions (runs in arq-worker)
    │   │   ├── send_invitation_email()        ← EMAIL CODE HERE!
    │   │   ├── send_bulk_invitation_emails()  ← EMAIL CODE HERE!
    │   │   └── persist_audit_log()
    │   │
    │   ├── queue.py                 # Queue helpers (shared)
    │   └── config.py                # Redis settings (shared)
    │
    └── email/
        └── service.py               # SMTP logic (imported by worker)
```

## Key Points

### ✅ **Where Email Sending Happens:**
**ARQ Worker Container** (`arq-worker` service in docker-compose)

### ✅ **Database Session:**
Worker creates its **OWN session** - no lock issues!

```python
# In worker.py
async def send_bulk_invitation_emails(ctx, invitation_ids, tenant_id):
    async with AsyncSessionLocal() as db:  # NEW session!
        # Fetch data
        # Send emails
        # Update status
        await db.commit()
```

### ✅ **Process Isolation:**
- **b2b-api**: Web requests, fast response
- **arq-worker**: CPU-intensive email sending
- **redis**: Communication bridge

## Starting the Services

```bash
# Start all services
docker-compose up

# Services that start:
# - postgres (database)
# - redis (message queue)
# - b2b-api (web server) - handles requests
# - arq-worker (background) - sends emails
# - platform-api, b2c-api, domain-api (other services)
# - nginx (gateway)
# - frontend (UI)
```

## Scaling

Need more email throughput? Scale the worker:

```bash
# Scale to 3 workers
docker-compose up --scale arq-worker=3
```

All 3 workers will:
- Share the same Redis queue
- Process tasks in parallel
- Have their own DB connections

## Monitoring Worker

```bash
# View worker logs
docker-compose logs -f arq-worker

# Output:
# arq-worker | INFO: Worker started
# arq-worker | INFO: Processing send_bulk_invitation_emails
# arq-worker | INFO: Sent email to alice@acme.com  ← EMAIL SENT HERE
# arq-worker | INFO: Sent email to bob@acme.com
# arq-worker | INFO: Task complete
```

## Summary

**Question**: Where does email code run?

**Answer**: In the **`arq-worker` container**, which is a separate Docker container running the ARQ worker process. It:
1. Monitors Redis for new tasks
2. Executes the email sending functions
3. Has its own database session (no locks!)
4. Runs independently from the API server

The API just says "send these emails later" by putting a job in Redis. The worker picks it up and actually sends them.
