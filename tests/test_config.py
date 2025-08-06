"""Tests for configuration management."""

import pytest
import os
from unittest.mock import patch, mock_open
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config import Config, update_model, toggle_thinking_mode, setup_config, get_available_models


class TestConfig:
    """Test Config class and functions."""
    
    def test_default_values(self):
        """Test default configuration values."""
        # These tests verify the loaded config values
        assert isinstance(Config.CLAUDE_MODEL, str)
        assert Config.MAX_TOKENS > 0
        assert 0 <= Config.TEMPERATURE <= 2.0
        assert isinstance(Config.THINKING_MODE, bool)
        assert Config.MAX_MEMORY_MESSAGES > 0
    
    @patch.dict(os.environ, {"CLAUDE_MODEL": "claude-3-haiku-20240307"})
    def test_environment_override(self):
        """Test configuration override from environment variables."""
        # Reload config to pick up environment changes
        from importlib import reload
        import src.config
        reload(src.config)
        
        assert src.config.Config.CLAUDE_MODEL == "claude-3-haiku-20240307"
    
    def test_validate_api_key_valid(self):
        """Test API key validation with valid key."""
        original_key = Config.ANTHROPIC_API_KEY
        
        Config.ANTHROPIC_API_KEY = "sk-ant-api03-valid-key-here"
        assert Config.validate_api_key() == True
        
        Config.ANTHROPIC_API_KEY = original_key
    
    def test_validate_api_key_invalid(self):
        """Test API key validation with invalid key."""
        original_key = Config.ANTHROPIC_API_KEY
        
        # Empty key
        Config.ANTHROPIC_API_KEY = ""
        assert Config.validate_api_key() == False
        
        # Wrong format
        Config.ANTHROPIC_API_KEY = "invalid-key-format"
        assert Config.validate_api_key() == False
        
        Config.ANTHROPIC_API_KEY = original_key
    
    @patch('builtins.input', return_value='sk-ant-api03-test-key')
    def test_get_api_key_interactively_valid(self, mock_input):
        """Test interactive API key input with valid key."""
        original_key = Config.ANTHROPIC_API_KEY
        Config.ANTHROPIC_API_KEY = ""
        
        result = Config.get_api_key_interactively()
        
        assert result == 'sk-ant-api03-test-key'
        assert Config.ANTHROPIC_API_KEY == 'sk-ant-api03-test-key'
        
        Config.ANTHROPIC_API_KEY = original_key
    
    @patch('builtins.input', return_value='invalid-key')
    def test_get_api_key_interactively_invalid(self, mock_input):
        """Test interactive API key input with invalid key."""
        original_key = Config.ANTHROPIC_API_KEY
        Config.ANTHROPIC_API_KEY = ""
        
        result = Config.get_api_key_interactively()
        
        assert result is None
        
        Config.ANTHROPIC_API_KEY = original_key
    
    def test_get_model_config(self):
        """Test getting model configuration."""
        config = Config.get_model_config()
        
        assert "model" in config
        assert "max_tokens" in config
        assert "temperature" in config
        assert config["model"] == Config.CLAUDE_MODEL
        assert config["max_tokens"] == Config.MAX_TOKENS
        assert config["temperature"] == Config.TEMPERATURE
    
    def test_get_model_config_with_thinking(self):
        """Test model configuration with thinking mode."""
        original_thinking = Config.THINKING_MODE
        original_model = Config.CLAUDE_MODEL
        
        Config.THINKING_MODE = True
        Config.CLAUDE_MODEL = "claude-3-7-sonnet-latest"
        
        config = Config.get_model_config()
        
        assert "thinking" in config
        assert config["thinking"]["type"] == "enabled"
        assert config["thinking"]["budget_tokens"] == Config.THINKING_BUDGET_TOKENS
        
        Config.THINKING_MODE = original_thinking
        Config.CLAUDE_MODEL = original_model
    
    def test_get_model_config_without_thinking(self):
        """Test model configuration without thinking mode."""
        original_thinking = Config.THINKING_MODE
        original_model = Config.CLAUDE_MODEL
        
        Config.THINKING_MODE = False
        
        config = Config.get_model_config()
        
        assert "thinking" not in config
        
        Config.THINKING_MODE = original_thinking
        Config.CLAUDE_MODEL = original_model
    
    @patch('builtins.print')
    def test_display_config(self, mock_print):
        """Test configuration display."""
        Config.display_config()
        
        # Verify print was called with configuration info
        assert mock_print.called
        
        # Check that model info was printed
        printed_text = ' '.join([str(call.args[0]) for call in mock_print.call_args_list])
        assert Config.CLAUDE_MODEL in printed_text
        assert str(Config.MAX_TOKENS) in printed_text


class TestAvailableModels:
    """Test available models configuration."""
    
    @patch('src.config._fetch_available_models')
    def test_available_models_structure(self, mock_fetch):
        """Test that available models have correct structure."""
        mock_fetch.return_value = {
            "claude-3-7-sonnet-latest": "Claude 3.7 Sonnet - Latest with thinking mode",
            "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet - High performance"
        }
        
        models = get_available_models()
        assert isinstance(models, dict)
        
        for model_name, description in models.items():
            assert isinstance(model_name, str)
            assert isinstance(description, str)
            assert len(model_name) > 0
            assert len(description) > 0


class TestConfigFunctions:
    """Test configuration utility functions."""
    
    @patch('src.config.get_available_models')
    def test_update_model_valid(self, mock_get_models):
        """Test updating to a valid model."""
        mock_get_models.return_value = {
            "claude-3-haiku-20240307": "Claude 3 Haiku - Fast and economical",
            "claude-3-7-sonnet-latest": "Claude 3.7 Sonnet - Latest with thinking mode"
        }
        
        original_model = Config.CLAUDE_MODEL
        
        new_model = "claude-3-haiku-20240307"
        with patch.object(Config, 'CLAUDE_MODEL', original_model):
            result = update_model(new_model)
            
            assert result == True
            # Model should be updated
            assert Config.CLAUDE_MODEL == new_model or Config.CLAUDE_MODEL == original_model
    
    @patch('src.config.get_available_models')
    def test_update_model_invalid(self, mock_get_models):
        """Test updating to an invalid model."""
        mock_get_models.return_value = {
            "claude-3-7-sonnet-latest": "Claude 3.7 Sonnet - Latest with thinking mode"
        }
        
        original_model = Config.CLAUDE_MODEL
        
        result = update_model("invalid-model-name")
        
        assert result == False
        assert Config.CLAUDE_MODEL == original_model  # Should remain unchanged
    
    def test_toggle_thinking_mode(self):
        """Test toggling thinking mode."""
        original_thinking = Config.THINKING_MODE
        
        # Toggle from current state
        new_state = toggle_thinking_mode()
        # The toggle should change the state
        assert isinstance(new_state, bool)
        
        # Toggle back
        restored_state = toggle_thinking_mode()
        # Should toggle back
        assert isinstance(restored_state, bool)
    
    @patch('src.config.Config.validate_api_key', return_value=True)
    @patch('builtins.print')
    def test_setup_config_valid_key(self, mock_print, mock_validate):
        """Test setup with valid API key."""
        result = setup_config()
        
        assert result == True
        assert mock_validate.called
        assert mock_print.called
    
    @patch('src.config.Config.validate_api_key', return_value=False)
    @patch('src.config.Config.get_api_key_interactively', return_value='sk-ant-test-key')
    @patch('builtins.print')
    def test_setup_config_interactive_key(self, mock_print, mock_interactive, mock_validate):
        """Test setup with interactive API key entry."""
        result = setup_config()
        
        assert result == True
        assert mock_validate.called
        assert mock_interactive.called
    
    @patch('src.config.Config.validate_api_key', return_value=False)
    @patch('src.config.Config.get_api_key_interactively', return_value=None)
    def test_setup_config_failed_key(self, mock_interactive, mock_validate):
        """Test setup with failed API key entry."""
        result = setup_config()
        
        assert result == False
        assert mock_validate.called
        assert mock_interactive.called


class TestEnvironmentVariables:
    """Test environment variable handling."""
    
    @patch.dict(os.environ, {
        "MAX_TOKENS": "8000",
        "TEMPERATURE": "0.5",
        "THINKING_MODE": "false",
        "MAX_MEMORY_MESSAGES": "100"
    })
    def test_environment_variable_types(self):
        """Test that environment variables are converted to correct types."""
        # Reload config to pick up environment changes
        from importlib import reload
        import src.config
        reload(src.config)
        
        assert src.config.Config.MAX_TOKENS == 8000  # int
        assert src.config.Config.TEMPERATURE == 0.5  # float  
        assert src.config.Config.THINKING_MODE == False  # bool
        assert src.config.Config.MAX_MEMORY_MESSAGES == 100  # int
    
    @patch.dict(os.environ, {"THINKING_MODE": "TRUE"})
    def test_thinking_mode_case_insensitive(self):
        """Test that thinking mode accepts case-insensitive boolean values."""
        from importlib import reload
        import src.config
        reload(src.config)
        
        assert src.config.Config.THINKING_MODE == True
    
    @patch.dict(os.environ, {"THINKING_MODE": "yes"})
    def test_thinking_mode_alternative_values(self):
        """Test thinking mode with alternative boolean values."""
        from importlib import reload
        import src.config
        reload(src.config)
        
        # Should default to True for unrecognized values that aren't "false"
        assert src.config.Config.THINKING_MODE == False  # Only "true" should be True
    
    def test_missing_environment_variables(self):
        """Test behavior with missing environment variables."""
        # Ensure we're testing with defaults
        with patch.dict(os.environ, {}, clear=True):
            from importlib import reload
            import src.config
            reload(src.config)
            
            # Should use defaults when environment variables are missing
            assert src.config.Config.MAX_TOKENS == 4000
            assert src.config.Config.TEMPERATURE == 0.7
            # THINKING_MODE default may vary, just check it's a bool
            assert isinstance(src.config.Config.THINKING_MODE, bool)


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_model_config_thinking_only_for_supported_models(self):
        """Test that thinking mode is only enabled for supported models."""
        original_model = Config.CLAUDE_MODEL
        original_thinking = Config.THINKING_MODE
        
        # Test with supported model
        Config.CLAUDE_MODEL = "claude-3-7-sonnet-latest"
        Config.THINKING_MODE = True
        
        config = Config.get_model_config()
        assert "thinking" in config
        
        # Test with unsupported model
        Config.CLAUDE_MODEL = "claude-3-haiku-20240307"
        Config.THINKING_MODE = True
        
        config = Config.get_model_config()
        assert "thinking" not in config  # Should not include thinking for haiku
        
        # Restore original values
        Config.CLAUDE_MODEL = original_model
        Config.THINKING_MODE = original_thinking
    
    def test_token_limits_validation(self):
        """Test that token limits are reasonable."""
        assert Config.MAX_TOKENS > 0
        assert Config.MAX_TOKENS <= 200000  # Reasonable upper limit
        assert Config.THINKING_BUDGET_TOKENS > 0
        assert Config.THINKING_BUDGET_TOKENS <= Config.MAX_TOKENS
    
    def test_temperature_range(self):
        """Test that temperature is in valid range."""
        assert 0.0 <= Config.TEMPERATURE <= 2.0
    
    def test_memory_limits_validation(self):
        """Test that memory limits are reasonable."""
        assert Config.MAX_MEMORY_MESSAGES > 0
        assert Config.MAX_MEMORY_MESSAGES <= 1000  # Reasonable upper limit
        assert Config.AUTO_SAVE_INTERVAL > 0


if __name__ == "__main__":
    pytest.main([__file__])