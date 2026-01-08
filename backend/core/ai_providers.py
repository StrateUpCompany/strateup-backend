"""
AI Providers - Multi-provider system with Ollama optimization

Providers:
- OllamaProvider: Local LLM with streaming, 32K context, model selector
- OpenAIProvider: GPT-4o fallback
- ClaudeProvider: Claude 3.5 Sonnet fallback

Factory: get_provider(name) -> BaseAIProvider
"""
import os
import json
import requests
from abc import ABC, abstractmethod
from typing import Generator, Optional, Dict, Any, List
from backend.utils.logger import logger
from backend.core.secrets_manager import get_secret


# =============================================================================
# BASE PROVIDER
# =============================================================================

class BaseAIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    def complete(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        """Generate a completion (non-streaming)"""
        pass
    
    @abstractmethod
    def stream(self, prompt: str, system_prompt: str = "", **kwargs) -> Generator[str, None, None]:
        """Generate a streaming completion"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass


# =============================================================================
# OLLAMA PROVIDER - Optimized
# =============================================================================

class OllamaProvider(BaseAIProvider):
    """
    Optimized Ollama provider with:
    - Streaming support
    - 32K context window
    - Intelligent model selector
    """
    
    # Model configurations
    MODELS = {
        "llama3.2-vision": {
            "size": "7.8GB",
            "context": 32768,
            "capabilities": ["text", "vision"],
            "use_for": ["image_analysis", "screenshot_analysis"]
        },
        "llama3": {
            "size": "4.7GB",
            "context": 32768,
            "capabilities": ["text"],
            "use_for": ["content_generation", "copy_analysis", "proposals"]
        },
        "llama3.2": {
            "size": "2.0GB",
            "context": 32768,
            "capabilities": ["text"],
            "use_for": ["quick_analysis", "simple_tasks"]
        }
    }
    
    def __init__(
        self,
        model: str = None,
        api_url: str = "http://localhost:11434",
        context_size: int = None
    ):
        self.default_model = model or get_secret("OLLAMA_MODEL", "llama3")
        self.api_url = api_url
        self.context_size = context_size or int(get_secret("OLLAMA_CONTEXT_SIZE", "32768"))
        
    @property
    def name(self) -> str:
        return "ollama"
    
    def is_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            resp = requests.get(f"{self.api_url}/api/tags", timeout=2)
            return resp.status_code == 200
        except:
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of installed models"""
        try:
            resp = requests.get(f"{self.api_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return [m["name"].split(":")[0] for m in models]
        except:
            pass
        return []
    
    def select_model(self, task_type: str = "default", has_image: bool = False) -> str:
        """
        Intelligently select the best model for the task.
        
        Args:
            task_type: Type of task (content_generation, quick_analysis, etc)
            has_image: Whether the task involves image analysis
        """
        available = self.get_available_models()
        
        # Image tasks require vision model
        if has_image and "llama3.2-vision" in available:
            logger.info("Selected llama3.2-vision for image task")
            return "llama3.2-vision"
        
        # Match task to best model
        for model_name, config in self.MODELS.items():
            if task_type in config.get("use_for", []) and model_name in available:
                logger.info(f"Selected {model_name} for {task_type}")
                return model_name
        
        # Fallback to default or llama3
        if self.default_model in available:
            return self.default_model
        if "llama3" in available:
            return "llama3"
        if available:
            return available[0]
        
        return self.default_model
    
    def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        task_type: str = "default",
        has_image: bool = False,
        **kwargs
    ) -> str:
        """
        Generate a non-streaming completion.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            task_type: For model selection
            has_image: For model selection
        """
        model = self.select_model(task_type, has_image)
        
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        payload = {
            "model": model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "num_ctx": self.context_size,
                "temperature": kwargs.get("temperature", 0.7),
            }
        }
        
        # Add image if provided
        if has_image and "images" in kwargs:
            payload["images"] = kwargs["images"]
        
        try:
            logger.info(f"Ollama complete: model={model}, ctx={self.context_size}")
            response = requests.post(
                f"{self.api_url}/api/generate",
                json=payload,
                timeout=kwargs.get("timeout", 180)
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.exceptions.ConnectionError:
            raise ProviderError("Ollama não está rodando. Execute: ollama serve")
        except Exception as e:
            raise ProviderError(f"Ollama error: {str(e)}")
    
    def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        task_type: str = "default",
        has_image: bool = False,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Generate a streaming completion.
        
        Yields chunks of text as they are generated.
        """
        model = self.select_model(task_type, has_image)
        
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        payload = {
            "model": model,
            "prompt": full_prompt,
            "stream": True,
            "options": {
                "num_ctx": self.context_size,
                "temperature": kwargs.get("temperature", 0.7),
            }
        }
        
        if has_image and "images" in kwargs:
            payload["images"] = kwargs["images"]
        
        try:
            logger.info(f"Ollama stream: model={model}, ctx={self.context_size}")
            response = requests.post(
                f"{self.api_url}/api/generate",
                json=payload,
                stream=True,
                timeout=kwargs.get("timeout", 300)
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        chunk = data.get("response", "")
                        if chunk:
                            yield chunk
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
                        
        except requests.exceptions.ConnectionError:
            raise ProviderError("Ollama não está rodando. Execute: ollama serve")
        except Exception as e:
            raise ProviderError(f"Ollama stream error: {str(e)}")


# =============================================================================
# OPENAI PROVIDER
# =============================================================================

class OpenAIProvider(BaseAIProvider):
    """OpenAI GPT-4o provider as fallback"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        self.api_key = api_key or get_secret("OPENAI_API_KEY")
        self.model = model
        self.api_url = "https://api.openai.com/v1/chat/completions"
    
    @property
    def name(self) -> str:
        return "openai"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def complete(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        if not self.is_available():
            raise ProviderError("OpenAI API key não configurada")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096)
        }
        
        try:
            logger.info(f"OpenAI complete: model={self.model}")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=kwargs.get("timeout", 120)
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise ProviderError(f"OpenAI error: {str(e)}")
    
    def stream(self, prompt: str, system_prompt: str = "", **kwargs) -> Generator[str, None, None]:
        if not self.is_available():
            raise ProviderError("OpenAI API key não configurada")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": True
        }
        
        try:
            logger.info(f"OpenAI stream: model={self.model}")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=kwargs.get("timeout", 300)
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            content = chunk["choices"][0]["delta"].get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            raise ProviderError(f"OpenAI stream error: {str(e)}")


# =============================================================================
# CLAUDE PROVIDER
# =============================================================================

class ClaudeProvider(BaseAIProvider):
    """Anthropic Claude 3.5 Sonnet provider as fallback"""
    
    def __init__(self, api_key: str = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or get_secret("ANTHROPIC_API_KEY")
        self.model = model
        self.api_url = "https://api.anthropic.com/v1/messages"
    
    @property
    def name(self) -> str:
        return "claude"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def complete(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        if not self.is_available():
            raise ProviderError("Anthropic API key não configurada")
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": [{"role": "user", "content": prompt}]
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            logger.info(f"Claude complete: model={self.model}")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=kwargs.get("timeout", 120)
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]
        except Exception as e:
            raise ProviderError(f"Claude error: {str(e)}")
    
    def stream(self, prompt: str, system_prompt: str = "", **kwargs) -> Generator[str, None, None]:
        if not self.is_available():
            raise ProviderError("Anthropic API key não configurada")
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": [{"role": "user", "content": prompt}],
            "stream": True
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            logger.info(f"Claude stream: model={self.model}")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=kwargs.get("timeout", 300)
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "content_block_delta":
                                text = data.get("delta", {}).get("text", "")
                                if text:
                                    yield text
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            raise ProviderError(f"Claude stream error: {str(e)}")


# =============================================================================
# EXCEPTIONS
# =============================================================================

class ProviderError(Exception):
    """Exception raised when a provider fails"""
    pass


class AllProvidersFailed(Exception):
    """Exception raised when all providers fail"""
    pass


# =============================================================================
# FACTORY & FALLBACK CHAIN
# =============================================================================

_providers: Dict[str, BaseAIProvider] = {}

def get_provider(name: str = None) -> BaseAIProvider:
    """
    Get a provider instance by name.
    
    Args:
        name: Provider name (ollama, openai, claude) or None for default
    
    Returns:
        Provider instance
    """
    if name is None:
        name = get_secret("AI_PROVIDER", "ollama")
    
    if name not in _providers:
        if name == "ollama":
            _providers[name] = OllamaProvider()
        elif name == "openai":
            _providers[name] = OpenAIProvider()
        elif name == "claude":
            _providers[name] = ClaudeProvider()
        else:
            raise ValueError(f"Unknown provider: {name}")
    
    return _providers[name]


def get_fallback_chain() -> List[str]:
    """Get the fallback chain order"""
    primary = get_secret("AI_PROVIDER", "ollama")
    chain = [primary]
    
    fallbacks = ["ollama", "openai", "claude"]
    for fb in fallbacks:
        if fb not in chain:
            chain.append(fb)
    
    return chain


def complete_with_fallback(
    prompt: str,
    system_prompt: str = "",
    **kwargs
) -> str:
    """
    Complete with automatic fallback to other providers.
    
    Args:
        prompt: User prompt
        system_prompt: System instructions
        **kwargs: Additional provider-specific args
    
    Returns:
        Generated text
    
    Raises:
        AllProvidersFailed: If all providers fail
    """
    chain = get_fallback_chain()
    errors = []
    
    for provider_name in chain:
        try:
            provider = get_provider(provider_name)
            if not provider.is_available():
                logger.warning(f"Provider {provider_name} not available, skipping")
                continue
            
            result = provider.complete(prompt, system_prompt, **kwargs)
            logger.info(f"Completed with provider: {provider_name}")
            return result
            
        except ProviderError as e:
            logger.warning(f"Provider {provider_name} failed: {e}")
            errors.append(f"{provider_name}: {str(e)}")
            continue
    
    raise AllProvidersFailed(f"All providers failed: {'; '.join(errors)}")


def stream_with_fallback(
    prompt: str,
    system_prompt: str = "",
    **kwargs
) -> Generator[str, None, None]:
    """
    Stream with automatic fallback to other providers.
    
    Args:
        prompt: User prompt
        system_prompt: System instructions
        **kwargs: Additional provider-specific args
    
    Yields:
        Text chunks
    
    Raises:
        AllProvidersFailed: If all providers fail
    """
    chain = get_fallback_chain()
    errors = []
    
    for provider_name in chain:
        try:
            provider = get_provider(provider_name)
            if not provider.is_available():
                logger.warning(f"Provider {provider_name} not available, skipping")
                continue
            
            logger.info(f"Streaming with provider: {provider_name}")
            yield from provider.stream(prompt, system_prompt, **kwargs)
            return
            
        except ProviderError as e:
            logger.warning(f"Provider {provider_name} failed: {e}")
            errors.append(f"{provider_name}: {str(e)}")
            continue
    
    raise AllProvidersFailed(f"All providers failed: {'; '.join(errors)}")
