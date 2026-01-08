"""
Tests for backend/core/funnel_mapper.py - FunnelMapper
"""
import pytest
from backend.core.funnel_mapper import FunnelMapper


class TestFunnelMapper:
    """Tests for FunnelMapper class"""
    
    def test_init(self):
        """Test FunnelMapper initialization"""
        mapper = FunnelMapper("https://example.com", max_steps=3)
        
        assert mapper.start_url == "https://example.com"
        assert mapper.max_steps == 3
        assert mapper.funnel_map == []
        assert mapper.visited_urls == set()
    
    def test_init_default_max_steps(self):
        """Test FunnelMapper with default max_steps"""
        mapper = FunnelMapper("https://example.com")
        
        assert mapper.max_steps == 5
    
    def test_analyze_tech_stack_wordpress(self):
        """Test WordPress detection"""
        mapper = FunnelMapper("https://example.com")
        
        html = '<html><link href="/wp-content/themes/style.css"></html>'
        result = mapper._analyze_tech_stack(html)
        
        assert result['platform'] == "WordPress"
    
    def test_analyze_tech_stack_shopify(self):
        """Test Shopify detection"""
        mapper = FunnelMapper("https://example.com")
        
        html = '<html><script src="//cdn.shopify.com/s/files/script.js"></script></html>'
        result = mapper._analyze_tech_stack(html)
        
        assert result['platform'] == "Shopify"
    
    def test_analyze_tech_stack_hotmart(self):
        """Test Hotmart detection"""
        mapper = FunnelMapper("https://example.com")
        
        html = '<html><!-- Hotmart checkout --></html>'
        result = mapper._analyze_tech_stack(html)
        
        assert result['platform'] == "Hotmart"
    
    def test_analyze_tech_stack_kiwify(self):
        """Test Kiwify detection"""
        mapper = FunnelMapper("https://example.com")
        
        html = '<html><script src="kiwify.js"></script></html>'
        result = mapper._analyze_tech_stack(html)
        
        assert result['platform'] == "Kiwify"
    
    def test_analyze_tech_stack_pixels_meta(self):
        """Test Meta Pixel detection"""
        mapper = FunnelMapper("https://example.com")
        
        html = '<html><script src="fbevents.js"></script></html>'
        result = mapper._analyze_tech_stack(html)
        
        assert "Meta Pixel" in result['pixels']
    
    def test_analyze_tech_stack_pixels_gtm(self):
        """Test GTM detection"""
        mapper = FunnelMapper("https://example.com")
        
        html = '<html><script src="googletagmanager.com/gtm.js"></script></html>'
        result = mapper._analyze_tech_stack(html)
        
        assert "GTM" in result['pixels']
    
    def test_analyze_tech_stack_video_vturb(self):
        """Test Vturb video player detection"""
        mapper = FunnelMapper("https://example.com")
        
        html = '<html><iframe src="vturb.com.br/video"></iframe></html>'
        result = mapper._analyze_tech_stack(html)
        
        assert result['video_player'] == "Vturb"
    
    def test_analyze_tech_stack_video_youtube(self):
        """Test YouTube detection"""
        mapper = FunnelMapper("https://example.com")
        
        html = '<html><iframe src="youtube.com/embed/abc"></iframe></html>'
        result = mapper._analyze_tech_stack(html)
        
        assert result['video_player'] == "YouTube"
    
    def test_analyze_tech_stack_elementor(self):
        """Test Elementor builder detection"""
        mapper = FunnelMapper("https://example.com")
        
        html = '<html><div class="elementor-widget"></div></html>'
        result = mapper._analyze_tech_stack(html)
        
        assert "Elementor" in result['builders']
    
    def test_extract_prices_brl(self):
        """Test BRL price extraction"""
        mapper = FunnelMapper("https://example.com")
        
        text = "O curso custa apenas R$ 97,00 ou 12x de R$ 9,90"
        result = mapper._extract_prices(text)
        
        assert len(result) > 0
        assert any("97" in p for p in result)
    
    def test_extract_prices_multiple(self):
        """Test multiple price extraction"""
        mapper = FunnelMapper("https://example.com")
        
        text = "De R$ 297,00 por apenas R$ 97,00"
        result = mapper._extract_prices(text)
        
        # Should find both prices but limit to 3
        assert len(result) <= 3
    
    def test_extract_prices_no_prices(self):
        """Test no prices found"""
        mapper = FunnelMapper("https://example.com")
        
        text = "This text has no prices at all"
        result = mapper._extract_prices(text)
        
        assert result == []
    
    def test_analyze_tech_stack_unknown(self):
        """Test unknown platform returns Custom/Unknown"""
        mapper = FunnelMapper("https://example.com")
        
        html = '<html><body>Simple page</body></html>'
        result = mapper._analyze_tech_stack(html)
        
        assert result['platform'] == "Custom/Unknown"
        assert result['video_player'] == "None"
        assert result['pixels'] == []
        assert result['builders'] == []
