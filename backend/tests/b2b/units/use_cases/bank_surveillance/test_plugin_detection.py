"""
Unit Tests for Plugin Detection Service

Tests the detection strategies in isolation (no DB, mocked dependencies).
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestPluginDetectionStrategies:
    """Unit tests for region and classification detection strategies."""
    
    def test_lookup_sender_domain_exact_match(self):
        """Test sender domain lookup with exact @ prefix match."""
        from modules.domains.b2b.bank_surveillance.services.plugin_detection import PluginDetectionService
        
        # Create instance with mocked db
        service = PluginDetectionService(MagicMock(), uuid.uuid4())
        
        domain_map = {
            "@bank-apac.com": "uuid-apac",
            "@bank-emea.com": "uuid-emea",
        }
        
        result = service._lookup_sender_domain("trader@bank-apac.com", domain_map)
        assert result == "uuid-apac"
    
    def test_lookup_sender_domain_without_prefix(self):
        """Test sender domain lookup without @ prefix in map."""
        from modules.domains.b2b.bank_surveillance.services.plugin_detection import PluginDetectionService
        
        service = PluginDetectionService(MagicMock(), uuid.uuid4())
        
        domain_map = {
            "bank-apac.com": "uuid-apac",
        }
        
        result = service._lookup_sender_domain("trader@bank-apac.com", domain_map)
        assert result == "uuid-apac"
    
    def test_lookup_sender_domain_no_match(self):
        """Test sender domain lookup with no match returns None."""
        from modules.domains.b2b.bank_surveillance.services.plugin_detection import PluginDetectionService
        
        service = PluginDetectionService(MagicMock(), uuid.uuid4())
        
        domain_map = {
            "@bank-apac.com": "uuid-apac",
        }
        
        result = service._lookup_sender_domain("trader@other-bank.com", domain_map)
        assert result is None
    
    def test_lookup_sender_domain_empty_sender(self):
        """Test sender domain lookup with empty sender."""
        from modules.domains.b2b.bank_surveillance.services.plugin_detection import PluginDetectionService
        
        service = PluginDetectionService(MagicMock(), uuid.uuid4())
        
        result = service._lookup_sender_domain("", {"@bank.com": "uuid"})
        assert result is None
    
    def test_lookup_sender_domain_empty_map(self):
        """Test sender domain lookup with empty domain map."""
        from modules.domains.b2b.bank_surveillance.services.plugin_detection import PluginDetectionService
        
        service = PluginDetectionService(MagicMock(), uuid.uuid4())
        
        result = service._lookup_sender_domain("trader@bank.com", {})
        assert result is None
    
    def test_is_uuid_valid(self):
        """Test UUID validation with valid UUID."""
        from modules.domains.b2b.bank_surveillance.services.plugin_detection import PluginDetectionService
        
        valid_uuid = str(uuid.uuid4())
        assert PluginDetectionService._is_uuid(valid_uuid) is True
    
    def test_is_uuid_invalid(self):
        """Test UUID validation with invalid string."""
        from modules.domains.b2b.bank_surveillance.services.plugin_detection import PluginDetectionService
        
        assert PluginDetectionService._is_uuid("not-a-uuid") is False
        assert PluginDetectionService._is_uuid("internal") is False
        assert PluginDetectionService._is_uuid("") is False


class TestContentRulesMatching:
    """Unit tests for content-based classification matching."""
    
    def test_match_content_rules_keyword_match(self):
        """Test content rules matching with keyword pattern."""
        from modules.domains.b2b.bank_surveillance.services.plugin_detection import PluginDetectionService
        
        service = PluginDetectionService(MagicMock(), uuid.uuid4())
        
        # Create mock communication
        comm = MagicMock()
        comm.content = "This discussion involves MNPI about the merger."
        comm.subject = "Confidential"
        
        rules = [
            {"pattern": "MNPI|material non-public", "level_id": str(uuid.uuid4())}
        ]
        
        result = service._match_content_rules(comm, rules)
        assert result is not None
    
    def test_match_content_rules_no_match(self):
        """Test content rules matching with no pattern match."""
        from modules.domains.b2b.bank_surveillance.services.plugin_detection import PluginDetectionService
        
        service = PluginDetectionService(MagicMock(), uuid.uuid4())
        
        comm = MagicMock()
        comm.content = "Regular water-cooler chat."
        comm.subject = "Hello"
        
        rules = [
            {"pattern": "MNPI|material non-public", "level_id": str(uuid.uuid4())}
        ]
        
        result = service._match_content_rules(comm, rules)
        assert result is None
    
    def test_match_content_rules_invalid_regex(self):
        """Test content rules matching with invalid regex pattern."""
        from modules.domains.b2b.bank_surveillance.services.plugin_detection import PluginDetectionService
        
        service = PluginDetectionService(MagicMock(), uuid.uuid4())
        
        comm = MagicMock()
        comm.content = "Some content"
        comm.subject = "Subject"
        
        # Invalid regex pattern
        rules = [
            {"pattern": "[invalid(regex", "level_id": str(uuid.uuid4())}
        ]
        
        # Should not raise, just skip invalid pattern
        result = service._match_content_rules(comm, rules)
        assert result is None
    
    def test_match_content_rules_case_insensitive(self):
        """Test content rules matching is case insensitive."""
        from modules.domains.b2b.bank_surveillance.services.plugin_detection import PluginDetectionService
        
        service = PluginDetectionService(MagicMock(), uuid.uuid4())
        
        comm = MagicMock()
        comm.content = "This has mnpi information"  # lowercase
        comm.subject = ""
        
        test_uuid = str(uuid.uuid4())
        rules = [
            {"pattern": "MNPI", "level_id": test_uuid}  # uppercase pattern
        ]
        
        result = service._match_content_rules(comm, rules)
        assert result is not None
