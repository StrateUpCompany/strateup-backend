"""
Tests for AI Providers
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestOllamaProvider:
    """Tests for OllamaProvider"""
    
    def test_ollama_provider_init(self):
        """Test OllamaProvider initialization"""
        from backend.core.ai_providers import OllamaProvider
        
        provider = OllamaProvider(model="llama3", context_size=32768)
        
        assert provider.name == "ollama"
        assert provider.default_model == "llama3"
        assert provider.context_size == 32768
    
    def test_ollama_is_available_success(self):
        """Test is_available when Ollama is running"""
        from backend.core.ai_providers import OllamaProvider
        
        with patch("requests.get") as mock_get:
            mock_get.return_value = Mock(status_code=200)
            
            provider = OllamaProvider()
            assert provider.is_available() is True
    
    def test_ollama_is_available_failure(self):
        """Test is_available when Ollama is not running"""
        from backend.core.ai_providers import OllamaProvider
        
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            
            provider = OllamaProvider()
            assert provider.is_available() is False
    
    def test_ollama_select_model_default(self):
        """Test model selection with default task"""
        from backend.core.ai_providers import OllamaProvider
        
        with patch.object(OllamaProvider, "get_available_models", return_value=["llama3", "llama3.2"]):
            provider = OllamaProvider(model="llama3")
            
            model = provider.select_model("default")
            assert model == "llama3"
    
    def test_ollama_select_model_vision(self):
        """Test model selection for image tasks"""
        from backend.core.ai_providers import OllamaProvider
        
        with patch.object(OllamaProvider, "get_available_models", return_value=["llama3", "llama3.2-vision"]):
            provider = OllamaProvider()
            
            model = provider.select_model("image_analysis", has_image=True)
            assert model == "llama3.2-vision"
    
    def test_ollama_select_model_quick(self):
        """Test model selection for quick analysis"""
        from backend.core.ai_providers import OllamaProvider
        
        with patch.object(OllamaProvider, "get_available_models", return_value=["llama3", "llama3.2"]):
            provider = OllamaProvider()
            
            model = provider.select_model("quick_analysis")
            assert model == "llama3.2"
    
    @patch("requests.post")
    def test_ollama_complete_success(self, mock_post):
        """Test successful completion"""
        from backend.core.ai_providers import OllamaProvider
        
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {"response": "Test response"}
        )
        mock_post.return_value.raise_for_status = Mock()
        
        with patch.object(OllamaProvider, "is_available", return_value=True):
            with patch.object(OllamaProvider, "get_available_models", return_value=["llama3"]):
                provider = OllamaProvider()
                result = provider.complete("Test prompt", "System prompt")
                
                assert result == "Test response"
                mock_post.assert_called_once()
    
    @patch("requests.post")
    def test_ollama_stream_success(self, mock_post):
        """Test successful streaming"""
        from backend.core.ai_providers import OllamaProvider
        
        # Mock streaming response
        mock_response = Mock()
        mock_response.iter_lines.return_value = [
            json.dumps({"response": "Hello", "done": False}).encode(),
            json.dumps({"response": " world", "done": False}).encode(),
            json.dumps({"response": "!", "done": True}).encode(),
        ]
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        with patch.object(OllamaProvider, "is_available", return_value=True):
            with patch.object(OllamaProvider, "get_available_models", return_value=["llama3"]):
                provider = OllamaProvider()
                chunks = list(provider.stream("Test prompt"))
                
                assert chunks == ["Hello", " world", "!"]


class TestOpenAIProvider:
    """Tests for OpenAIProvider"""
    
    def test_openai_provider_init(self):
        """Test OpenAIProvider initialization"""
        from backend.core.ai_providers import OpenAIProvider
        
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o")
        
        assert provider.name == "openai"
        assert provider.api_key == "test-key"
        assert provider.model == "gpt-4o"
    
    def test_openai_is_available_with_key(self):
        """Test is_available with API key"""
        from backend.core.ai_providers import OpenAIProvider
        
        provider = OpenAIProvider(api_key="test-key")
        assert provider.is_available() is True
    
    def test_openai_is_available_without_key(self):
        """Test is_available without API key"""
        from backend.core.ai_providers import OpenAIProvider
        
        with patch.dict("os.environ", {}, clear=True):
            provider = OpenAIProvider(api_key=None)
            # Will check env var
            provider.api_key = None
            assert provider.is_available() is False


class TestClaudeProvider:
    """Tests for ClaudeProvider"""
    
    def test_claude_provider_init(self):
        """Test ClaudeProvider initialization"""
        from backend.core.ai_providers import ClaudeProvider
        
        provider = ClaudeProvider(api_key="test-key")
        
        assert provider.name == "claude"
        assert provider.api_key == "test-key"
    
    def test_claude_is_available_with_key(self):
        """Test is_available with API key"""
        from backend.core.ai_providers import ClaudeProvider
        
        provider = ClaudeProvider(api_key="test-key")
        assert provider.is_available() is True


class TestProviderFactory:
    """Tests for provider factory"""
    
    def test_get_provider_ollama(self):
        """Test getting Ollama provider"""
        from backend.core.ai_providers import get_provider, OllamaProvider
        
        provider = get_provider("ollama")
        assert isinstance(provider, OllamaProvider)
    
    def test_get_provider_openai(self):
        """Test getting OpenAI provider"""
        from backend.core.ai_providers import get_provider, OpenAIProvider
        
        provider = get_provider("openai")
        assert isinstance(provider, OpenAIProvider)
    
    def test_get_provider_claude(self):
        """Test getting Claude provider"""
        from backend.core.ai_providers import get_provider, ClaudeProvider
        
        provider = get_provider("claude")
        assert isinstance(provider, ClaudeProvider)
    
    def test_get_provider_unknown(self):
        """Test getting unknown provider raises error"""
        from backend.core.ai_providers import get_provider
        
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("unknown")


class TestFallbackChain:
    """Tests for fallback chain"""
    
    @patch("backend.core.ai_providers.get_provider")
    def test_complete_with_fallback_primary_success(self, mock_get_provider):
        """Test fallback uses primary provider when available"""
        from backend.core.ai_providers import complete_with_fallback
        
        mock_provider = Mock()
        mock_provider.is_available.return_value = True
        mock_provider.complete.return_value = "Success"
        mock_get_provider.return_value = mock_provider
        
        result = complete_with_fallback("test prompt")
        
        assert result == "Success"
        mock_provider.complete.assert_called_once()
    
    @patch("backend.core.ai_providers.get_fallback_chain", return_value=["ollama", "openai"])
    @patch("backend.core.ai_providers.get_provider")
    def test_complete_with_fallback_uses_next(self, mock_get_provider, mock_chain):
        """Test fallback uses next provider when primary fails"""
        from backend.core.ai_providers import complete_with_fallback, ProviderError
        
        # First provider fails
        ollama_provider = Mock()
        ollama_provider.is_available.return_value = True
        ollama_provider.complete.side_effect = ProviderError("Ollama failed")
        
        # Second provider succeeds
        openai_provider = Mock()
        openai_provider.is_available.return_value = True
        openai_provider.complete.return_value = "OpenAI success"
        
        def get_provider_side_effect(name):
            if name == "ollama":
                return ollama_provider
            return openai_provider
        
        mock_get_provider.side_effect = get_provider_side_effect
        
        result = complete_with_fallback("test prompt")
        
        assert result == "OpenAI success"


class TestAIManager:
    """Tests for AIManager wrapper"""
    
    def test_ai_manager_init(self):
        """Test AIManager initialization"""
        from backend.core.ai_manager import AIManager
        
        with patch("backend.core.ai_manager.get_provider") as mock_get:
            mock_provider = Mock()
            mock_provider.name = "ollama"
            mock_get.return_value = mock_provider
            
            manager = AIManager()
            
            assert manager.provider == mock_provider
    
    def test_ai_manager_check_connection(self):
        """Test check_connection delegates to provider"""
        from backend.core.ai_manager import AIManager
        
        with patch("backend.core.ai_manager.get_provider") as mock_get:
            mock_provider = Mock()
            mock_provider.name = "ollama"
            mock_provider.is_available.return_value = True
            mock_get.return_value = mock_provider
            
            manager = AIManager()
            result = manager.check_connection()
            
            assert result is True
            mock_provider.is_available.assert_called_once()
    
    def test_ai_manager_analyze_text(self):
        """Test analyze_text uses fallback"""
        from backend.core.ai_manager import AIManager
        
        with patch("backend.core.ai_manager.get_provider") as mock_get:
            with patch("backend.core.ai_manager.complete_with_fallback") as mock_complete:
                mock_provider = Mock()
                mock_provider.name = "ollama"
                mock_get.return_value = mock_provider
                mock_complete.return_value = "Analysis result"
                
                manager = AIManager()
                result = manager.analyze_text("Test text")
                
                assert result == "Analysis result"
                mock_complete.assert_called_once()
    
    def test_ai_manager_get_system_prompt(self):
        """Test _get_system_prompt returns correct prompts"""
        from backend.core.ai_manager import AIManager
        
        with patch("backend.core.ai_manager.get_provider") as mock_get:
            mock_provider = Mock()
            mock_provider.name = "ollama"
            mock_get.return_value = mock_provider
            
            manager = AIManager()
            
            prompt = manager._get_system_prompt("copy_analysis")
            assert "Marketing Digital" in prompt
            
            prompt = manager._get_system_prompt("funnel_strategy")
            assert "Estrategista" in prompt
            
            prompt = manager._get_system_prompt("unknown")
            assert prompt == "Analise este texto."
