"""
Service Tests for Aggregation Service

Tests aggregation logic with real DB session.
"""
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, date


class TestAggregationService:
    """Service-level tests for aggregation with DB."""
    
    @pytest.mark.asyncio
    async def test_aggregate_events_no_events(self, db_session, b2b_test_setup):
        """Test aggregation when no risk events exist."""
        from modules.domains.b2b.bank_surveillance.services.aggregation import AggregationService
        
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        service = AggregationService(session, tenant_id)
        incidents_created, events_processed = await service.aggregate_events()
        
        assert incidents_created == 0
        assert events_processed == 0
    
    @pytest.mark.asyncio
    async def test_aggregate_events_creates_incident(self, db_session, b2b_test_setup):
        """Test aggregation creates incident from risk events."""
        from modules.domains.b2b.bank_surveillance.services.aggregation import AggregationService
        from modules.domains.b2b.bank_surveillance.models import (
            SurveillanceControl,
            Communication,
            RiskEvent,
            Incident
        )
        from sqlalchemy import select
        
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        # Create control
        control = SurveillanceControl(
            tenant_id=tenant_id,
            risk_typology="Market Manipulation",
            risk_indicator="Load Shifting",
            detection_methods=[],
            status="Active"
        )
        session.add(control)
        await session.flush()
        
        # Create 3 communications to generate 3 events
        today = date.today()
        for i in range(3):
            comm = Communication(
                tenant_id=tenant_id,
                channel="email",
                sender="trader@bank.com",
                recipients=["recipient@bank.com"],
                content=f"Content {i}",
                timestamp=datetime.utcnow(),
                analyzed=True
            )
            session.add(comm)
            await session.flush()
            
            event = RiskEvent(
                tenant_id=tenant_id,
                communication_id=comm.id,
                control_id=control.id,
                sender="trader@bank.com",
                event_date=today,
                match_type="keyword",
                matched_keywords=["load"],
                match_score=0.8
            )
            session.add(event)
        await session.commit()
        
        # Run aggregation
        service = AggregationService(session, tenant_id)
        incidents_created, events_processed = await service.aggregate_events()
        
        assert incidents_created == 1
        assert events_processed == 3
        
        # Verify incident created
        result = await session.execute(
            select(Incident).where(Incident.tenant_id == tenant_id)
        )
        incident = result.scalar_one()
        assert incident.sender == "trader@bank.com"
        assert incident.event_count == 3
        assert incident.severity == "low"
    
    @pytest.mark.asyncio
    async def test_aggregate_events_groups_by_sender_date_control(self, db_session, b2b_test_setup):
        """Test aggregation groups events by sender, date, and control."""
        from modules.domains.b2b.bank_surveillance.services.aggregation import AggregationService
        from modules.domains.b2b.bank_surveillance.models import (
            SurveillanceControl,
            Communication,
            RiskEvent,
            Incident
        )
        from sqlalchemy import select, func
        
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        # Create 2 controls
        control1 = SurveillanceControl(
            tenant_id=tenant_id,
            risk_typology="Type1",
            risk_indicator="Indicator1",
            detection_methods=[],
            status="Active"
        )
        control2 = SurveillanceControl(
            tenant_id=tenant_id,
            risk_typology="Type2",
            risk_indicator="Indicator2",
            detection_methods=[],
            status="Active"
        )
        session.add_all([control1, control2])
        await session.flush()
        
        today = date.today()
        
        # Helper to create comm and event
        async def create_event(control_id, sender):
            comm = Communication(
                tenant_id=tenant_id,
                channel="email",
                sender=sender,
                recipients=["recipient@bank.com"],
                content="Content",
                timestamp=datetime.utcnow(),
                analyzed=True
            )
            session.add(comm)
            await session.flush()
            
            session.add(RiskEvent(
                tenant_id=tenant_id,
                communication_id=comm.id,
                control_id=control_id,
                sender=sender,
                event_date=today,
                match_type="keyword",
                matched_keywords=[],
                match_score=0.5
            ))

        # Group 1: trader@bank.com, today, control1 (2 events)
        await create_event(control1.id, "trader@bank.com")
        await create_event(control1.id, "trader@bank.com")
        
        # Group 2: trader@bank.com, today, control2 (1 event)
        await create_event(control2.id, "trader@bank.com")
        
        # Group 3: other@bank.com, today, control1 (1 event)
        await create_event(control1.id, "other@bank.com")
        
        await session.commit()
        
        # Run aggregation
        service = AggregationService(session, tenant_id)
        incidents_created, events_processed = await service.aggregate_events()
        
        # Should create 3 incidents (3 unique groupings)
        assert incidents_created == 3
        assert events_processed == 4
    
    @pytest.mark.asyncio
    async def test_generate_alerts_creates_alert(self, db_session, b2b_test_setup):
        """Test alert generation from incidents."""
        from modules.domains.b2b.bank_surveillance.services.aggregation import AggregationService
        from modules.domains.b2b.bank_surveillance.models import (
            SurveillanceControl,
            Incident,
            Alert
        )
        from sqlalchemy import select
        
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        # Create control
        control = SurveillanceControl(
            tenant_id=tenant_id,
            risk_typology="Market Manipulation",
            risk_indicator="Load Shifting",
            detection_methods=[],
            status="Active"
        )
        session.add(control)
        await session.flush()
        
        # Create incident without alert
        incident = Incident(
            tenant_id=tenant_id,
            control_id=control.id,
            sender="trader@bank.com",
            incident_date=date.today(),
            event_count=5,
            severity="medium"
        )
        session.add(incident)
        await session.commit()
        
        # Generate alerts
        service = AggregationService(session, tenant_id)
        alerts_created = await service.generate_alerts()
        
        assert alerts_created == 1
        
        # Verify alert
        result = await session.execute(
            select(Alert).where(Alert.tenant_id == tenant_id)
        )
        alert = result.scalar_one()
        assert "trader@bank.com" in alert.subject
        assert "Load Shifting" in alert.subject
        assert alert.severity == "medium"

