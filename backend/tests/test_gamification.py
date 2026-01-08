"""
Gamification Tests
LeadHunter AI - Testing gamification module

Tests for:
- XP system
- Levels
- State management
"""
import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.core.gamification import GamificationEngine


# =============================================================================
# GAMIFICATION ENGINE TESTS
# =============================================================================

class TestGamificationEngine:
    """Tests for GamificationEngine class."""
    
    def test_init_creates_default_data(self):
        """Should initialize with default data."""
        engine = GamificationEngine(data_path="test_gamification.json")
        
        state = engine.get_state()
        
        assert "xp" in state
        assert "level" in state
        assert state["level"] == 1
        
        # Cleanup
        if Path("test_gamification.json").exists():
            os.remove("test_gamification.json")
    
    def test_get_state(self):
        """Should return current state."""
        engine = GamificationEngine(data_path="test_state.json")
        
        state = engine.get_state()
        
        assert isinstance(state, dict)
        assert "xp" in state
        assert "level" in state
        assert "achievements" in state
        
        # Cleanup
        if Path("test_state.json").exists():
            os.remove("test_state.json")


# =============================================================================
# XP SYSTEM TESTS
# =============================================================================

class TestXPSystem:
    """Tests for XP points system."""
    
    def test_add_xp(self):
        """Should add XP points."""
        engine = GamificationEngine(data_path="test_xp.json")
        
        result = engine.add_xp(100, reason="test_action")
        
        assert result["xp"] == 100
        assert result["added"] == 100
        assert result["reason"] == "test_action"
        
        # Cleanup
        if Path("test_xp.json").exists():
            os.remove("test_xp.json")
    
    def test_add_xp_multiple(self):
        """Should accumulate XP."""
        engine = GamificationEngine(data_path="test_xp_multi.json")
        
        engine.add_xp(50)
        result = engine.add_xp(50)
        
        assert result["xp"] == 100
        
        # Cleanup
        if Path("test_xp_multi.json").exists():
            os.remove("test_xp_multi.json")


# =============================================================================
# LEVEL SYSTEM TESTS
# =============================================================================

class TestLevelSystem:
    """Tests for leveling system."""
    
    def test_level_up(self):
        """Should level up after enough XP."""
        engine = GamificationEngine(data_path="test_level.json")
        
        # Add enough XP to level up (500 XP per level)
        result = engine.add_xp(500)
        
        assert result["level"] >= 2
        assert result["leveled_up"] is True
        
        # Cleanup
        if Path("test_level.json").exists():
            os.remove("test_level.json")
    
    def test_no_level_up(self):
        """Should not level up with little XP."""
        engine = GamificationEngine(data_path="test_no_level.json")
        
        result = engine.add_xp(10)
        
        assert result["level"] == 1
        assert result["leveled_up"] is False
        
        # Cleanup
        if Path("test_no_level.json").exists():
            os.remove("test_no_level.json")


# =============================================================================
# PERSISTENCE TESTS
# =============================================================================

class TestPersistence:
    """Tests for data persistence."""
    
    def test_save_and_load(self):
        """Should persist data across instances."""
        # Create and add XP
        engine1 = GamificationEngine(data_path="test_persist.json")
        engine1.add_xp(200)
        
        # Create new instance
        engine2 = GamificationEngine(data_path="test_persist.json")
        state = engine2.get_state()
        
        assert state["xp"] == 200
        
        # Cleanup
        if Path("test_persist.json").exists():
            os.remove("test_persist.json")
    
    def test_default_data_structure(self):
        """Should have correct default structure."""
        engine = GamificationEngine(data_path="test_default.json")
        
        default = engine._default_data()
        
        assert default["xp"] == 0
        assert default["level"] == 1
        assert default["streak"] == 0
        assert default["achievements"] == []
        
        # Cleanup
        if Path("test_default.json").exists():
            os.remove("test_default.json")
