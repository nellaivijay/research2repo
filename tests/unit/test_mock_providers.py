"""
Unit tests for mock providers
"""

import pytest
from tests.mocks.mock_providers.mock_gemini import MockGeminiProvider
from tests.mocks.mock_providers.mock_openai import MockOpenAIProvider
from tests.mocks.mock_providers.mock_anthropic import MockAnthropicProvider


@pytest.mark.unit
@pytest.mark.mock
class TestMockGeminiProvider:
    """Test MockGeminiProvider functionality."""
    
    def test_initialization(self):
        """Test provider initialization."""
        provider = MockGeminiProvider()
        assert provider.model_name == "gemini-1.5-pro"
        assert provider.call_count == 0
        assert provider.latency == 0.1
    
    def test_custom_model_name(self):
        """Test provider with custom model name."""
        provider = MockGeminiProvider(model_name="gemini-1.5-flash")
        assert provider.model_name == "gemini-1.5-flash"
    
    def test_generate_call(self):
        """Test generate call increments call count."""
        provider = MockGeminiProvider()
        response = provider.generate("test prompt")
        
        assert provider.call_count == 1
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_analysis_response(self):
        """Test analysis response generation."""
        provider = MockGeminiProvider()
        response = provider.generate("Analyze this paper")
        
        assert "title" in response.lower()
        assert "authors" in response.lower()
    
    def test_code_response(self):
        """Test code generation response."""
        provider = MockGeminiProvider()
        response = provider.generate("Generate code for this")
        
        assert "import" in response.lower()
        assert "class" in response.lower() or "def" in response.lower()
    
    def test_call_history(self):
        """Test call history tracking."""
        provider = MockGeminiProvider()
        provider.generate("prompt 1")
        provider.generate("prompt 2")
        
        history = provider.get_call_history()
        assert len(history) == 2
        assert history[0]["prompt"] == "prompt 1"
        assert history[1]["prompt"] == "prompt 2"
    
    def test_reset(self):
        """Test provider reset functionality."""
        provider = MockGeminiProvider()
        provider.generate("test")
        assert provider.call_count == 1
        
        provider.reset()
        assert provider.call_count == 0
        assert len(provider.get_call_history()) == 0


@pytest.mark.unit
@pytest.mark.mock
class TestMockOpenAIProvider:
    """Test MockOpenAIProvider functionality."""
    
    def test_initialization(self):
        """Test provider initialization."""
        provider = MockOpenAIProvider()
        assert provider.model_name == "gpt-4o"
        assert provider.call_count == 0
    
    def test_generate_call(self):
        """Test generate call."""
        provider = MockOpenAIProvider()
        response = provider.generate("test prompt")
        
        assert provider.call_count == 1
        assert isinstance(response, str)
    
    def test_analysis_response(self):
        """Test analysis response."""
        provider = MockOpenAIProvider()
        response = provider.generate("Analyze this paper")
        
        assert "title" in response.lower()
    
    def test_reset(self):
        """Test reset functionality."""
        provider = MockOpenAIProvider()
        provider.generate("test")
        provider.reset()
        
        assert provider.call_count == 0


@pytest.mark.unit
@pytest.mark.mock
class TestMockAnthropicProvider:
    """Test MockAnthropicProvider functionality."""
    
    def test_initialization(self):
        """Test provider initialization."""
        provider = MockAnthropicProvider()
        assert provider.model_name == "claude-3-5-sonnet"
        assert provider.call_count == 0
    
    def test_generate_call(self):
        """Test generate call."""
        provider = MockAnthropicProvider()
        response = provider.generate("test prompt")
        
        assert provider.call_count == 1
        assert isinstance(response, str)
    
    def test_analysis_response(self):
        """Test analysis response."""
        provider = MockAnthropicProvider()
        response = provider.generate("Analyze this paper")
        
        assert "title" in response.lower()
    
    def test_reset(self):
        """Test reset functionality."""
        provider = MockAnthropicProvider()
        provider.generate("test")
        provider.reset()
        
        assert provider.call_count == 0