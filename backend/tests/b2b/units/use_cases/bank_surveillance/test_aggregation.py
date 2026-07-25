"""
Unit Tests for Aggregation Service

Tests incident severity calculation and grouping logic in isolation.
"""
import uuid
import pytest
from unittest.mock import MagicMock


class TestIncidentSeverityCalculation:
    """Unit tests for severity calculation logic."""
    
    def test_severity_low(self):
        """Test low severity calculation (<4 events)."""
        from modules.domains.b2b.bank_surveillance.models.incident import Incident, IncidentSeverity
        
        assert Incident.calculate_severity(1) == IncidentSeverity.LOW.value
        assert Incident.calculate_severity(2) == IncidentSeverity.LOW.value
        assert Incident.calculate_severity(3) == IncidentSeverity.LOW.value
    
    def test_severity_medium(self):
        """Test medium severity calculation (4-7 events)."""
        from modules.domains.b2b.bank_surveillance.models.incident import Incident, IncidentSeverity
        
        assert Incident.calculate_severity(4) == IncidentSeverity.MEDIUM.value
        assert Incident.calculate_severity(5) == IncidentSeverity.MEDIUM.value
        assert Incident.calculate_severity(7) == IncidentSeverity.MEDIUM.value
    
    def test_severity_high(self):
        """Test high severity calculation (8-15 events)."""
        from modules.domains.b2b.bank_surveillance.models.incident import Incident, IncidentSeverity
        
        assert Incident.calculate_severity(8) == IncidentSeverity.HIGH.value
        assert Incident.calculate_severity(10) == IncidentSeverity.HIGH.value
        assert Incident.calculate_severity(15) == IncidentSeverity.HIGH.value
    
    def test_severity_critical(self):
        """Test critical severity calculation (>=16 events)."""
        from modules.domains.b2b.bank_surveillance.models.incident import Incident, IncidentSeverity
        
        assert Incident.calculate_severity(16) == IncidentSeverity.CRITICAL.value
        assert Incident.calculate_severity(20) == IncidentSeverity.CRITICAL.value
        assert Incident.calculate_severity(100) == IncidentSeverity.CRITICAL.value


class TestAlertSeverityMapping:
    """Unit tests for alert severity mapping."""
    
    def test_map_severity_all_levels(self):
        """Test all severity level mappings."""
        from modules.domains.b2b.bank_surveillance.services.aggregation import AggregationService
        from modules.domains.b2b.bank_surveillance.models.incident import IncidentSeverity
        from modules.domains.b2b.bank_surveillance.models.alert import AlertSeverity
        
        service = AggregationService(MagicMock(), uuid.uuid4())
        
        assert service._map_severity(IncidentSeverity.LOW.value) == AlertSeverity.LOW.value
        assert service._map_severity(IncidentSeverity.MEDIUM.value) == AlertSeverity.MEDIUM.value
        assert service._map_severity(IncidentSeverity.HIGH.value) == AlertSeverity.HIGH.value
        assert service._map_severity(IncidentSeverity.CRITICAL.value) == AlertSeverity.CRITICAL.value
    
    def test_map_severity_unknown_default(self):
        """Test unknown severity defaults to MEDIUM."""
        from modules.domains.b2b.bank_surveillance.services.aggregation import AggregationService
        from modules.domains.b2b.bank_surveillance.models.alert import AlertSeverity
        
        service = AggregationService(MagicMock(), uuid.uuid4())
        
        assert service._map_severity("unknown") == AlertSeverity.MEDIUM.value
        assert service._map_severity("") == AlertSeverity.MEDIUM.value
