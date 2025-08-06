"""Memory Manager for in-memory conversation storage and management."""

import json
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from config import Config
import logging


@dataclass
class MessageData:
    """Data class for individual messages."""
    role: str
    content: str
    timestamp: str
    tokens: int = 0
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageData':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class SessionMetadata:
    """Metadata for chat sessions."""
    session_id: str
    name: str
    created_at: str
    last_updated: str
    message_count: int
    total_tokens: int
    model_used: str
    is_active: bool = False
    summary: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionMetadata':
        """Create from dictionary."""
        return cls(**data)


class ConversationSession:
    """Represents a single conversation session."""
    
    def __init__(self, session_id: str, name: str = None):
        self.session_id = session_id
        self.name = name or f"Session {session_id[:8]}"
        self.messages: List[MessageData] = []
        self.metadata = SessionMetadata(
            session_id=session_id,
            name=self.name,
            created_at=datetime.now(timezone.utc).isoformat(),
            last_updated=datetime.now(timezone.utc).isoformat(),
            message_count=0,
            total_tokens=0,
            model_used=Config.CLAUDE_MODEL
        )
        self.pinned_messages: List[int] = []  # Indices of pinned messages
        self.logger = logging.getLogger(__name__)
    
    def add_message(self, role: str, content: str, tokens: int = 0, metadata: Dict[str, Any] = None) -> None:
        """Add a message to the session."""
        message = MessageData(
            role=role,
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tokens=tokens,
            metadata=metadata or {}
        )
        
        self.messages.append(message)
        self.metadata.message_count = len(self.messages)
        self.metadata.total_tokens += tokens
        self.metadata.last_updated = message.timestamp
        self.metadata.model_used = Config.CLAUDE_MODEL
        
        self.logger.debug(f"Added {role} message to session {self.session_id}")
    
    def get_messages(self, limit: Optional[int] = None, include_system: bool = True) -> List[Dict[str, str]]:
        """Get messages in format suitable for LLM."""
        messages = []
        
        for i, msg in enumerate(self.messages):
            if not include_system and msg.role == "system":
                continue
            
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        if limit:
            return messages[-limit:]
        return messages
    
    def get_recent_context(self, token_limit: int = None) -> List[Dict[str, str]]:
        """Get recent messages within token limit."""
        if not token_limit:
            token_limit = Config.MAX_TOKENS // 2  # Use half of max tokens for context
        
        messages = []
        current_tokens = 0
        
        # Start from the end and work backwards
        for msg in reversed(self.messages):
            if current_tokens + msg.tokens > token_limit:
                break
            
            messages.insert(0, {
                "role": msg.role,
                "content": msg.content
            })
            current_tokens += msg.tokens
        
        return messages
    
    def pin_message(self, index: int) -> bool:
        """Pin a message to prevent it from being summarized."""
        if 0 <= index < len(self.messages):
            if index not in self.pinned_messages:
                self.pinned_messages.append(index)
                self.logger.info(f"Pinned message {index} in session {self.session_id}")
                return True
        return False
    
    def unpin_message(self, index: int) -> bool:
        """Unpin a message."""
        if index in self.pinned_messages:
            self.pinned_messages.remove(index)
            self.logger.info(f"Unpinned message {index} in session {self.session_id}")
            return True
        return False
    
    def clear_messages(self) -> int:
        """Clear all messages and return count of cleared messages."""
        count = len(self.messages)
        self.messages.clear()
        self.pinned_messages.clear()
        self.metadata.message_count = 0
        self.metadata.total_tokens = 0
        self.metadata.last_updated = datetime.now(timezone.utc).isoformat()
        
        self.logger.info(f"Cleared {count} messages from session {self.session_id}")
        return count
    
    def get_summary(self) -> Dict[str, Any]:
        """Get session summary."""
        if not self.messages:
            return {
                "session_id": self.session_id,
                "name": self.name,
                "message_count": 0,
                "total_tokens": 0,
                "last_activity": "Never",
                "created": self.metadata.created_at,
                "model": self.metadata.model_used
            }
        
        last_message = self.messages[-1]
        return {
            "session_id": self.session_id,
            "name": self.name,
            "message_count": len(self.messages),
            "total_tokens": self.metadata.total_tokens,
            "last_activity": last_message.timestamp,
            "last_message_preview": last_message.content[:100] + "..." if len(last_message.content) > 100 else last_message.content,
            "created": self.metadata.created_at,
            "model": self.metadata.model_used,
            "pinned_count": len(self.pinned_messages)
        }
    
    def export_data(self) -> Dict[str, Any]:
        """Export session data for persistence."""
        return {
            "metadata": self.metadata.to_dict(),
            "messages": [msg.to_dict() for msg in self.messages],
            "pinned_messages": self.pinned_messages
        }
    
    @classmethod
    def from_export_data(cls, data: Dict[str, Any]) -> 'ConversationSession':
        """Create session from exported data."""
        metadata = SessionMetadata.from_dict(data["metadata"])
        session = cls(metadata.session_id, metadata.name)
        session.metadata = metadata
        session.messages = [MessageData.from_dict(msg) for msg in data["messages"]]
        session.pinned_messages = data.get("pinned_messages", [])
        return session


class MemoryManager:
    """Manages in-memory conversation storage and sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationSession] = {}
        self.current_session_id: Optional[str] = None
        self.logger = logging.getLogger(__name__)
        self._auto_save_enabled = True
        self._last_auto_save = time.time()
    
    def create_session(self, name: str = None, model: str = None) -> str:
        """Create a new conversation session with optional model specification."""
        session_id = str(uuid.uuid4())
        session = ConversationSession(session_id, name)
        
        # Set the model for this session
        if model:
            session.metadata.model_used = model
        
        self.sessions[session_id] = session
        
        # Set as current session if it's the first one
        if not self.current_session_id:
            self.current_session_id = session_id
            session.metadata.is_active = True
        
        self.logger.info(f"Created new session: {session_id} ({session.name})")
        return session_id
    
    def switch_session(self, session_id: str) -> bool:
        """Switch to a different session."""
        if session_id not in self.sessions:
            return False
        
        # Deactivate current session
        if self.current_session_id:
            self.sessions[self.current_session_id].metadata.is_active = False
        
        # Activate new session
        self.current_session_id = session_id
        self.sessions[session_id].metadata.is_active = True
        
        self.logger.info(f"Switched to session: {session_id}")
        return True
    
    def get_current_session(self) -> Optional[ConversationSession]:
        """Get the current active session."""
        if self.current_session_id:
            return self.sessions.get(self.current_session_id)
        return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id not in self.sessions:
            return False
        
        # If deleting current session, switch to another one
        if session_id == self.current_session_id:
            remaining_sessions = [sid for sid in self.sessions.keys() if sid != session_id]
            if remaining_sessions:
                self.switch_session(remaining_sessions[0])
            else:
                self.current_session_id = None
        
        del self.sessions[session_id]
        self.logger.info(f"Deleted session: {session_id}")
        return True
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions with their summaries."""
        sessions = []
        for session in self.sessions.values():
            summary = session.get_summary()
            summary["is_active"] = session.session_id == self.current_session_id
            sessions.append(summary)
        
        # Sort by last activity (most recent first)
        sessions.sort(key=lambda x: x["last_activity"], reverse=True)
        return sessions
    
    def get_session_model(self, session_id: str = None) -> Optional[str]:
        """Get the model used by a specific session or current session."""
        if session_id is None:
            session = self.get_current_session()
        else:
            session = self.sessions.get(session_id)
        
        if session:
            return session.metadata.model_used
        return None
    
    def set_session_model(self, model: str, session_id: str = None) -> bool:
        """Set the model for a specific session or current session."""
        if session_id is None:
            session = self.get_current_session()
        else:
            session = self.sessions.get(session_id)
        
        if session:
            session.metadata.model_used = model
            session.metadata.last_updated = datetime.now(timezone.utc).isoformat()
            self.logger.info(f"Updated model for session {session.session_id} to {model}")
            return True
        return False
    
    def add_message(self, role: str, content: str, tokens: int = 0, metadata: Dict[str, Any] = None) -> bool:
        """Add a message to the current session."""
        session = self.get_current_session()
        if not session:
            # Create a default session if none exists
            self.create_session("Default")
            session = self.get_current_session()
        
        session.add_message(role, content, tokens, metadata)
        self._check_auto_save()
        return True
    
    def get_conversation_history(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Get conversation history from current session."""
        session = self.get_current_session()
        if not session:
            return []
        
        return session.get_messages(limit)
    
    def get_memory_optimized_history(self) -> List[Dict[str, str]]:
        """Get conversation history optimized for memory usage."""
        session = self.get_current_session()
        if not session:
            return []
        
        # Use token limit to get recent context
        return session.get_recent_context()
    
    def clear_current_session(self) -> int:
        """Clear messages from current session."""
        session = self.get_current_session()
        if session:
            return session.clear_messages()
        return 0
    
    def optimize_memory(self, session_id: str = None) -> Dict[str, Any]:
        """Optimize memory usage by summarizing old messages."""
        target_session = session_id or self.current_session_id
        if not target_session or target_session not in self.sessions:
            return {"error": "Session not found"}
        
        session = self.sessions[target_session]
        
        # If session has fewer messages than limit, no optimization needed
        if len(session.messages) <= Config.MAX_MEMORY_MESSAGES:
            return {
                "optimized": False,
                "reason": "Session within memory limits",
                "message_count": len(session.messages)
            }
        
        # Keep recent messages and pinned messages
        messages_to_keep = Config.MAX_MEMORY_MESSAGES // 2
        recent_messages = session.messages[-messages_to_keep:]
        
        # Collect pinned messages that aren't in recent messages
        pinned_messages = []
        for idx in session.pinned_messages:
            if idx < len(session.messages) - messages_to_keep:
                pinned_messages.append(session.messages[idx])
        
        # Create summary of old messages (simplified for now)
        old_messages = session.messages[:-messages_to_keep]
        old_messages = [msg for i, msg in enumerate(old_messages) if i not in session.pinned_messages]
        
        if old_messages:
            summary_content = f"[Previous conversation summary: {len(old_messages)} messages exchanged]"
            summary_tokens = sum(msg.tokens for msg in old_messages)
            
            # Create new message list
            new_messages = []
            
            # Add summary message
            if old_messages:
                new_messages.append(MessageData(
                    role="system",
                    content=summary_content,
                    timestamp=old_messages[0].timestamp,
                    tokens=summary_tokens // 10,  # Compressed tokens
                    metadata={"type": "summary", "original_count": len(old_messages)}
                ))
            
            # Add pinned messages
            new_messages.extend(pinned_messages)
            
            # Add recent messages
            new_messages.extend(recent_messages)
            
            # Update session
            old_count = len(session.messages)
            session.messages = new_messages
            session.metadata.message_count = len(new_messages)
            session.metadata.total_tokens = sum(msg.tokens for msg in new_messages)
            
            # Update pinned message indices
            session.pinned_messages = []
            
            self.logger.info(f"Optimized session {target_session}: {old_count} -> {len(new_messages)} messages")
            
            return {
                "optimized": True,
                "old_count": old_count,
                "new_count": len(new_messages),
                "tokens_saved": summary_tokens - (summary_tokens // 10),
                "summary_created": True
            }
        
        return {
            "optimized": False,
            "reason": "No optimization possible",
            "message_count": len(session.messages)
        }
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        total_sessions = len(self.sessions)
        total_messages = sum(len(session.messages) for session in self.sessions.values())
        total_tokens = sum(session.metadata.total_tokens for session in self.sessions.values())
        
        current_session = self.get_current_session()
        current_stats = {}
        if current_session:
            current_stats = {
                "messages": len(current_session.messages),
                "tokens": current_session.metadata.total_tokens,
                "pinned": len(current_session.pinned_messages),
                "memory_usage": len(current_session.messages) / Config.MAX_MEMORY_MESSAGES * 100
            }
        
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "current_session": current_stats,
            "memory_limit": Config.MAX_MEMORY_MESSAGES
        }
    
    def search_messages(self, query: str, session_id: str = None) -> List[Dict[str, Any]]:
        """Search for messages containing the query."""
        results = []
        sessions_to_search = [session_id] if session_id else list(self.sessions.keys())
        
        for sid in sessions_to_search:
            if sid not in self.sessions:
                continue
                
            session = self.sessions[sid]
            for i, message in enumerate(session.messages):
                if query.lower() in message.content.lower():
                    results.append({
                        "session_id": sid,
                        "session_name": session.name,
                        "message_index": i,
                        "role": message.role,
                        "content": message.content,
                        "timestamp": message.timestamp,
                        "preview": self._get_message_preview(message.content, query)
                    })
        
        return results
    
    def _get_message_preview(self, content: str, query: str, context_chars: int = 100) -> str:
        """Get a preview of message content around the query match."""
        query_lower = query.lower()
        content_lower = content.lower()
        
        match_index = content_lower.find(query_lower)
        if match_index == -1:
            return content[:context_chars] + "..." if len(content) > context_chars else content
        
        start = max(0, match_index - context_chars // 2)
        end = min(len(content), match_index + len(query) + context_chars // 2)
        
        preview = content[start:end]
        if start > 0:
            preview = "..." + preview
        if end < len(content):
            preview = preview + "..."
        
        return preview
    
    def _check_auto_save(self) -> None:
        """Check if auto-save should be triggered."""
        if not self._auto_save_enabled:
            return
        
        current_time = time.time()
        if current_time - self._last_auto_save > Config.AUTO_SAVE_INTERVAL:
            self._auto_save()
            self._last_auto_save = current_time
    
    def _auto_save(self) -> None:
        """Perform auto-save (placeholder for future file persistence)."""
        # This would save to file in a real implementation
        self.logger.debug("Auto-save triggered (in-memory only)")
    
    def export_session(self, session_id: str = None, format_type: str = "json") -> Dict[str, Any]:
        """Export session data in specified format."""
        target_session = session_id or self.current_session_id
        if not target_session or target_session not in self.sessions:
            return {"error": "Session not found"}
        
        session = self.sessions[target_session]
        
        if format_type == "json":
            return session.export_data()
        elif format_type == "markdown":
            return self._export_as_markdown(session)
        elif format_type == "txt":
            return self._export_as_text(session)
        else:
            return {"error": f"Unsupported format: {format_type}"}
    
    def _export_as_markdown(self, session: ConversationSession) -> Dict[str, Any]:
        """Export session as markdown format."""
        lines = [
            f"# Chat Session: {session.name}",
            f"**Session ID:** {session.session_id}",
            f"**Created:** {session.metadata.created_at}",
            f"**Messages:** {len(session.messages)}",
            f"**Total Tokens:** {session.metadata.total_tokens}",
            f"**Model:** {session.metadata.model_used}",
            "",
            "---",
            ""
        ]
        
        for i, message in enumerate(session.messages):
            role_display = "🧑 **You**" if message.role == "user" else "🤖 **Claude**"
            timestamp = datetime.fromisoformat(message.timestamp.replace('Z', '+00:00')).strftime('%H:%M:%S')
            
            lines.append(f"## {role_display} [{timestamp}]")
            lines.append("")
            
            if message.role == "system":
                lines.append(f"*System: {message.content}*")
            else:
                lines.append(message.content)
            
            if i in session.pinned_messages:
                lines.append("📌 *Pinned*")
            
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return {"content": "\n".join(lines), "format": "markdown"}
    
    def _export_as_text(self, session: ConversationSession) -> Dict[str, Any]:
        """Export session as plain text format."""
        lines = [
            f"Chat Session: {session.name}",
            f"Session ID: {session.session_id}",
            f"Created: {session.metadata.created_at}",
            f"Messages: {len(session.messages)}",
            f"Total Tokens: {session.metadata.total_tokens}",
            f"Model: {session.metadata.model_used}",
            "",
            "=" * 80,
            ""
        ]
        
        for i, message in enumerate(session.messages):
            role_display = "You" if message.role == "user" else "Claude"
            timestamp = datetime.fromisoformat(message.timestamp.replace('Z', '+00:00')).strftime('%H:%M:%S')
            
            lines.append(f"[{timestamp}] {role_display}:")
            lines.append(message.content)
            
            if i in session.pinned_messages:
                lines.append("(Pinned)")
            
            lines.append("")
            lines.append("-" * 40)
            lines.append("")
        
        return {"content": "\n".join(lines), "format": "text"}