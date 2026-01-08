"""
Session Manager Tests
LeadHunter AI - Testing session/history management

Tests for:
- Session creation
- Session updates
- History retrieval
"""
import pytest
import os
import tempfile
from pathlib import Path

from backend.core.session_manager import SessionManager


# =============================================================================
# SESSION MANAGER TESTS
# =============================================================================

class TestSessionManager:
    """Tests for SessionManager class."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for tests."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)
    
    def test_init(self, temp_db):
        """Should initialize and create database."""
        manager = SessionManager(db_path=temp_db)
        
        assert manager.db_path == temp_db
        assert os.path.exists(temp_db)
    
    def test_init_creates_table(self, temp_db):
        """Should create clones table."""
        manager = SessionManager(db_path=temp_db)
        
        import sqlite3
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clones'")
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None


# =============================================================================
# CREATE ENTRY TESTS
# =============================================================================

class TestCreateEntry:
    """Tests for session entry creation."""
    
    @pytest.fixture
    def manager(self):
        """Create manager with temp database."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        mgr = SessionManager(db_path=path)
        yield mgr
        if os.path.exists(path):
            os.unlink(path)
    
    def test_create_entry(self, manager):
        """Should create new entry."""
        entry_id = manager.create_entry(
            url="https://example.com",
            mode="full"
        )
        
        assert entry_id > 0
    
    def test_create_entry_returns_id(self, manager):
        """Should return unique IDs."""
        id1 = manager.create_entry("https://site1.com", "full")
        id2 = manager.create_entry("https://site2.com", "full")
        
        assert id1 != id2
        assert id1 > 0
        assert id2 > 0


# =============================================================================
# UPDATE ENTRY TESTS
# =============================================================================

class TestUpdateEntry:
    """Tests for session entry updates."""
    
    @pytest.fixture
    def manager(self):
        """Create manager with temp database."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        mgr = SessionManager(db_path=path)
        yield mgr
        if os.path.exists(path):
            os.unlink(path)
    
    def test_update_status(self, manager):
        """Should update entry status."""
        entry_id = manager.create_entry("https://example.com", "full")
        
        manager.update_entry(entry_id, status="COMPLETED")
        
        entry = manager.get_by_id(entry_id)
        assert entry["status"] == "COMPLETED"
    
    def test_update_with_path(self, manager):
        """Should update entry with local path."""
        entry_id = manager.create_entry("https://example.com", "full")
        
        manager.update_entry(entry_id, status="COMPLETED", local_path="/tmp/clone")
        
        entry = manager.get_by_id(entry_id)
        assert entry["local_path"] == "/tmp/clone"
    
    def test_update_with_error(self, manager):
        """Should update entry with error message."""
        entry_id = manager.create_entry("https://example.com", "full")
        
        manager.update_entry(entry_id, status="FAILED", error="Connection timeout")
        
        entry = manager.get_by_id(entry_id)
        assert entry["status"] == "FAILED"
        assert "timeout" in entry["error_msg"]


# =============================================================================
# GET HISTORY TESTS
# =============================================================================

class TestGetHistory:
    """Tests for history retrieval."""
    
    @pytest.fixture
    def manager(self):
        """Create manager with temp database."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        mgr = SessionManager(db_path=path)
        yield mgr
        if os.path.exists(path):
            os.unlink(path)
    
    def test_get_history_empty(self, manager):
        """Should return empty list when no entries."""
        history = manager.get_history()
        
        assert isinstance(history, list)
        assert len(history) == 0
    
    def test_get_history_with_entries(self, manager):
        """Should return entries."""
        manager.create_entry("https://site1.com", "full")
        manager.create_entry("https://site2.com", "full")
        
        history = manager.get_history()
        
        assert len(history) == 2
    
    def test_get_history_limit(self, manager):
        """Should respect limit parameter."""
        for i in range(5):
            manager.create_entry(f"https://site{i}.com", "full")
        
        history = manager.get_history(limit=3)
        
        assert len(history) == 3
    
    def test_get_history_order(self, manager):
        """Should return newest first (based on count)."""
        manager.create_entry("https://first.com", "full")
        manager.create_entry("https://second.com", "full")
        
        history = manager.get_history()
        
        # Should have 2 entries
        assert len(history) == 2
        # All entries should have ids
        assert all(h.get("id") for h in history)


# =============================================================================
# GET BY ID TESTS
# =============================================================================

class TestGetById:
    """Tests for get by ID."""
    
    @pytest.fixture
    def manager(self):
        """Create manager with temp database."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        mgr = SessionManager(db_path=path)
        yield mgr
        if os.path.exists(path):
            os.unlink(path)
    
    def test_get_by_id_existing(self, manager):
        """Should get existing entry."""
        entry_id = manager.create_entry("https://example.com", "full")
        
        entry = manager.get_by_id(entry_id)
        
        assert entry is not None
        assert entry["url"] == "https://example.com"
        assert entry["mode"] == "full"
    
    def test_get_by_id_nonexistent(self, manager):
        """Should return None for nonexistent ID."""
        entry = manager.get_by_id(9999)
        
        assert entry is None
