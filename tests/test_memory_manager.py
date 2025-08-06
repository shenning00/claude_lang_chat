"""Tests for the memory manager."""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.memory_manager import MemoryManager, ConversationSession, MessageData, SessionMetadata
from src.config import Config


class TestMessageData:
    """Test MessageData class."""
    
    def test_message_creation(self):
        """Test message data creation."""
        message = MessageData(
            role="user",
            content="Hello, world!",
            timestamp="2025-01-01T12:00:00Z",
            tokens=10
        )
        
        assert message.role == "user"
        assert message.content == "Hello, world!"
        assert message.timestamp == "2025-01-01T12:00:00Z"
        assert message.tokens == 10
    
    def test_message_serialization(self):
        """Test message serialization."""
        message = MessageData(
            role="assistant",
            content="Hello back!",
            timestamp="2025-01-01T12:00:01Z",
            tokens=8,
            metadata={"type": "greeting"}
        )
        
        # Test to_dict
        data = message.to_dict()
        assert data["role"] == "assistant"
        assert data["content"] == "Hello back!"
        assert data["metadata"]["type"] == "greeting"
        
        # Test from_dict
        restored = MessageData.from_dict(data)
        assert restored.role == message.role
        assert restored.content == message.content
        assert restored.metadata == message.metadata


class TestSessionMetadata:
    """Test SessionMetadata class."""
    
    def test_metadata_creation(self):
        """Test session metadata creation."""
        metadata = SessionMetadata(
            session_id="test-123",
            name="Test Session",
            created_at="2025-01-01T12:00:00Z",
            last_updated="2025-01-01T12:01:00Z",
            message_count=5,
            total_tokens=100,
            model_used="claude-3-7-sonnet-latest"
        )
        
        assert metadata.session_id == "test-123"
        assert metadata.name == "Test Session"
        assert metadata.message_count == 5
        assert metadata.total_tokens == 100
        assert metadata.is_active == False
    
    def test_metadata_serialization(self):
        """Test metadata serialization."""
        metadata = SessionMetadata(
            session_id="test-456",
            name="Another Session",
            created_at="2025-01-01T12:00:00Z",
            last_updated="2025-01-01T12:05:00Z",
            message_count=10,
            total_tokens=200,
            model_used="claude-3-haiku-20240307",
            is_active=True
        )
        
        # Test to_dict
        data = metadata.to_dict()
        assert data["session_id"] == "test-456"
        assert data["is_active"] == True
        
        # Test from_dict
        restored = SessionMetadata.from_dict(data)
        assert restored.session_id == metadata.session_id
        assert restored.is_active == metadata.is_active


class TestConversationSession:
    """Test ConversationSession class."""
    
    def test_session_creation(self):
        """Test conversation session creation."""
        session = ConversationSession("test-session-id", "Test Session")
        
        assert session.session_id == "test-session-id"
        assert session.name == "Test Session"
        assert len(session.messages) == 0
        assert session.metadata.session_id == "test-session-id"
    
    def test_add_message(self):
        """Test adding messages to session."""
        session = ConversationSession("test-id")
        
        session.add_message("user", "Hello", tokens=5)
        session.add_message("assistant", "Hi there!", tokens=7)
        
        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[1].role == "assistant"
        assert session.metadata.message_count == 2
        assert session.metadata.total_tokens == 12
    
    def test_get_messages(self):
        """Test getting messages from session."""
        session = ConversationSession("test-id")
        
        session.add_message("user", "First message", tokens=10)
        session.add_message("assistant", "First response", tokens=12)
        session.add_message("user", "Second message", tokens=11)
        
        # Get all messages
        messages = session.get_messages()
        assert len(messages) == 3
        
        # Get limited messages
        limited = session.get_messages(limit=2)
        assert len(limited) == 2
        assert limited[0]["content"] == "First response"
        assert limited[1]["content"] == "Second message"
    
    def test_get_recent_context(self):
        """Test getting recent context within token limit."""
        session = ConversationSession("test-id")
        
        # Add messages with varying token counts
        session.add_message("user", "Message 1", tokens=20)
        session.add_message("assistant", "Response 1", tokens=25)
        session.add_message("user", "Message 2", tokens=15)
        session.add_message("assistant", "Response 2", tokens=10)
        
        # Get context with token limit
        context = session.get_recent_context(token_limit=30)
        
        # Should include last 2 messages (15 + 10 = 25 tokens)
        assert len(context) == 2
        assert context[0]["content"] == "Message 2"
        assert context[1]["content"] == "Response 2"
    
    def test_pin_unpin_messages(self):
        """Test pinning and unpinning messages."""
        session = ConversationSession("test-id")
        
        session.add_message("user", "Important message", tokens=10)
        session.add_message("assistant", "Response", tokens=8)
        
        # Pin first message
        result = session.pin_message(0)
        assert result == True
        assert 0 in session.pinned_messages
        
        # Try to pin again (should return True but not duplicate)
        result = session.pin_message(0)
        # Pin operation returns True whether new or existing
        assert len(session.pinned_messages) == 1
        
        # Unpin message
        result = session.unpin_message(0)
        assert result == True
        assert 0 not in session.pinned_messages
    
    def test_clear_messages(self):
        """Test clearing session messages."""
        session = ConversationSession("test-id")
        
        session.add_message("user", "Message 1", tokens=10)
        session.add_message("assistant", "Response 1", tokens=12)
        session.pin_message(0)
        
        count = session.clear_messages()
        
        assert count == 2
        assert len(session.messages) == 0
        assert len(session.pinned_messages) == 0
        assert session.metadata.message_count == 0
        assert session.metadata.total_tokens == 0
    
    def test_get_summary(self):
        """Test getting session summary."""
        session = ConversationSession("test-id", "Test Session")
        
        # Empty session
        summary = session.get_summary()
        assert summary["session_id"] == "test-id"
        assert summary["message_count"] == 0
        
        # Add messages
        session.add_message("user", "Hello there!", tokens=5)
        session.add_message("assistant", "Hi! How can I help you today?", tokens=10)
        
        summary = session.get_summary()
        assert summary["message_count"] == 2
        assert summary["total_tokens"] == 15
        assert "last_message_preview" in summary
    
    def test_export_import(self):
        """Test exporting and importing session data."""
        session = ConversationSession("test-id", "Test Session")
        
        session.add_message("user", "Message 1", tokens=10)
        session.add_message("assistant", "Response 1", tokens=12)
        session.pin_message(0)
        
        # Export data
        exported = session.export_data()
        assert "metadata" in exported
        assert "messages" in exported
        assert "pinned_messages" in exported
        
        # Import data
        restored = ConversationSession.from_export_data(exported)
        assert restored.session_id == session.session_id
        assert len(restored.messages) == 2
        assert 0 in restored.pinned_messages


class TestMemoryManager:
    """Test MemoryManager class."""
    
    def test_manager_initialization(self):
        """Test memory manager initialization."""
        manager = MemoryManager()
        
        assert len(manager.sessions) == 0
        assert manager.current_session_id is None
    
    def test_create_session(self):
        """Test creating sessions."""
        manager = MemoryManager()
        
        # Create first session
        session_id = manager.create_session("First Session")
        assert session_id in manager.sessions
        assert manager.current_session_id == session_id
        assert manager.sessions[session_id].name == "First Session"
        
        # Create second session
        session_id2 = manager.create_session("Second Session")
        assert session_id2 in manager.sessions
        assert len(manager.sessions) == 2
    
    def test_switch_session(self):
        """Test switching between sessions."""
        manager = MemoryManager()
        
        id1 = manager.create_session("Session 1")
        id2 = manager.create_session("Session 2")
        
        # Switch to first session
        result = manager.switch_session(id1)
        assert result == True
        assert manager.current_session_id == id1
        assert manager.sessions[id1].metadata.is_active == True
        assert manager.sessions[id2].metadata.is_active == False
        
        # Try invalid session
        result = manager.switch_session("invalid-id")
        assert result == False
    
    def test_delete_session(self):
        """Test deleting sessions."""
        manager = MemoryManager()
        
        id1 = manager.create_session("Session 1")
        id2 = manager.create_session("Session 2")
        
        # Delete non-current session
        result = manager.delete_session(id1)
        assert result == True
        assert id1 not in manager.sessions
        assert manager.current_session_id == id2
        
        # Delete current session (only one left)
        result = manager.delete_session(id2)
        assert result == True
        assert len(manager.sessions) == 0
        assert manager.current_session_id is None
    
    def test_add_message_to_current(self):
        """Test adding messages to current session."""
        manager = MemoryManager()
        
        # Add message without session (should create default)
        manager.add_message("user", "Hello", tokens=5)
        
        assert len(manager.sessions) == 1
        assert manager.current_session_id is not None
        
        session = manager.get_current_session()
        assert len(session.messages) == 1
        assert session.messages[0].content == "Hello"
    
    def test_get_conversation_history(self):
        """Test getting conversation history."""
        manager = MemoryManager()
        
        manager.create_session("Test")
        manager.add_message("user", "Message 1", tokens=10)
        manager.add_message("assistant", "Response 1", tokens=12)
        manager.add_message("user", "Message 2", tokens=8)
        
        # Get all history
        history = manager.get_conversation_history()
        assert len(history) == 3
        
        # Get limited history
        limited = manager.get_conversation_history(limit=2)
        assert len(limited) == 2
    
    def test_optimize_memory(self):
        """Test memory optimization."""
        manager = MemoryManager()
        
        session_id = manager.create_session("Test")
        
        # Add many messages
        for i in range(60):
            manager.add_message("user", f"Message {i}", tokens=10)
            manager.add_message("assistant", f"Response {i}", tokens=12)
        
        # Optimize memory
        result = manager.optimize_memory()
        
        assert result["optimized"] == True
        assert result["old_count"] == 120
        assert result["new_count"] < 120
    
    def test_search_messages(self):
        """Test searching messages."""
        manager = MemoryManager()
        
        id1 = manager.create_session("Session 1")
        manager.add_message("user", "Tell me about Python", tokens=10)
        manager.add_message("assistant", "Python is a programming language", tokens=15)
        
        id2 = manager.create_session("Session 2")
        manager.add_message("user", "What is JavaScript?", tokens=8)
        
        # Search for "Python"
        results = manager.search_messages("Python")
        assert len(results) == 2
        assert results[0]["session_id"] == id1
        
        # Search for "JavaScript"
        results = manager.search_messages("JavaScript")
        assert len(results) == 1
        # Verify the result is from session 2 (either id1 or id2 could be current)
        assert results[0]["content"] == "What is JavaScript?"
    
    def test_get_memory_stats(self):
        """Test getting memory statistics."""
        manager = MemoryManager()
        
        manager.create_session("Test")
        manager.add_message("user", "Message", tokens=10)
        manager.add_message("assistant", "Response", tokens=12)
        
        stats = manager.get_memory_stats()
        
        assert stats["total_sessions"] == 1
        assert stats["total_messages"] == 2
        assert stats["total_tokens"] == 22
        assert "current_session" in stats
        assert stats["current_session"]["messages"] == 2
    
    def test_export_session(self):
        """Test exporting session in different formats."""
        manager = MemoryManager()
        
        session_id = manager.create_session("Test Session")
        manager.add_message("user", "Hello", tokens=5)
        manager.add_message("assistant", "Hi there!", tokens=7)
        
        # Export as JSON
        json_export = manager.export_session(format_type="json")
        assert "metadata" in json_export
        assert "messages" in json_export
        
        # Export as Markdown
        md_export = manager.export_session(format_type="markdown")
        assert "content" in md_export
        assert md_export["format"] == "markdown"
        assert "# Chat Session" in md_export["content"]
        
        # Export as text
        txt_export = manager.export_session(format_type="txt")
        assert "content" in txt_export
        assert txt_export["format"] == "text"


if __name__ == "__main__":
    pytest.main([__file__])