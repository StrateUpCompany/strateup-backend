import pytest
import os
from unittest.mock import MagicMock, patch
from bs4 import BeautifulSoup
from backend.core.engine import CloneEngine

# Mock config
@pytest.fixture
def mock_engine(tmp_path):
    engine = CloneEngine("http://example.com", options={'pasta_destino': str(tmp_path)})
    engine.session_manager = MagicMock()
    return engine

@pytest.fixture
def mock_pastas(tmp_path):
    return {
        'main': str(tmp_path),
        'images': str(tmp_path / 'images'),
        'css': str(tmp_path / 'css'),
        'js': str(tmp_path / 'js')
    }

def test_srcset_parsing(mock_engine, mock_pastas):
    """Test if srcset attributes are correctly parsed and urls extracted"""
    os.makedirs(mock_pastas['images'], exist_ok=True)
    
    html = """
    <html>
        <img src="img1.jpg" srcset="img1-1x.jpg 1x, img1-2x.jpg 2x">
        <source srcset="source1.jpg">
    </html>
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"fake_image_content"
        
        mock_engine._download_resources(soup, mock_pastas)
        
        # Verify img srcset was modified
        img = soup.find('img')
        assert "images/img1-1x.jpg" in img['srcset'] # Filename might vary but path structure should be relative
        
def test_background_image_parsing(mock_engine, mock_pastas):
    """Test inline style background-image extraction"""
    os.makedirs(mock_pastas['images'], exist_ok=True)
    
    html = """
    <div style="background-image: url('bg.png'); color: red;"></div>
    <div style="background: url(no-quote.jpg)"></div>
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"fake_bg_content"
        
        mock_engine._download_resources(soup, mock_pastas)
        
        divs = soup.find_all('div')
        assert "url('images/bg.png')" in divs[0]['style'] or "url('images/" in divs[0]['style']
