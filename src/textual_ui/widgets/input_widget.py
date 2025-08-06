"""Multi-line input widget with Shift+Enter support for the chat application."""

from textual.widgets import TextArea, Button
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual.message import Message
from textual import events


class ChatInputWidgetSendMessage(Message):
    """Message sent when user wants to send chat input."""

    def __init__(self, content: str) -> None:
        self.content = content
        super().__init__()


class ChatInputWidgetToggleThinking(Message):
    """Message sent when user wants to toggle thinking mode."""

    def __init__(self) -> None:
        super().__init__()


# Keep old name for backwards compatibility
SendMessage = ChatInputWidgetSendMessage


class ChatTextArea(TextArea):
    """Internal TextArea component of the ChatInputWidget."""

    BINDINGS = [
        Binding("ctrl+enter", "new_line", "New Line", show=False),
        Binding("escape", "clear_input", "Clear", show=False),
        Binding("ctrl+a", "select_all", "Select All", show=False),
        Binding("ctrl+l", "clear_input", "Clear", show=False),
        Binding("ctrl+u", "clear_input", "Clear", show=False),
        Binding(
            "ctrl+k", "clear_from_cursor", "Clear From Cursor", show=False
        ),
    ]

    def __init__(self, **kwargs):
        super().__init__(show_line_numbers=False, **kwargs)
        self.can_focus = True

    def on_key(self, event: events.Key) -> None:
        if event.key == "shift+enter":
            print(f"{event}")

    def on_mount(self) -> None:
        """Called when widget is mounted."""
        self.border_title = "Message Input"
        self.border_subtitle = (
            "Shift+Enter: New Line | Use Submit Button or Enter to Send"
        )
        if hasattr(self, "placeholder"):
            self.placeholder = "Type your message here..."

    def action_new_line(self) -> None:
        """Insert a new line at cursor position."""
        self.insert("\n")

    def action_clear_input(self) -> None:
        """Clear all input text."""
        self.clear()
        self.move_cursor((0, 0))

    def action_select_all(self) -> None:
        """Select all text in the input."""
        self.select_all()

    def action_clear_from_cursor(self) -> None:
        """Clear text from cursor to end."""
        cursor_row, cursor_col = self.cursor_location
        lines = self.text.split("\n")

        if cursor_row < len(lines):
            lines[cursor_row] = lines[cursor_row][:cursor_col]
            lines = lines[: cursor_row + 1]
            self.text = "\n".join(lines)
            self.move_cursor((cursor_row, cursor_col))


class ChatInputWidget(Vertical):
    """Multi-line text input widget with Submit button and Thinking Mode toggle."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text_area = None
        self.submit_button = None
        self.thinking_button = None
        self.is_sending = False

    def compose(self):
        """Create child widgets."""
        yield ChatTextArea(id="chat-textarea")
        with Horizontal(id="button-container"):
            yield Button(
                "Submit Message", id="submit-button", variant="success"
            )
            yield Button(
                "Thinking: ON", id="thinking-button", variant="primary"
            )

    def on_mount(self) -> None:
        """Called when widget is mounted."""
        # Get references to child widgets after mounting
        self.text_area = self.query_one("#chat-textarea", ChatTextArea)
        self.submit_button = self.query_one("#submit-button", Button)
        self.thinking_button = self.query_one("#thinking-button", Button)

        # Update thinking button text based on current config
        self.update_thinking_button()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "submit-button":
            self.action_send_message()
        elif event.button.id == "thinking-button":
            self.action_toggle_thinking()

    def action_send_message(self) -> None:
        """Send the current message content."""
        if not self.text_area or self.is_sending:
            return

        content = self.text_area.text.strip()

        if content:
            # Set button to sending state
            self.set_sending_state(True)

            # Post message to parent
            self.post_message(ChatInputWidgetSendMessage(content))

            # Clear the input
            self.text_area.clear()
            self.text_area.move_cursor((0, 0))
        else:
            # If empty, just bell
            self.app.bell()

    def set_sending_state(self, sending: bool) -> None:
        """Update button state for sending/waiting."""
        if not self.submit_button:
            return

        self.is_sending = sending
        if sending:
            self.submit_button.label = "Sending..."
            self.submit_button.variant = "warning"
            self.submit_button.disabled = True
        else:
            self.submit_button.label = "Submit Message"
            self.submit_button.variant = "success"
            self.submit_button.disabled = False

    @property
    def text(self) -> str:
        """Get the current text content."""
        return self.text_area.text if self.text_area else ""

    def clear(self) -> None:
        """Clear the text area."""
        if self.text_area:
            self.text_area.clear()
            self.text_area.move_cursor((0, 0))
        # Reset button state
        self.set_sending_state(False)

    def action_toggle_thinking(self) -> None:
        """Toggle thinking mode."""
        self.post_message(ChatInputWidgetToggleThinking())

    def update_thinking_button(self) -> None:
        """Update thinking button text and style based on current config."""
        if not self.thinking_button:
            return

        # Import here to avoid circular imports
        try:
            from config import Config

            if Config.THINKING_MODE:
                self.thinking_button.label = "Thinking: ON"
                self.thinking_button.remove_class("thinking-off")
                self.thinking_button.add_class("thinking-on")
            else:
                self.thinking_button.label = "Thinking: OFF"
                self.thinking_button.remove_class("thinking-on")
                self.thinking_button.add_class("thinking-off")
        except Exception:
            # Fallback if config not available
            self.thinking_button.label = "Thinking: ?"
            self.thinking_button.remove_class("thinking-on")
            self.thinking_button.add_class("thinking-off")

    def focus(self) -> None:
        """Focus the text area."""
        if self.text_area:
            self.text_area.focus()

    def get_input_text(self) -> str:
        """Get the current input text."""
        return self.text

    def set_input_text(self, text: str) -> None:
        """Set the input text programmatically."""
        if self.text_area:
            self.text_area.text = text
            # Move cursor to end
            lines = text.split("\n")
            last_line = len(lines) - 1
            last_col = len(lines[-1]) if lines else 0
            self.text_area.move_cursor((last_line, last_col))

    def insert_text_at_cursor(self, text: str) -> None:
        """Insert text at the current cursor position."""
        if self.text_area:
            self.text_area.insert(text)

    def get_cursor_position(self) -> tuple[int, int]:
        """Get current cursor position as (row, col)."""
        return self.text_area.cursor_location if self.text_area else (0, 0)

    def set_placeholder_text(self, text: str) -> None:
        """Update the placeholder text."""
        if self.text_area and hasattr(self.text_area, "placeholder"):
            self.text_area.placeholder = text
