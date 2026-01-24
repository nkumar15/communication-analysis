"""
Unit Tests for Detection Service

Tests keyword/regex matching logic in isolation.
"""
import uuid
import pytest
from unittest.mock import MagicMock
from datetime import datetime


class TestDetectionMatching:
    """Unit tests for detection matching logic."""
    
    def test_match_control_keyword_match(self):
        """Test keyword matching in communication content."""
        from modules.domains.b2b.bank_surveillance.services.detection import DetectionService
        
        service = DetectionService(MagicMock(), uuid.uuid4())
        
        # Create mock communication
        comm = MagicMock()
        comm.content = "Need to shift the load to tomorrow's trading session"
        comm.subject = "Trading Strategy"
        
        # Create mock control with keyword detection
        control = MagicMock()
        control.detection_methods = [
            {"type": "keyword", "keywords": ["load shifting", "shift", "load"]}
        ]
        
        result = service._match_control(comm, control)
        
        assert result is not None
        assert result["match_type"] == "keyword"
        assert len(result["matched_keywords"]) > 0
    
    def test_match_control_no_match(self):
        """Test no match when keywords not in content."""
        from modules.domains.b2b.bank_surveillance.services.detection import DetectionService
        
        service = DetectionService(MagicMock(), uuid.uuid4())
        
        comm = MagicMock()
        comm.content = "Regular meeting notes from today's standup"
        comm.subject = "Meeting Notes"
        
        control = MagicMock()
        control.detection_methods = [
            {"type": "keyword", "keywords": ["insider", "confidential", "MNPI"]}
        ]
        
        result = service._match_control(comm, control)
        assert result is None
    
    def test_match_control_regex_match(self):
        """Test regex pattern matching."""
        from modules.domains.b2b.bank_surveillance.services.detection import DetectionService
        
        service = DetectionService(MagicMock(), uuid.uuid4())
        
        comm = MagicMock()
        comm.content = "The stock price will be $150.00 after the announcement"
        comm.subject = "Price Target"
        
        control = MagicMock()
        control.detection_methods = [
            {"type": "regex", "patterns": [r"\$\d+\.\d{2}"]}
        ]
        
        result = service._match_control(comm, control)
        
        assert result is not None
        assert result["match_type"] == "regex"
    
    def test_match_control_regex_no_match(self):
        """Test regex pattern with no match."""
        from modules.domains.b2b.bank_surveillance.services.detection import DetectionService
        
        service = DetectionService(MagicMock(), uuid.uuid4())
        
        comm = MagicMock()
        comm.content = "No price targets mentioned here"
        comm.subject = "General Discussion"
        
        control = MagicMock()
        control.detection_methods = [
            {"type": "regex", "patterns": [r"\$\d+\.\d{2}"]}
        ]
        
        result = service._match_control(comm, control)
        assert result is None
    
    def test_match_control_invalid_regex(self):
        """Test invalid regex pattern is handled gracefully."""
        from modules.domains.b2b.bank_surveillance.services.detection import DetectionService
        
        service = DetectionService(MagicMock(), uuid.uuid4())
        
        comm = MagicMock()
        comm.content = "Some content"
        comm.subject = "Subject"
        
        control = MagicMock()
        control.detection_methods = [
            {"type": "regex", "patterns": ["[invalid(regex"]}
        ]
        
        # Should not raise, just skip invalid pattern
        result = service._match_control(comm, control)
        assert result is None
    
    def test_match_control_empty_content(self):
        """Test matching with empty content."""
        from modules.domains.b2b.bank_surveillance.services.detection import DetectionService
        
        service = DetectionService(MagicMock(), uuid.uuid4())
        
        comm = MagicMock()
        comm.content = ""
        comm.subject = ""
        
        control = MagicMock()
        control.detection_methods = [
            {"type": "keyword", "keywords": ["test"]}
        ]
        
        result = service._match_control(comm, control)
        assert result is None
    
    def test_match_control_no_detection_methods(self):
        """Test control with no detection methods."""
        from modules.domains.b2b.bank_surveillance.services.detection import DetectionService
        
        service = DetectionService(MagicMock(), uuid.uuid4())
        
        comm = MagicMock()
        comm.content = "Some content with keywords"
        comm.subject = "Subject"
        
        control = MagicMock()
        control.detection_methods = []
        
        result = service._match_control(comm, control)
        assert result is None


class TestSnippetExtraction:
    """Unit tests for snippet extraction."""
    
    def test_extract_snippet_middle(self):
        """Test snippet extraction from middle of text."""
        from modules.domains.b2b.bank_surveillance.services.detection import DetectionService
        
        service = DetectionService(MagicMock(), uuid.uuid4())
        
        text = "A" * 200 + "TARGET" + "B" * 200
        snippet = service._extract_snippet(text, "TARGET", context_chars=50)
        
        assert "TARGET" in snippet
        assert snippet.startswith("...")
        assert snippet.endswith("...")
    
    def test_extract_snippet_start(self):
        """Test snippet extraction from start of text."""
        from modules.domains.b2b.bank_surveillance.services.detection import DetectionService
        
        service = DetectionService(MagicMock(), uuid.uuid4())
        
        text = "TARGET" + "A" * 200
        snippet = service._extract_snippet(text, "TARGET", context_chars=50)
        
        assert "TARGET" in snippet
        assert not snippet.startswith("...")
    
    def test_extract_snippet_end(self):
        """Test snippet extraction from end of text."""
        from modules.domains.b2b.bank_surveillance.services.detection import DetectionService
        
        service = DetectionService(MagicMock(), uuid.uuid4())
        
        text = "A" * 200 + "TARGET"
        snippet = service._extract_snippet(text, "TARGET", context_chars=50)
        
        assert "TARGET" in snippet
        assert not snippet.endswith("...")
    
    def test_extract_snippet_not_found(self):
        """Test snippet extraction when match not found."""
        from modules.domains.b2b.bank_surveillance.services.detection import DetectionService
        
        service = DetectionService(MagicMock(), uuid.uuid4())
        
        text = "Some text without the match"
        snippet = service._extract_snippet(text, "NOTFOUND", context_chars=50)
        
        assert snippet == ""
