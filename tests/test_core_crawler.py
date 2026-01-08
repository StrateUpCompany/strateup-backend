"""
Tests for backend/core/crawler.py - ClonagemThread
"""
import pytest
from unittest.mock import MagicMock, patch


class TestClonagemThread:
    """Tests for ClonagemThread wrapper class"""
    
    @patch('backend.core.crawler.CloneEngine')
    def test_init_creates_engine(self, MockCloneEngine):
        """Test that ClonagemThread creates a CloneEngine instance"""
        from backend.core.crawler import ClonagemThread
        
        url = "https://example.com"
        opcoes = {'pasta_destino': '/tmp/test'}
        project_id = "test-project-123"
        
        thread = ClonagemThread(url, opcoes, project_id)
        
        MockCloneEngine.assert_called_once_with(url, opcoes, project_id)
        assert thread.daemon is True
    
    @patch('backend.core.crawler.CloneEngine')
    def test_init_with_defaults(self, MockCloneEngine):
        """Test ClonagemThread with default parameters"""
        from backend.core.crawler import ClonagemThread
        
        thread = ClonagemThread("https://example.com")
        
        MockCloneEngine.assert_called_once_with("https://example.com", None, None)
    
    @patch('backend.core.crawler.CloneEngine')
    @patch('backend.core.crawler.EventBus')
    def test_run_executes_engine(self, MockEventBus, MockCloneEngine):
        """Test that run() calls engine.run()"""
        from backend.core.crawler import ClonagemThread
        
        mock_engine = MagicMock()
        MockCloneEngine.return_value = mock_engine
        
        thread = ClonagemThread("https://example.com")
        thread.run()
        
        mock_engine.run.assert_called_once()
    
    @patch('backend.core.crawler.CloneEngine')
    @patch('backend.core.crawler.EventBus')
    def test_run_emits_error_on_exception(self, MockEventBus, MockCloneEngine):
        """Test that run() emits error event on exception"""
        from backend.core.crawler import ClonagemThread
        
        mock_engine = MagicMock()
        mock_engine.run.side_effect = Exception("Test error")
        MockCloneEngine.return_value = mock_engine
        
        thread = ClonagemThread("https://example.com")
        thread.run()
        
        MockEventBus.emit.assert_called_with("error", "Test error")
    
    @patch('backend.core.crawler.CloneEngine')
    def test_stop_calls_engine_stop(self, MockCloneEngine):
        """Test that stop() calls engine.stop()"""
        from backend.core.crawler import ClonagemThread
        
        mock_engine = MagicMock()
        MockCloneEngine.return_value = mock_engine
        
        thread = ClonagemThread("https://example.com")
        thread.stop()
        
        mock_engine.stop.assert_called_once()
