"""Help screen for the chat application."""

from textual.screen import ModalScreen
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Button, Markdown


class HelpScreen(ModalScreen):
    """Modal help screen with usage information."""
    
    CSS_PATH = "../styles/main.tcss"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.help_content = """
# Claude Chat Client Help

## Getting Started
Welcome to the Claude Chat Client! This application provides a full-screen terminal interface for chatting with Anthropic's Claude AI models.

## Basic Usage

### Sending Messages
- **Type your message** in the input area at the bottom
- **Press Enter** to send your message to Claude
- **Press Shift+Enter** to add a new line without sending

### Navigation
- **Tab** - Move between different areas of the interface
- **Arrow keys** - Navigate within text areas and lists
- **Page Up/Down** - Scroll through chat history

## Commands
You can use the following commands by typing them in the input field:

### Session Management
- `/new [name]` - Create a new chat session
- `/sessions` - List all available sessions
- `/switch <id>` - Switch to a specific session
- `/rename <name>` - Rename the current session
- `/delete <id>` - Delete a session

### Chat Management
- `/clear` - Clear the current chat history
- `/export <format>` - Export chat (formats: text, markdown, json)
- `/search <query>` - Search through chat history

### Settings
- `/model [name]` - Show or change the Claude model
- `/thinking [on|off]` - Toggle thinking mode
- `/config` - Show current configuration

### Utility
- `/help` - Show this help screen
- `/quit` - Exit the application

## Keyboard Shortcuts
- **Ctrl+C** - Quit application
- **Ctrl+H** - Show help
- **Ctrl+N** - New session
- **Ctrl+S** - Show sessions list

## Features

### Multi-line Input
The input area supports multi-line text:
- Use **Shift+Enter** to add new lines
- Use **Enter** to send your message
- The input area will expand as you type

### Markdown Support
Claude's responses support full markdown formatting:
- **Bold text**, *italic text*
- `Code snippets` and code blocks
- Lists and headers
- Blockquotes

### Session Management
- Create multiple chat sessions for different topics
- Switch between sessions using the sidebar
- Each session maintains its own conversation history

### Export Options
Save your conversations in multiple formats:
- **Text** - Plain text format
- **Markdown** - Formatted text with styling
- **JSON** - Machine-readable format with metadata

## Tips
- Use the sidebar to quickly navigate between sessions
- Commands can be clicked in the sidebar for quick access
- The status area shows your connection and model information
- Chat history is automatically saved and restored

## Troubleshooting
- If the interface seems unresponsive, try pressing **Tab** to change focus
- If text appears garbled, try resizing your terminal window
- For API issues, check your internet connection and API key

Press **Escape** or click **Close** to return to the chat.
"""
    
    def compose(self):
        """Compose the help screen layout."""
        with Vertical(id="help-container"):
            yield Static("Help & Documentation", id="help-title")
            yield Markdown(self.help_content, id="help-content")
            
            with Horizontal(id="help-buttons"):
                yield Button("Close", variant="primary", id="close-btn")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close-btn":
            self.dismiss()
    
    def on_key(self, event) -> None:
        """Handle key presses."""
        if event.key == "escape":
            self.dismiss()