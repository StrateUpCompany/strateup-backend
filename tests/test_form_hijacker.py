"""
Tests for backend/core/form_hijacker.py - FormHijacker
"""
import pytest
from backend.core.form_hijacker import FormHijacker


class TestFormHijacker:
    """Tests for FormHijacker class"""
    
    @pytest.fixture
    def hijacker(self):
        """Create a FormHijacker instance for testing"""
        return FormHijacker(project_id="test-123", api_url="http://localhost:8000")
    
    def test_init(self, hijacker):
        """Test FormHijacker initialization"""
        assert hijacker.project_id == "test-123"
        assert hijacker.capture_endpoint == "http://localhost:8000/projects/test-123/capture"
    
    def test_process_html_no_forms(self, hijacker):
        """Test processing HTML without forms returns unchanged"""
        html = "<html><body><p>No forms here</p></body></html>"
        result = hijacker.process_html(html)
        assert result == html
    
    def test_process_html_single_form(self, hijacker):
        """Test processing HTML with a single form"""
        html = '''
        <html>
            <body>
                <form action="https://original.com/submit" method="GET">
                    <input type="text" name="email">
                    <button type="submit">Submit</button>
                </form>
            </body>
        </html>
        '''
        result = hijacker.process_html(html)
        
        # Form action should be replaced
        assert 'action="http://localhost:8000/projects/test-123/capture"' in result
        # Method should be POST
        assert 'method="POST"' in result
        # Hidden field should be added
        assert '_original_action' in result
        assert 'https://original.com/submit' in result
    
    def test_process_html_multiple_forms(self, hijacker):
        """Test processing HTML with multiple forms"""
        html = '''
        <html>
            <body>
                <form action="/form1">
                    <input type="text" name="name">
                </form>
                <form action="/form2">
                    <input type="email" name="email">
                </form>
            </body>
        </html>
        '''
        result = hijacker.process_html(html)
        
        # Both forms should be hijacked
        assert result.count('action="http://localhost:8000/projects/test-123/capture"') == 2
        assert result.count('method="POST"') == 2
    
    def test_process_html_form_no_action(self, hijacker):
        """Test processing form without action attribute"""
        html = '''
        <html>
            <body>
                <form>
                    <input type="text" name="data">
                </form>
            </body>
        </html>
        '''
        result = hijacker.process_html(html)
        
        assert 'action="http://localhost:8000/projects/test-123/capture"' in result
        # Original action should be empty
        assert '_original_action' in result
    
    def test_process_html_preserves_other_elements(self, hijacker):
        """Test that non-form elements are preserved"""
        html = '''
        <html>
            <body>
                <h1>Header</h1>
                <form action="/test">
                    <input type="text">
                </form>
                <p>Footer text</p>
            </body>
        </html>
        '''
        result = hijacker.process_html(html)
        
        assert '<h1>Header</h1>' in result
        assert '<p>Footer text</p>' in result
    
    def test_process_html_invalid_html(self, hijacker):
        """Test processing invalid/malformed HTML"""
        html = "<not valid html at all"
        result = hijacker.process_html(html)
        
        # Should return original on error or handle gracefully
        assert result is not None
