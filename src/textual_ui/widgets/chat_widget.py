"""Chat messages display widget for the chat application."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from textual.containers import ScrollableContainer, Vertical
from textual.widgets import Static, Markdown
from textual.message import Message
from rich.text import Text
from rich.markdown import Markdown as RichMarkdown


class MessageAdded(Message):
    """Message sent when a new chat message is added."""
    
    def __init__(self, role: str, content: str, timestamp: Optional[str] = None) -> None:
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now().strftime("%H:%M:%S")
        super().__init__()


class ChatMessage(Static):
    """Individual chat message widget."""
    
    def __init__(self, role: str, content: str, timestamp: str, **kwargs):
        self.role = role
        self.content = content
        self.timestamp = timestamp
        
        # Format the message content
        formatted_content = self._format_message_content()
        
        super().__init__(formatted_content, **kwargs)
        self.add_class(f"message-{role}")
    
    def _format_message_content(self) -> str:
        """Format the message content with timestamp and role."""
        role_display = {
            "user": "You",
            "assistant": "Claude", 
            "system": "System"
        }.get(self.role, self.role.title())
        
        return f"[{self.timestamp}] {role_display}:\n{self.content}"


class MarkdownMessage(Markdown):
    """Markdown-rendered chat message widget."""
    
    def __init__(self, role: str, content: str, timestamp: str, **kwargs):
        self.role = role
        self.content = content
        self.timestamp = timestamp
        
        # Add timestamp and role to markdown content
        role_display = {
            "user": "You",
            "assistant": "Claude",
            "system": "System"
        }.get(self.role, self.role.title())
        
        formatted_content = f"**[{timestamp}] {role_display}:**\n\n{content}"
        
        super().__init__(formatted_content, **kwargs)
        self.add_class(f"message-{role}")


class ChatMessagesWidget(ScrollableContainer):
    """Scrollable container for chat messages with auto-scroll and formatting."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messages: List[Dict[str, Any]] = []
        self.max_messages = 1000  # Limit to prevent memory issues
        self.auto_scroll = True
        self.show_timestamps = True
        
    def on_mount(self) -> None:
        """Called when widget is mounted."""
        self.border_title = "Chat Messages"
        self.can_focus = True
        
        # Add welcome message
        self.add_system_message("Welcome to Claude Chat Client! Type a message to get started.")
    
    def add_message(self, role: str, content: str, timestamp: Optional[str] = None) -> None:
        """Add a new message to the chat."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Store message data
        message_data = {
            "role": role,
            "content": content, 
            "timestamp": timestamp,
            "id": len(self.messages)
        }
        self.messages.append(message_data)
        
        # Create appropriate widget based on content
        message_widget = self._create_message_widget(role, content, timestamp)
        
        # Mount the widget
        self.mount(message_widget)
        
        # Auto-scroll to bottom if enabled
        if self.auto_scroll:
            self.scroll_end(animate=True)
        
        # Cleanup old messages if we exceed limit
        if len(self.messages) > self.max_messages:
            self._cleanup_old_messages()
        
        # Update border subtitle with message count
        self.border_subtitle = f"{len(self.messages)} messages"
        
        # Post message to parent for potential processing
        self.post_message(MessageAdded(role, content, timestamp))
    
    def _create_message_widget(self, role: str, content: str, timestamp: str):
        """Create appropriate widget based on message content."""
        # Check if content contains markdown (code blocks, headers, etc.)
        has_markdown = any(marker in content for marker in ['```', '**', '##', '###', '*', '_', '`'])
        
        if has_markdown:
            return MarkdownMessage(role, content, timestamp)
        else:
            return ChatMessage(role, content, timestamp)
    
    def add_user_message(self, content: str, timestamp: Optional[str] = None) -> None:
        """Convenience method to add a user message."""
        self.add_message("user", content, timestamp)
    
    def add_assistant_message(self, content: str, timestamp: Optional[str] = None) -> None:
        """Convenience method to add an assistant message."""
        self.add_message("assistant", content, timestamp)
    
    def add_system_message(self, content: str, timestamp: Optional[str] = None) -> int:
        """Convenience method to add a system message. Returns message ID."""
        message_id = len(self.messages)
        self.add_message("system", content, timestamp)
        return message_id
    
    def add_typing_indicator(self, message: str = "🤔 Claude is thinking...") -> int:
        """Add a typing indicator message that can be removed later."""
        return self.add_system_message(message)
    
    def update_typing_indicator(self, message_id: int, message: str) -> bool:
        """Update a typing indicator message."""
        try:
            if 0 <= message_id < len(self.messages):
                # Update the message data
                self.messages[message_id]["content"] = message
                
                # Update the widget
                children_list = list(self.children)
                if message_id < len(children_list):
                    widget = children_list[message_id]
                    if hasattr(widget, 'update'):
                        widget.update(self._format_system_message(message))
                    return True
            return False
        except:
            return False
    
    def _format_system_message(self, content: str) -> str:
        """Format a system message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"[{timestamp}] System:\n{content}"
    
    def remove_message(self, message_id: int) -> bool:
        """Remove a message by its ID. Returns True if successful."""
        try:
            if 0 <= message_id < len(self.messages):
                # Remove from messages list
                self.messages.pop(message_id)
                
                # Remove the corresponding widget
                children_list = list(self.children)
                if message_id < len(children_list):
                    children_list[message_id].remove()
                    return True
            return False
        except:
            return False
    
    def clear_messages(self) -> None:
        """Clear all messages from the chat."""
        self.messages.clear()
        # Remove all child widgets
        for child in list(self.children):
            child.remove()
        
        self.border_subtitle = "0 messages"
        
        # Add a system message indicating clear
        self.add_system_message("Chat cleared.")
    
    def _cleanup_old_messages(self) -> None:
        """Remove old messages to prevent memory issues."""
        # Remove oldest 100 messages
        messages_to_remove = 100
        
        # Remove from messages list
        self.messages = self.messages[messages_to_remove:]
        
        # Remove widgets (oldest children)
        children_list = list(self.children)
        for i in range(min(messages_to_remove, len(children_list))):
            children_list[i].remove()
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all current messages."""
        return self.messages.copy()
    
    def get_last_message(self) -> Optional[Dict[str, Any]]:
        """Get the last message."""
        return self.messages[-1] if self.messages else None
    
    def get_messages_by_role(self, role: str) -> List[Dict[str, Any]]:
        """Get all messages by a specific role."""
        return [msg for msg in self.messages if msg["role"] == role]
    
    def search_messages(self, query: str) -> List[Dict[str, Any]]:
        """Search messages for a specific query."""
        query_lower = query.lower()
        return [
            msg for msg in self.messages 
            if query_lower in msg["content"].lower()
        ]
    
    def export_messages(self, format: str = "text") -> str:
        """Export messages in specified format."""
        if format == "text":
            return self._export_as_text()
        elif format == "markdown":
            return self._export_as_markdown()
        elif format == "json":
            import json
            return json.dumps(self.messages, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_as_text(self) -> str:
        """Export messages as plain text."""
        lines = []
        for msg in self.messages:
            role_display = {
                "user": "You",
                "assistant": "Claude",
                "system": "System"
            }.get(msg["role"], msg["role"].title())
            
            lines.append(f"[{msg['timestamp']}] {role_display}:")
            lines.append(msg["content"])
            lines.append("")  # Empty line between messages
        
        return "\n".join(lines)
    
    def _export_as_markdown(self) -> str:
        """Export messages as markdown."""
        lines = ["# Chat Export", "", f"Generated on: {datetime.now()}", ""]
        
        for msg in self.messages:
            role_display = {
                "user": "**You**",
                "assistant": "**Claude**", 
                "system": "**System**"
            }.get(msg["role"], f"**{msg['role'].title()}**")
            
            lines.append(f"### {role_display} - {msg['timestamp']}")
            lines.append("")
            lines.append(msg["content"])
            lines.append("")
        
        return "\n".join(lines)
    
    def toggle_auto_scroll(self) -> bool:
        """Toggle auto-scroll and return new state."""
        self.auto_scroll = not self.auto_scroll
        return self.auto_scroll
    
    def scroll_to_bottom(self) -> None:
        """Manually scroll to bottom."""
        self.scroll_end(animate=True)
    
    def scroll_to_top(self) -> None:
        """Manually scroll to top."""
        self.scroll_home(animate=True)
    
    def update_message_count_display(self) -> None:
        """Update the message count in the border subtitle."""
        count = len(self.messages)
        if count == 0:
            self.border_subtitle = "No messages"
        elif count == 1:
            self.border_subtitle = "1 message"
        else:
            self.border_subtitle = f"{count} messages"