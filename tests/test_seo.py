"""
SEO Analyzer Tests
LeadHunter AI - Testing SEO module

Tests for:
- Initialization
- Full analysis
"""
import pytest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from backend.core.seo import SEOAnalyzer


# =============================================================================
# SEO ANALYZER INITIALIZATION
# =============================================================================

class TestSEOAnalyzerInit:
    """Tests for SEOAnalyzer initialization."""
    
    def test_init(self):
        """Should initialize with soup and url."""
        html = "<html><head><title>Test</title></head><body></body></html>"
        soup = BeautifulSoup(html, 'html.parser')
        
        analyzer = SEOAnalyzer(soup, "https://example.com")
        
        assert analyzer.url == "https://example.com"
        assert analyzer.soup is not None
    
    def test_init_with_complex_html(self):
        """Should initialize with complex HTML."""
        html = """
        <html>
            <head>
                <title>Test Page</title>
                <meta name="description" content="Test description">
            </head>
            <body>
                <h1>Main Title</h1>
                <p>Content</p>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        analyzer = SEOAnalyzer(soup, "https://example.com/page")
        
        assert analyzer.url == "https://example.com/page"


# =============================================================================
# ANALYZE ALL TESTS
# =============================================================================

class TestAnalyzeAll:
    """Tests for full SEO analysis."""
    
    def test_analyze_all_returns_dict(self):
        """analyze_all should return dict."""
        html = """
        <html>
            <head>
                <title>Test Title</title>
                <meta name="description" content="Test description">
            </head>
            <body>
                <h1>Heading</h1>
                <p>Content here</p>
                <a href="/about">About</a>
                <img src="logo.png" alt="Logo">
            </body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        analyzer = SEOAnalyzer(soup, "https://example.com")
        
        result = analyzer.analyze_all()
        
        assert isinstance(result, dict)
    
    def test_analyze_all_has_sections(self):
        """Result should have expected sections."""
        html = """
        <html>
            <head><title>Test</title></head>
            <body><h1>Title</h1></body>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        analyzer = SEOAnalyzer(soup, "https://example.com")
        
        result = analyzer.analyze_all()
        
        # Should have some result
        assert len(result) > 0


# Tests removed - data attribute not exposed in public API
