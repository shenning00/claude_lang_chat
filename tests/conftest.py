"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock
import sys

# Add src to path for all tests
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config import Config


@pytest.fixture
def temp_directory():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_llm_handler():
    """Create a mock LLM handler for tests."""
    mock_llm = Mock()
    mock_llm.current_model = "claude-3-sonnet"
    mock_llm.generate_response.return_value = "Mock response"
    mock_llm.estimate_tokens.return_value = 50
    mock_llm.get_model_info.return_value = {
        "model": "claude-3-sonnet",
        "thinking_mode": False,
        "temperature": 0.7,
        "max_tokens": 4000
    }
    mock_llm.test_connection.return_value = True
    mock_llm.switch_model.return_value = True
    mock_llm.set_system_prompt.return_value = None
    mock_llm.clear_system_prompt.return_value = None
    return mock_llm


@pytest.fixture
def test_config():
    """Configure test settings."""
    # Store original values
    original_max_messages = Config.MAX_MEMORY_MESSAGES
    original_thinking_mode = Config.THINKING_MODE
    
    # Set test values
    Config.MAX_MEMORY_MESSAGES = 20  # Smaller for faster tests
    Config.THINKING_MODE = False
    
    yield Config
    
    # Restore original values
    Config.MAX_MEMORY_MESSAGES = original_max_messages
    Config.THINKING_MODE = original_thinking_mode


@pytest.fixture
def sample_messages():
    """Provide sample messages for testing."""
    return [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you! How can I help you today?"},
        {"role": "user", "content": "I need help with Python programming."},
        {"role": "assistant", "content": "I'd be happy to help with Python. What specific topic would you like to discuss?"},
        {"role": "user", "content": "How do I create a function?"},
        {"role": "assistant", "content": "You can create a function in Python using the 'def' keyword. Here's an example:\n\n```python\ndef my_function():\n    print('Hello, World!')\n```"}
    ]


@pytest.fixture
def sample_conversation_data():
    """Provide sample conversation data for testing."""
    return {
        "session_id": "test-session-123",
        "name": "Test Session",
        "created_at": "2025-01-01T12:00:00Z",
        "messages": [
            {
                "role": "user",
                "content": "Hello",
                "timestamp": "2025-01-01T12:00:00Z",
                "tokens": 5,
                "metadata": {}
            },
            {
                "role": "assistant", 
                "content": "Hello! How can I help you today?",
                "timestamp": "2025-01-01T12:00:01Z",
                "tokens": 10,
                "metadata": {}
            }
        ],
        "pinned_messages": [],
        "metadata": {
            "session_id": "test-session-123",
            "name": "Test Session",
            "created_at": "2025-01-01T12:00:00Z",
            "last_updated": "2025-01-01T12:00:01Z",
            "message_count": 2,
            "total_tokens": 15,
            "model_used": "claude-3-sonnet",
            "is_active": True,
            "summary": None
        }
    }


@pytest.fixture
def sample_prompt_templates():
    """Provide sample prompt templates for testing."""
    return [
        {
            "name": "coding-assistant",
            "description": "Helps with programming tasks",
            "system_prompt": "You are a {language} programming expert. Help users with {task_type} tasks.",
            "variables": ["language", "task_type"],
            "category": "development",
            "author": "test",
            "created_at": "2025-01-01T12:00:00Z",
            "usage_count": 5
        },
        {
            "name": "research-helper",
            "description": "Assists with research and analysis",
            "system_prompt": "You are a research assistant specializing in {domain}. Provide thorough analysis.",
            "variables": ["domain"],
            "category": "research",
            "author": "test", 
            "created_at": "2025-01-01T12:00:00Z",
            "usage_count": 3
        }
    ]


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up the test environment."""
    # Disable any external connections or file operations during tests
    # This is run once per test session
    yield
    # Cleanup after all tests


class TestHelpers:
    """Helper methods for tests."""
    
    @staticmethod
    def create_test_messages(count: int, start_index: int = 0):
        """Create test messages for testing."""
        messages = []
        for i in range(start_index, start_index + count):
            messages.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Test message {i}",
                "timestamp": f"2025-01-01T12:{i:02d}:00Z",
                "tokens": 10 + (i % 5),
                "metadata": {"test_index": i}
            })
        return messages
    
    @staticmethod
    def create_conversation_history(exchanges: int):
        """Create a conversation history with specified number of exchanges."""
        messages = []
        for i in range(exchanges):
            messages.append({
                "role": "user",
                "content": f"User message {i}",
            })
            messages.append({
                "role": "assistant", 
                "content": f"Assistant response {i}",
            })
        return messages
    
    @staticmethod
    def assert_valid_session_data(session_data):
        """Assert that session data has the expected structure."""
        required_fields = ["session_id", "name", "message_count", "total_tokens", "last_activity"]
        for field in required_fields:
            assert field in session_data, f"Missing required field: {field}"
        
        assert isinstance(session_data["message_count"], int)
        assert isinstance(session_data["total_tokens"], int)
        assert session_data["message_count"] >= 0
        assert session_data["total_tokens"] >= 0
    
    @staticmethod
    def assert_valid_command_result(result):
        """Assert that a command result has the expected structure."""
        assert isinstance(result, dict), "Command result should be a dictionary"
        
        # Should have either success or error, not both
        has_success = "success" in result
        has_error = "error" in result
        assert has_success != has_error, "Result should have either success or error, not both"
        
        if has_success:
            assert isinstance(result["success"], bool)
            if result["success"] and "message" in result:
                assert isinstance(result["message"], str)
        
        if has_error:
            assert isinstance(result["error"], str)
            assert len(result["error"]) > 0
    
    @staticmethod
    def assert_valid_analytics_data(analytics):
        """Assert that analytics data has the expected structure."""
        required_sections = ["session_info", "topic_analysis", "message_patterns", "memory_usage"]
        for section in required_sections:
            assert section in analytics, f"Missing analytics section: {section}"
        
        # Check session info
        session_info = analytics["session_info"]
        assert "total_messages" in session_info
        assert "user_messages" in session_info
        assert "assistant_messages" in session_info
        assert isinstance(session_info["total_messages"], int)
        
        # Check memory usage
        memory_usage = analytics["memory_usage"]
        assert "messages_in_memory" in memory_usage
        assert "memory_utilization" in memory_usage
        assert isinstance(memory_usage["memory_utilization"], (int, float))


# Make test helpers available globally
@pytest.fixture
def test_helpers():
    """Provide test helper methods."""
    return TestHelpers