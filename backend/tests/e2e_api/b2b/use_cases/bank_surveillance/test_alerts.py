
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from modules.domains.b2b.bank_surveillance.models.alert import Alert, AlertStatus, AlertSeverity, RiskType
from modules.domains.b2b.bank_surveillance.models.communication import Communication

# Use the b2b_test_setup fixture which creates a tenant and admin user
@pytest.mark.asyncio
async def test_api_list_alerts(api_client: AsyncClient, b2b_test_setup):
    setup = b2b_test_setup
    tenant_id = setup['tenant_id']
    headers = setup['headers']
    
    # 1. Create a dummy communication & alert in DB
    async with AsyncSession(setup['session'].bind) as db:
        comm = Communication(
            tenant_id=tenant_id,
            channel="email",
            sender="tracer@test.com",
            recipients=["target@test.com"],
            timestamp=uuid.uuid1().time, # simplified
            message_id=str(uuid.uuid4())
        )
        db.add(comm)
        await db.flush()
        
        alert = Alert(
            tenant_id=tenant_id,
            communication_id=comm.id,
            risk_type=RiskType.INSIDER_TRADING.value,
            severity=AlertSeverity.HIGH.value,
            status=AlertStatus.OPEN.value,
            description="Test Alert"
        )
        db.add(alert)
        await db.commit()
        alert_id = str(alert.id)

    # 2. Call API
    response = await api_client.get(
        "/api/b2b/domain/bank_surveillance/alerts/",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]['id'] == alert_id
    assert data[0]['risk_type'] == RiskType.INSIDER_TRADING.value

@pytest.mark.asyncio
async def test_api_update_alert_status(api_client: AsyncClient, b2b_test_setup):
    setup = b2b_test_setup
    tenant_id = setup['tenant_id']
    headers = setup['headers']
    
    # 1. Create alert
    async with AsyncSession(setup['session'].bind) as db:
        comm = Communication(
            tenant_id=tenant_id,
            channel="chat",
            sender="trader@test.com",
            recipients=[],
            timestamp=uuid.uuid1().time,
            message_id=str(uuid.uuid4())
        )
        db.add(comm)
        await db.flush()
        
        alert = Alert(
            tenant_id=tenant_id,
            communication_id=comm.id,
            risk_type=RiskType.OFF_CHANNEL.value,
            severity=AlertSeverity.MEDIUM.value,
            status=AlertStatus.OPEN.value
        )
        db.add(alert)
        await db.commit()
        alert_id = str(alert.id)

    # 2. Call Escalate endpoint
    response = await api_client.post(
        f"/api/b2b/domain/bank_surveillance/alerts/{alert_id}/escalate",
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()['status'] == AlertStatus.ESCALATED.value

    # 3. Call Close endpoint
    response = await api_client.post(
        f"/api/b2b/domain/bank_surveillance/alerts/{alert_id}/close",
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()['status'] == AlertStatus.CLOSED.value
