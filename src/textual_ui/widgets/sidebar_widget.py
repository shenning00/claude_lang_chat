"""Sidebar widget for sessions, commands, and status information."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, ListView, ListItem, Label, Button
from textual.message import Message
from rich.text import Text


class SessionSelected(Message):
    """Message sent when a session is selected."""
    
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__()


class NewSessionRequested(Message):
    """Message sent when user wants to create a new session."""
    
    def __init__(self) -> None:
        super().__init__()


class ModelSelectionRequested(Message):
    """Message sent when user wants to select a model."""
    
    def __init__(self) -> None:
        super().__init__()


class DeleteSessionRequested(Message):
    """Message sent when user wants to delete the selected session."""
    
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__()


class SwitchSessionRequested(Message):
    """Message sent when user wants to switch to the selected session."""
    
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__()


class SessionItem(ListItem):
    """Individual session item in the sidebar."""
    
    def __init__(self, session_id: str, session_name: str, message_count: int = 0, 
                 last_activity: Optional[str] = None, is_active: bool = False, 
                 model_used: str = None, **kwargs):
        self.session_id = session_id
        self.session_name = session_name
        self.message_count = message_count
        self.last_activity = last_activity or datetime.now().strftime("%H:%M")
        self.is_active = is_active
        self.model_used = model_used or "Unknown"
        
        # Create display text
        display_text = self._create_display_text()
        
        super().__init__(Static(display_text), **kwargs)
        
        if is_active:
            self.add_class("session-active")
    
    def _create_display_text(self) -> str:
        """Create the display text for this session."""
        status_indicator = "● " if self.is_active else "○ "
        name_truncated = self.session_name[:15] + "..." if len(self.session_name) > 18 else self.session_name
        
        # Shorten model name for display
        model_display = self.model_used.replace("claude-", "").replace("-20", " '")
        if len(model_display) > 15:
            model_display = model_display[:12] + "..."
        
        thinking_indicator = " 🧠" if "claude-3-7" in self.model_used else ""
        
        return f"{status_indicator}{name_truncated}\n{self.message_count} msgs | {model_display}{thinking_indicator}"
    
    def update_info(self, message_count: int, last_activity: Optional[str] = None, is_active: bool = None):
        """Update session information."""
        self.message_count = message_count
        if last_activity:
            self.last_activity = last_activity
        if is_active is not None:
            self.is_active = is_active
            if is_active:
                self.add_class("session-active")
            else:
                self.remove_class("session-active")
        
        # Update display
        self.query_one(Static).update(self._create_display_text())


# Removed CommandItem - no longer needed


class StatusWidget(Static):
    """Status information widget."""
    
    def __init__(self, **kwargs):
        self.connection_status = "Disconnected"
        self.current_model = "Unknown"
        self.thinking_mode = False
        self.token_count = 0
        
        super().__init__(self._create_status_text(), **kwargs)
        self.add_class("status-widget")
    
    def _create_status_text(self) -> str:
        """Create the status display text."""
        if self.connection_status == "Connected":
            status_icon = "🟢"
        elif self.connection_status == "NO MODELS":
            status_icon = "🔴"
        else:
            status_icon = "🔴"
            
        thinking_icon = "🧠" if self.thinking_mode else ""
        
        if self.connection_status == "NO MODELS":
            lines = [f"{status_icon} NO MODELS"]
        else:
            lines = [
                f"{status_icon} {self.connection_status}",
                f"Model: {self.current_model}",
            ]
            
            if self.thinking_mode:
                lines.append(f"{thinking_icon} Thinking Mode")
            
            if self.token_count > 0:
                lines.append(f"Tokens: ~{self.token_count}")
        
        return "\n".join(lines)
    
    def update_status(self, connection_status: Optional[str] = None, 
                     current_model: Optional[str] = None,
                     thinking_mode: Optional[bool] = None,
                     token_count: Optional[int] = None):
        """Update status information."""
        if connection_status is not None:
            self.connection_status = connection_status
        if current_model is not None:
            self.current_model = current_model
        if thinking_mode is not None:
            self.thinking_mode = thinking_mode
        if token_count is not None:
            self.token_count = token_count
        
        self.update(self._create_status_text())


class SidebarWidget(Vertical):
    """Main sidebar widget containing sessions, commands, and status."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.current_session_id: Optional[str] = None
    
    def compose(self):
        """Compose the sidebar layout."""
        # Sessions section
        yield Static("Sessions", classes="sidebar-header")
        yield ListView(id="sessions-list", classes="sidebar-content")
        
        # Session management buttons
        with Horizontal(id="session-buttons"):
            yield Button("New", id="new-session-btn", variant="success")
            yield Button("Switch", id="switch-session-btn", variant="primary")
            yield Button("Delete", id="delete-session-btn", variant="error")
        
        # Model selection section
        yield Static("Model", classes="sidebar-header")
        with Vertical(id="model-section"):
            yield Button("Select Model", id="select-model-btn", variant="default")
            yield Static("Current: Loading...", id="current-model-display", classes="model-info")
        
        # Status section
        yield Static("Status", classes="sidebar-header")
        yield StatusWidget(id="status-widget")
    
    def on_mount(self) -> None:
        """Called when widget is mounted."""
        self.border_title = "Navigation"
        
        # Add initial session if none exist
        if not self.sessions:
            self.add_session("default", "Default Session", is_current=True)
    
    def add_session(self, session_id: str, session_name: str, message_count: int = 0,
                   last_activity: Optional[str] = None, is_current: bool = False, 
                   model_used: str = None):
        """Add a new session to the sidebar."""
        # Store session data
        self.sessions[session_id] = {
            "name": session_name,
            "message_count": message_count,
            "last_activity": last_activity or datetime.now().strftime("%H:%M"),
            "is_current": is_current,
            "model_used": model_used or "Unknown"
        }
        
        # Update current session tracking
        if is_current:
            self.current_session_id = session_id
            # Mark other sessions as not current
            for sid, session_data in self.sessions.items():
                if sid != session_id:
                    session_data["is_current"] = False
        
        # Create and add session item
        session_item = SessionItem(
            session_id,
            session_name,
            message_count,
            last_activity,
            is_current,
            model_used
        )
        
        sessions_list = self.query_one("#sessions-list", ListView)
        sessions_list.append(session_item)
        
        # Update sessions header
        self._update_sessions_header()
    
    def remove_session(self, session_id: str):
        """Remove a session from the sidebar."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            
            # Remove from list view
            sessions_list = self.query_one("#sessions-list", ListView)
            for item in sessions_list.children:
                if isinstance(item, SessionItem) and item.session_id == session_id:
                    item.remove()
                    break
            
            # If this was current session, select another
            if self.current_session_id == session_id:
                if self.sessions:
                    # Select first available session
                    first_session_id = next(iter(self.sessions))
                    self.set_current_session(first_session_id)
                else:
                    self.current_session_id = None
            
            self._update_sessions_header()
    
    def set_current_session(self, session_id: str):
        """Set the current active session."""
        if session_id not in self.sessions:
            return
        
        # Update session data
        old_current = self.current_session_id
        self.current_session_id = session_id
        
        for sid, session_data in self.sessions.items():
            session_data["is_current"] = (sid == session_id)
        
        # Update list items
        sessions_list = self.query_one("#sessions-list", ListView)
        for item in sessions_list.children:
            if isinstance(item, SessionItem):
                item.update_info(
                    item.message_count,
                    item.last_activity,
                    item.session_id == session_id
                )
    
    def update_session_info(self, session_id: str, message_count: int, 
                           last_activity: Optional[str] = None):
        """Update information for a specific session."""
        if session_id not in self.sessions:
            return
        
        # Update stored data
        self.sessions[session_id]["message_count"] = message_count
        if last_activity:
            self.sessions[session_id]["last_activity"] = last_activity
        
        # Update list item
        sessions_list = self.query_one("#sessions-list", ListView)
        for item in sessions_list.children:
            if isinstance(item, SessionItem) and item.session_id == session_id:
                item.update_info(message_count, last_activity)
                break
    
    def _update_sessions_header(self):
        """Update the sessions header with count."""
        count = len(self.sessions)
        headers = self.query(".sidebar-header")
        if headers:
            sessions_header = headers[0]  # First header is sessions
            sessions_header.update(f"Sessions ({count})")
    
    def update_status(self, **kwargs):
        """Update the status widget."""
        status_widget = self.query_one("#status-widget", StatusWidget)
        status_widget.update_status(**kwargs)
    
    def update_current_model(self, model_name: str):
        """Update the current model display."""
        try:
            model_display = self.query_one("#current-model-display", Static)
            # Truncate long model names for display
            display_name = model_name.replace("claude-", "").replace("-20", " '")
            if len(display_name) > 25:
                display_name = display_name[:22] + "..."
            model_display.update(f"Current: {display_name}")
        except Exception:
            # Widget might not be mounted yet
            pass
    
    def get_current_session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self.current_session_id
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific session."""
        return self.sessions.get(session_id)
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get all sessions information."""
        return self.sessions.copy()
    
    def clear_sessions(self) -> None:
        """Clear all sessions from the sidebar."""
        self.sessions.clear()
        self.current_session_id = None
        
        # Clear the sessions list view
        sessions_list = self.query_one("#sessions-list", ListView)
        sessions_list.clear()
        
        # Update header
        self._update_sessions_header()
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle selection in list views."""
        if event.list_view.id == "sessions-list":
            # Session selected
            if isinstance(event.item, SessionItem):
                self.post_message(SessionSelected(event.item.session_id))
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "new-session-btn":
            self.post_message(NewSessionRequested())
        elif event.button.id == "select-model-btn":
            self.post_message(ModelSelectionRequested())
        elif event.button.id == "switch-session-btn":
            # Get currently selected session for switching
            sessions_list = self.query_one("#sessions-list", ListView)
            if sessions_list.index is not None and sessions_list.index >= 0:
                # Get the selected session item
                selected_item = sessions_list.children[sessions_list.index]
                if isinstance(selected_item, SessionItem):
                    self.post_message(SwitchSessionRequested(selected_item.session_id))
        elif event.button.id == "delete-session-btn":
            # Get currently selected session for deletion
            sessions_list = self.query_one("#sessions-list", ListView)
            if sessions_list.index is not None and sessions_list.index >= 0:
                # Get the selected session item
                selected_item = sessions_list.children[sessions_list.index]
                if isinstance(selected_item, SessionItem):
                    self.post_message(DeleteSessionRequested(selected_item.session_id))