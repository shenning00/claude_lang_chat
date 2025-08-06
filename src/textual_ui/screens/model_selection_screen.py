"""Model selection screen for choosing Claude models."""

from typing import List, Tuple, Optional
from textual.app import ComposeResult
from textual.containers import Center, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Static, Button, ListView, ListItem, Label
from textual.message import Message


class ModelSelected(Message):
    """Message sent when a model is selected."""
    
    def __init__(self, model_id: str, model_description: str) -> None:
        self.model_id = model_id
        self.model_description = model_description
        super().__init__()


class ModelSelectionCancelled(Message):
    """Message sent when model selection is cancelled."""
    
    def __init__(self) -> None:
        super().__init__()


class ModelItem(ListItem):
    """A list item representing a model."""
    
    def __init__(self, model_id: str, description: str, is_current: bool = False):
        self.model_id = model_id
        self.description = description
        self.is_current = is_current
        
        # Create display text
        prefix = "→ " if is_current else "  "
        thinking_indicator = " 🧠" if "claude-3-7" in model_id else ""
        display_text = f"{prefix}{model_id}{thinking_indicator}\n    {description}"
        
        super().__init__(Label(display_text))
        
        if is_current:
            self.add_class("current-model")


class ModelSelectionScreen(ModalScreen):
    """Modal screen for selecting a Claude model."""
    
    DEFAULT_CSS = """
    ModelSelectionScreen {
        align: center middle;
    }
    
    #model-selection-dialog {
        width: 80;
        height: 20;
        border: thick $primary 80%;
        background: $surface;
    }
    
    #model-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    #model-list {
        height: 12;
        border: solid $accent;
        margin: 1 2;
    }
    
    .current-model {
        background: $accent-darken-1;
        color: $text;
    }
    
    #button-container {
        align: center middle;
        margin-top: 1;
    }
    
    Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, available_models: List[Tuple[str, str]], current_model: str = None):
        super().__init__()
        self.available_models = available_models
        self.current_model = current_model
        self.selected_model: Optional[Tuple[str, str]] = None
    
    def compose(self) -> ComposeResult:
        """Compose the model selection dialog."""
        with Center():
            with Vertical(id="model-selection-dialog"):
                yield Static("Select Claude Model", id="model-title")
                yield ListView(id="model-list")
                with Horizontal(id="button-container"):
                    yield Button("Select", id="select-btn", variant="primary")
                    yield Button("Cancel", id="cancel-btn", variant="default")
    
    def on_mount(self) -> None:
        """Called when screen is mounted."""
        model_list = self.query_one("#model-list", ListView)
        
        # Add model items to the list
        for model_id, description in self.available_models:
            is_current = model_id == self.current_model
            model_item = ModelItem(model_id, description, is_current)
            model_list.append(model_item)
            
            # Pre-select current model
            if is_current:
                self.selected_model = (model_id, description)
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle model selection."""
        if isinstance(event.item, ModelItem):
            self.selected_model = (event.item.model_id, event.item.description)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "select-btn":
            if self.selected_model:
                self.post_message(ModelSelected(self.selected_model[0], self.selected_model[1]))
                self.dismiss()
        elif event.button.id == "cancel-btn":
            self.post_message(ModelSelectionCancelled())
            self.dismiss()
    
    def on_key(self, event) -> None:
        """Handle key presses."""
        if event.key == "escape":
            self.post_message(ModelSelectionCancelled())
            self.dismiss()
        elif event.key == "enter":
            if self.selected_model:
                self.post_message(ModelSelected(self.selected_model[0], self.selected_model[1]))
                self.dismiss()