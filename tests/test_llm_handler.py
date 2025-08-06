"""Tests for LLM handler."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.llm_handler import LLMHandler, StreamingCallbackHandler
from src.config import Config


class TestStreamingCallbackHandler:
    """Test StreamingCallbackHandler class."""
    
    def test_callback_initialization(self):
        """Test callback handler initialization."""
        handler = StreamingCallbackHandler()
        
        assert handler.tokens == []
        assert handler.is_thinking == False
        assert handler.thinking_tokens == 0
    
    def test_token_handling(self):
        """Test token handling."""
        handler = StreamingCallbackHandler()
        
        # Regular tokens
        handler.on_llm_new_token("Hello")
        handler.on_llm_new_token(" world")
        
        assert handler.get_response() == "Hello world"
    
    def test_thinking_mode_tokens(self):
        """Test thinking mode token handling."""
        handler = StreamingCallbackHandler()
        
        # Start thinking
        handler.on_llm_new_token("<thinking>")
        assert handler.is_thinking == True
        
        # Thinking tokens
        handler.on_llm_new_token("internal thought")
        assert handler.thinking_tokens == 1
        
        # End thinking
        handler.on_llm_new_token("</thinking>")
        assert handler.is_thinking == False
        
        # Regular response
        handler.on_llm_new_token("Hello")
        
        assert handler.get_response() == "Hello"
        assert handler.thinking_tokens == 1
    
    def test_reset_handler(self):
        """Test resetting the handler."""
        handler = StreamingCallbackHandler()
        
        handler.on_llm_new_token("Hello")
        handler.thinking_tokens = 5
        
        handler.reset()
        
        assert handler.tokens == []
        assert handler.thinking_tokens == 0
        assert handler.is_thinking == False


class TestLLMHandler:
    """Test LLMHandler class."""
    
    @patch('src.llm_handler.ChatAnthropic')
    def test_initialization(self, mock_chat_anthropic):
        """Test LLM handler initialization."""
        mock_client = Mock()
        mock_chat_anthropic.return_value = mock_client
        
        handler = LLMHandler()
        
        assert handler.client == mock_client
        assert handler.current_model == Config.CLAUDE_MODEL
        assert handler.system_prompt is None
    
    @patch('src.llm_handler.ChatAnthropic')
    def test_set_system_prompt(self, mock_chat_anthropic):
        """Test setting system prompt."""
        handler = LLMHandler()
        
        test_prompt = "You are a helpful assistant."
        handler.set_system_prompt(test_prompt)
        
        assert handler.system_prompt == test_prompt
    
    @patch('src.llm_handler.ChatAnthropic')
    @patch('src.config.get_available_models')
    def test_switch_model(self, mock_get_models, mock_chat_anthropic):
        """Test model switching."""
        mock_get_models.return_value = {
            "claude-3-haiku-20240307": "Claude 3 Haiku",
            "claude-3-7-sonnet-latest": "Claude 3.7 Sonnet"
        }
        
        handler = LLMHandler()
        
        # Test valid model switch
        valid_model = "claude-3-haiku-20240307"
        result = handler.switch_model(valid_model)
        
        assert result == True
        assert handler.current_model == valid_model
        
        # Test invalid model switch
        result = handler.switch_model("invalid-model")
        assert result == False
    
    @patch('src.llm_handler.ChatAnthropic')
    def test_estimate_tokens(self, mock_chat_anthropic):
        """Test token estimation."""
        handler = LLMHandler()
        
        # Test short text
        short_text = "Hello"
        tokens = handler.estimate_tokens(short_text)
        assert tokens > 0
        assert tokens < 10
        
        # Test longer text
        long_text = "This is a much longer text that should have more tokens " * 10
        long_tokens = handler.estimate_tokens(long_text)
        assert long_tokens > tokens
    
    @patch('src.llm_handler.ChatAnthropic')
    @patch('src.config.get_available_models')
    def test_get_model_info(self, mock_get_models, mock_chat_anthropic):
        """Test getting model information."""
        mock_get_models.return_value = {
            "claude-3-7-sonnet-latest": "Claude 3.7 Sonnet"
        }
        
        handler = LLMHandler()
        
        info = handler.get_model_info()
        
        assert "model" in info
        assert "description" in info
        assert "thinking_mode" in info
        assert "max_tokens" in info
        assert "temperature" in info
        assert "system_prompt" in info
    
    @patch('src.llm_handler.ChatAnthropic')
    def test_supports_thinking_mode(self, mock_chat_anthropic):
        """Test checking thinking mode support."""
        handler = LLMHandler()
        
        # Test with Claude 3.7 model
        handler.current_model = "claude-3-7-sonnet-latest"
        assert handler.supports_thinking_mode() == True
        
        # Test with non-3.7 model
        handler.current_model = "claude-3-haiku-20240307"
        assert handler.supports_thinking_mode() == False
    
    @patch('src.llm_handler.ChatAnthropic')
    def test_prepare_messages(self, mock_chat_anthropic):
        """Test message preparation."""
        handler = LLMHandler()
        
        # Set system prompt
        handler.set_system_prompt("You are helpful.")
        
        # Test message conversion
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        
        prepared = handler._prepare_messages(messages)
        
        # Should have system message + 2 messages
        assert len(prepared) == 3
        assert prepared[0].content == "You are helpful."
        assert prepared[1].content == "Hello"
        assert prepared[2].content == "Hi there"
    
    @patch('src.llm_handler.ChatAnthropic')
    def test_handle_api_error(self, mock_chat_anthropic):
        """Test API error handling."""
        handler = LLMHandler()
        
        # Test rate limit error
        rate_error = Exception("rate limit exceeded")
        msg = handler._handle_api_error(rate_error)
        assert "rate limit" in msg.lower()
        
        # Test auth error
        auth_error = Exception("invalid api key")
        msg = handler._handle_api_error(auth_error)
        assert "api key" in msg.lower()
        
        # Test network error
        network_error = Exception("connection refused")
        msg = handler._handle_api_error(network_error)
        assert "network" in msg.lower() or "connection" in msg.lower()
        
        # Test generic error
        generic_error = Exception("Something went wrong")
        msg = handler._handle_api_error(generic_error)
        assert "Something went wrong" in msg


if __name__ == "__main__":
    pytest.main([__file__])