"""Setup screen for initial configuration."""

import os
from textual.screen import Screen
from textual.containers import Vertical, Horizontal, Center
from textual.widgets import Static, Input, Select, Button, Label
from textual.validation import Function

# Import backend components for configuration
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import Config, update_model, toggle_thinking_mode


class SetupScreen(Screen):
    """Initial setup screen for API key and model configuration."""
    
    CSS_PATH = "../styles/main.tcss"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_key = ""
        self.selected_model = ""
        
        # Available models from config (dynamically fetched)
        from config import get_available_models
        available_models_dict = get_available_models()
        self.available_models = [
            (model, description) for model, description in available_models_dict.items()
        ]
    
    def compose(self):
        """Compose the setup screen layout."""
        yield Static("Claude Chat Client Setup", id="setup-title")
        
        with Center():
            with Vertical(id="setup-form"):
                yield Label("Welcome! Let's get you set up.")
                yield Label("")
                
                yield Label("Anthropic API Key:")
                yield Input(
                    placeholder="Enter your API key (sk-ant-...)",
                    password=True,
                    id="api-key-input",
                    validators=[
                        Function(self.validate_api_key, "API key must start with 'sk-ant-'")
                    ]
                )
                yield Label("")
                
                yield Label("Select Claude Model:")
                yield Select(
                    options=[(model[0], model[1]) for model in self.available_models],
                    value=self.available_models[0][0],
                    id="model-select"
                )
                yield Label("")
                
                yield Label("Enable Thinking Mode:")
                yield Select(
                    options=[("true", "Yes"), ("false", "No")],
                    value="true",
                    id="thinking-select"
                )
                yield Label("")
                
                with Horizontal(id="setup-buttons"):
                    yield Button("Cancel", variant="default", id="cancel-btn")
                    yield Button("Continue", variant="primary", id="continue-btn")
    
    def validate_api_key(self, value: str) -> bool:
        """Validate API key format."""
        return value.startswith("sk-ant-") and len(value) > 10
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-btn":
            # Exit the application
            self.app.exit()
        
        elif event.button.id == "continue-btn":
            # Validate and save configuration
            if self.save_configuration():
                # Switch to main screen
                self.app.pop_screen()
    
    def save_configuration(self) -> bool:
        """Save the configuration and validate inputs."""
        # Get values from inputs
        api_key_input = self.query_one("#api-key-input", Input)
        model_select = self.query_one("#model-select", Select)
        thinking_select = self.query_one("#thinking-select", Select)
        
        self.api_key = api_key_input.value
        self.selected_model = model_select.value
        thinking_mode = thinking_select.value == "true"
        
        # Validate API key
        if not self.validate_api_key(self.api_key):
            # Show error
            api_key_input.add_class("error")
            self._show_error("Invalid API key format. Must start with 'sk-ant-'")
            return False
        
        try:
            # Save configuration
            Config.ANTHROPIC_API_KEY = self.api_key
            os.environ["ANTHROPIC_API_KEY"] = self.api_key
            
            # Update model if different
            if self.selected_model != Config.CLAUDE_MODEL:
                update_model(self.selected_model)
            
            # Update thinking mode if different
            if thinking_mode != Config.THINKING_MODE:
                toggle_thinking_mode()
            
            # Reinitialize the app's backend
            if hasattr(self.app, '_initialize_backend'):
                self.app._initialize_backend()
            
            # Show success message
            self._show_success(f"✅ Configuration saved!\nModel: {self.selected_model}\nThinking Mode: {thinking_mode}")
            
            # Remove error styling
            api_key_input.remove_class("error")
            
            return True
            
        except Exception as e:
            self._show_error(f"Failed to save configuration: {str(e)}")
            return False
    
    def _show_success(self, message: str) -> None:
        """Show success message."""
        try:
            # Remove any existing message
            existing = self.query("#success-message")
            if existing:
                existing[0].remove()
        except:
            pass
        
        status_label = Static(message, id="success-message")
        status_label.add_class("success-message")
        
        # Add success message
        form = self.query_one("#setup-form")
        form.mount(status_label)
    
    def _show_error(self, message: str) -> None:
        """Show error message."""
        try:
            # Remove any existing message
            existing = self.query("#error-message")
            if existing:
                existing[0].remove()
        except:
            pass
        
        error_label = Static(f"❌ {message}", id="error-message")
        error_label.add_class("error-message")
        
        # Add error message
        form = self.query_one("#setup-form")
        form.mount(error_label)
    
    def on_mount(self) -> None:
        """Called when screen is mounted."""
        # Focus the API key input
        api_key_input = self.query_one("#api-key-input", Input)
        api_key_input.focus()