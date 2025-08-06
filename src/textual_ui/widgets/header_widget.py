"""Header widget for the chat application."""

from textual.widgets import Header as TextualHeader
from textual.reactive import reactive


class HeaderWidget(TextualHeader):
    """Custom header widget with connection status and model information."""
    
    # Reactive attributes that automatically update the display
    connection_status = reactive("Disconnected")
    model_name = reactive("Unknown")
    thinking_mode = reactive(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def compose(self):
        """Header is a built-in widget, so we don't need to compose children."""
        return super().compose()
    
    def on_mount(self) -> None:
        """Called when widget is mounted."""
        self.update_display()
    
    def update_connection_status(self, status: str):
        """Update the connection status."""
        self.connection_status = status
        self.update_display()
    
    def update_model_info(self, model_name: str, thinking_mode: bool = False):
        """Update the model information."""
        self.model_name = model_name
        self.thinking_mode = thinking_mode
        self.update_display()
    
    def update_display(self):
        """Update the header display with current information."""
        if self.connection_status == "Connected":
            status_icon = "🟢"
        elif self.connection_status == "NO MODELS":
            status_icon = "🔴"
        else:
            status_icon = "🔴"
            
        thinking_icon = " 🧠" if self.thinking_mode else ""
        
        # Update sub_title with status information
        if self.connection_status == "NO MODELS":
            self.sub_title = f"{status_icon} NO MODELS"
        else:
            self.sub_title = f"{status_icon} {self.connection_status} | {self.model_name}{thinking_icon}"
    
    def watch_connection_status(self, status: str) -> None:
        """Watch for changes to connection status."""
        self.update_display()
    
    def watch_model_name(self, model_name: str) -> None:
        """Watch for changes to model name."""
        self.update_display()
    
    def watch_thinking_mode(self, thinking_mode: bool) -> None:
        """Watch for changes to thinking mode."""
        self.update_display()