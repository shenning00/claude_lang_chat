"""Configuration management for the chat client."""

import os
import logging
from typing import Optional, Dict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging for this module
logger = logging.getLogger(__name__)


class Config:
    """Configuration class for managing environment variables and settings."""

    # API Configuration
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Model Configuration
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-3-7-sonnet-latest")
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "4000"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))

    # Thinking Mode Configuration
    THINKING_MODE: bool = os.getenv("THINKING_MODE", "true").lower() == "true"
    THINKING_BUDGET_TOKENS: int = int(
        os.getenv("THINKING_BUDGET_TOKENS", "2000")
    )

    # Memory Management
    MAX_MEMORY_MESSAGES: int = int(os.getenv("MAX_MEMORY_MESSAGES", "50"))
    AUTO_SAVE_INTERVAL: int = int(os.getenv("AUTO_SAVE_INTERVAL", "300"))

    # UI Configuration
    ENABLE_COLORS: bool = os.getenv("ENABLE_COLORS", "true").lower() == "true"
    SHOW_TIMESTAMPS: bool = (
        os.getenv("SHOW_TIMESTAMPS", "true").lower() == "true"
    )
    SHOW_TOKEN_USAGE: bool = (
        os.getenv("SHOW_TOKEN_USAGE", "true").lower() == "true"
    )

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "chat_client.log")

    @classmethod
    def validate_api_key(cls) -> bool:
        """Validate that the API key is present and properly formatted."""
        if not cls.ANTHROPIC_API_KEY:
            return False

        # Basic validation - should start with 'sk-ant-'
        if not cls.ANTHROPIC_API_KEY.startswith("sk-ant-"):
            return False

        return True

    @classmethod
    def get_api_key_interactively(cls) -> Optional[str]:
        """Prompt user for API key if not found in environment."""
        print("🤖 Claude Chat Client")
        print("⚠️  API key not found. Please set your Anthropic API key:")
        print("    Option 1: Set ANTHROPIC_API_KEY environment variable")
        print("    Option 2: Enter it now (will be saved for this session)")
        print()

        api_key = input("Enter API key: ").strip()

        if api_key and api_key.startswith("sk-ant-"):
            # Store for this session
            cls.ANTHROPIC_API_KEY = api_key
            os.environ["ANTHROPIC_API_KEY"] = api_key
            return api_key
        else:
            print("❌ Invalid API key format. Should start with 'sk-ant-'")
            return None

    @classmethod
    def get_model_config(cls) -> dict:
        """Get model configuration dictionary."""
        # For thinking mode, temperature must be 1.0
        temperature = (
            1.0
            if (cls.THINKING_MODE and "claude-3-7" in cls.CLAUDE_MODEL)
            else cls.TEMPERATURE
        )

        config = {
            "model": cls.CLAUDE_MODEL,
            "max_tokens": cls.MAX_TOKENS,
            "temperature": temperature,
        }

        # Add thinking mode configuration if enabled
        if cls.THINKING_MODE and "claude-3-7" in cls.CLAUDE_MODEL:
            config["thinking"] = {
                "type": "enabled",
                "budget_tokens": cls.THINKING_BUDGET_TOKENS,
            }

        return config

    @classmethod
    def display_config(cls) -> None:
        """Display current configuration."""
        print("📋 Current Configuration:")
        print(f"  • Model: {cls.CLAUDE_MODEL}")
        print(f"  • Max Tokens: {cls.MAX_TOKENS}")
        print(f"  • Temperature: {cls.TEMPERATURE}")
        print(
            f"  • Thinking Mode: {'Enabled' if cls.THINKING_MODE else 'Disabled'}"
        )
        if cls.THINKING_MODE:
            print(f"  • Thinking Budget: {cls.THINKING_BUDGET_TOKENS} tokens")
        print(f"  • Max Memory Messages: {cls.MAX_MEMORY_MESSAGES}")
        print(f"  • Colors: {'Enabled' if cls.ENABLE_COLORS else 'Disabled'}")
        print(
            f"  • Timestamps: {'Enabled' if cls.SHOW_TIMESTAMPS else 'Disabled'}"
        )
        print(
            f"  • Token Usage: {'Visible' if cls.SHOW_TOKEN_USAGE else 'Hidden'}"
        )


# Dynamic model loading from Anthropic API
def _fetch_available_models() -> Dict[str, str]:
    """Fetch available models from Anthropic API."""
    try:
        import anthropic

        if not Config.ANTHROPIC_API_KEY:
            logger.error("No API key available for fetching models")
            return {}

        client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        models_response = client.models.list()

        available_models = {}
        for model in models_response.data:
            model_id = model.id
            display_name = model.display_name or model_id

            # Add descriptive text based on model ID patterns
            if "claude-3-7" in model_id and "sonnet" in model_id:
                description = f"{display_name} - Latest with thinking mode"
            elif "claude-3-5" in model_id and "sonnet" in model_id:
                description = f"{display_name} - High performance"
            elif "opus" in model_id:
                description = f"{display_name} - Maximum capability"
            elif "haiku" in model_id:
                description = f"{display_name} - Fast and economical"
            else:
                description = display_name

            available_models[model_id] = description

        logger.info(
            f"Successfully fetched {len(available_models)} models from Anthropic API"
        )
        return available_models

    except ImportError:
        logger.error("anthropic package not available - no models loaded")
        return {}
    except Exception as e:
        logger.error(f"Failed to fetch models from API: {e}")
        return {}


# Initialize available models dynamically
def _initialize_available_models():
    """Initialize the AVAILABLE_MODELS attribute."""
    if not hasattr(Config, "AVAILABLE_MODELS") or not Config.AVAILABLE_MODELS:
        Config.AVAILABLE_MODELS = _fetch_available_models()
    return Config.AVAILABLE_MODELS


# Lazy initialization - models will be fetched on first access
Config.AVAILABLE_MODELS = None


def get_available_models() -> Dict[str, str]:
    """Get available models, fetching from API if not already loaded."""
    if Config.AVAILABLE_MODELS is None:
        Config.AVAILABLE_MODELS = _fetch_available_models()
    return Config.AVAILABLE_MODELS


def update_model(model_name: str) -> bool:
    """Update the current model configuration."""
    available_models = get_available_models()
    if model_name in available_models:
        Config.CLAUDE_MODEL = model_name
        os.environ["CLAUDE_MODEL"] = model_name
        return True
    return False


def toggle_thinking_mode() -> bool:
    """Toggle thinking mode on/off."""
    Config.THINKING_MODE = not Config.THINKING_MODE
    os.environ["THINKING_MODE"] = str(Config.THINKING_MODE).lower()
    return Config.THINKING_MODE


def setup_config() -> bool:
    """Set up configuration and validate API key."""
    if not Config.validate_api_key():
        api_key = Config.get_api_key_interactively()
        if not api_key:
            return False

    print("✅ API key validated successfully!")
    print(f"🚀 Connected to {Config.CLAUDE_MODEL}")
    print()

    return True
