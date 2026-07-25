"""
Service Tests for Detection Service

Tests detection logic with real DB session but mocked controls.
"""
import uuid
import pytest
import pytest_asyncio
from datetime import datetime

from tests.conftest import create_test_tenant, set_tenant_context


class TestDetectionService:
    """Service-level tests for detection with DB."""
    
    @pytest.mark.asyncio
    async def test_analyze_unprocessed_no_controls(self, db_session, b2b_test_setup):
        """Test detection when no controls exist."""
        from modules.domains.b2b.bank_surveillance.services.detection import DetectionService
        
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        service = DetectionService(session, tenant_id)
        events_created = await service.analyze_unprocessed(limit=10)
        
        # No controls = no events
        assert events_created == 0
    
    @pytest.mark.asyncio
    async def test_analyze_unprocessed_no_communications(self, db_session, b2b_test_setup):
        """Test detection when no communications exist."""
        from modules.domains.b2b.bank_surveillance.services.detection import DetectionService
        from modules.domains.b2b.bank_surveillance.models import SurveillanceControl
        
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        # Create a control
        control = SurveillanceControl(
            tenant_id=tenant_id,
            risk_typology="Market Manipulation",
            risk_indicator="Load Shifting",
            detection_methods=[{"type": "keyword", "keywords": ["shift", "load"]}],
            status="Active"
        )
        session.add(control)
        await session.commit()
        
        service = DetectionService(session, tenant_id)
        events_created = await service.analyze_unprocessed(limit=10)
        
        # No communications = no events
        assert events_created == 0
    
    @pytest.mark.asyncio
    async def test_analyze_unprocessed_creates_event(self, db_session, b2b_test_setup):
        """Test detection creates RiskEvent when match found."""
        from modules.domains.b2b.bank_surveillance.services.detection import DetectionService
        from modules.domains.b2b.bank_surveillance.models import (
            SurveillanceControl, 
            Communication, 
            RiskEvent
        )
        from sqlalchemy import select
        
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        # Create a control
        control = SurveillanceControl(
            tenant_id=tenant_id,
            risk_typology="Market Manipulation",
            risk_indicator="Load Shifting",
            detection_methods=[{"type": "keyword", "keywords": ["shift load", "shifting"]}],
            status="Active"
        )
        session.add(control)
        
        # Create a communication with matching content
        comm = Communication(
            tenant_id=tenant_id,
            channel="email",
            sender="trader@bank.com",
            recipients=["counterparty@other.com"],
            subject="Trading Strategy",
            content="We need to shift load to tomorrow.",
            timestamp=datetime.utcnow(),
            analyzed=False
        )
        session.add(comm)
        await session.commit()
        
        # Run detection
        service = DetectionService(session, tenant_id)
        events_created = await service.analyze_unprocessed(limit=10)
        
        # Should create at least one event
        assert events_created >= 1
        
        # Verify communication is marked as analyzed
        result = await session.execute(
            select(Communication).where(Communication.id == comm.id)
        )
        updated_comm = result.scalar_one()
        assert updated_comm.analyzed is True
        
        # Verify RiskEvent exists
        event_result = await session.execute(
            select(RiskEvent).where(RiskEvent.communication_id == comm.id)
        )
        event = event_result.scalar_one_or_none()
        assert event is not None
        assert event.control_id == control.id
        assert event.match_type == "keyword"
    
    @pytest.mark.asyncio
    async def test_analyze_unprocessed_respects_limit(self, db_session, b2b_test_setup):
        """Test detection respects limit parameter."""
        from modules.domains.b2b.bank_surveillance.services.detection import DetectionService
        from modules.domains.b2b.bank_surveillance.models import Communication, SurveillanceControl
        
        setup = b2b_test_setup
        tenant_id = setup["tenant_id"]
        session = setup["session"]
        
        # Create a control (required for detection to run)
        control = SurveillanceControl(
            tenant_id=tenant_id,
            risk_typology="Test",
            risk_indicator="Test Indicator",
            detection_methods=[{"type": "keyword", "keywords": ["nonexistent_keyword_xyz"]}],
            status="Active"
        )
        session.add(control)
        
        # Create multiple communications
        for i in range(5):
            comm = Communication(
                tenant_id=tenant_id,
                channel="email",
                sender=f"sender{i}@bank.com",
                recipients=["recipient@bank.com"],
                content="Regular content without matches",
                timestamp=datetime.utcnow(),
                analyzed=False
            )
            session.add(comm)
        await session.commit()
        
        # Run with limit of 2
        service = DetectionService(session, tenant_id)
        await service.analyze_unprocessed(limit=2)
        await session.commit()  # Commit the analyzed flag changes
        
        # Should only process 2 (even if no matches)
        from sqlalchemy import select, func
        count_result = await session.execute(
            select(func.count()).select_from(Communication).where(
                Communication.tenant_id == tenant_id,
                Communication.analyzed == True
            )
        )
        analyzed_count = count_result.scalar()
        assert analyzed_count == 2

