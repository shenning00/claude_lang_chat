"""Footer widget for the chat application."""

from textual.widgets import Footer as TextualFooter
from textual.reactive import reactive
from textual.containers import Horizontal
from textual.widgets import Static


class FooterWidget(TextualFooter):
    """Custom footer widget with shortcuts and additional information."""
    
    # Reactive attributes
    session_info = reactive("No session")
    token_count = reactive(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def on_mount(self) -> None:
        """Called when widget is mounted."""
        self.update_display()
    
    def update_session_info(self, session_name: str, message_count: int = 0):
        """Update session information."""
        self.session_info = f"{session_name} ({message_count} messages)"
        self.update_display()
    
    def update_token_count(self, count: int):
        """Update token count."""
        self.token_count = count
        self.update_display()
    
    def update_display(self):
        """Update the footer display with current information."""
        # The footer already shows key bindings, we can add session info to the right
        # This is done through CSS styling of the footer
        pass
    
    def watch_session_info(self, session_info: str) -> None:
        """Watch for changes to session info."""
        self.update_display()
    
    def watch_token_count(self, token_count: int) -> None:
        """Watch for changes to token count."""
        self.update_display()