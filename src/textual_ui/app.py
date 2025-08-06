"""Main Textual application for Claude Chat Client."""

import sys
import asyncio
from pathlib import Path
from typing import Optional
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from .widgets import ChatMessagesWidget, ChatInputWidget, SidebarWidget, HeaderWidget, FooterWidget
from .widgets.input_widget import ChatInputWidgetSendMessage, ChatInputWidgetToggleThinking
from .widgets.sidebar_widget import NewSessionRequested, DeleteSessionRequested, SwitchSessionRequested, ModelSelectionRequested, SessionSelected
from .screens import SetupScreen, HelpScreen
from .screens.model_selection_screen import ModelSelectionScreen, ModelSelected, ModelSelectionCancelled

# Import backend components
from config import Config, setup_config
from memory_manager import MemoryManager
from llm_handler import LLMHandler


class ClaudeChatApp(App):
    """Main Textual application for Claude Chat Client."""
    
    CSS_PATH = str(Path(__file__).parent / "styles" / "main.tcss")
    TITLE = "Claude Chat Client"
    SUB_TITLE = "Powered by Anthropic Claude"
    
    BINDINGS = [
        ("ctrl+q", "quit_app", "Quit"),
        ("ctrl+h", "help", "Help"),
        ("f1", "help", "Help"),
        ("ctrl+n", "new_session", "New Session"),
    ]
    
    def __init__(self):
        super().__init__()
        # Initialize backend components
        self.memory_manager: Optional[MemoryManager] = None
        self.llm_handler: Optional[LLMHandler] = None
        self.config_initialized = False
        self.current_session_id: Optional[str] = None
        self.connection_status = "Disconnected"
        self.init_error: Optional[str] = None
        self._initialize_backend()
    
    def _initialize_backend(self) -> None:
        """Initialize backend components."""
        try:
            # Check if API key is available (without interactive prompt)
            if not Config.validate_api_key():
                self.config_initialized = False
                self.connection_status = "NO MODELS"
                return
            
            self.config_initialized = True
            
            # Check if models are available first
            from config import get_available_models
            available_models = get_available_models()
            
            if not available_models:
                self.connection_status = "NO MODELS"
                # Don't initialize backend components if no models available
                return
                
            # Initialize backend components
            self.memory_manager = MemoryManager()
            self.llm_handler = LLMHandler()
            
            # Test the connection to Claude
            try:
                # Simple connection test
                self.llm_handler.estimate_tokens("test")
                self.connection_status = "Connected"
            except Exception as e:
                self.connection_status = "Connection Error"
                # Still proceed but mark as error
            
            # Create default session if none exists
            if not self.memory_manager.sessions:
                self.current_session_id = self.memory_manager.create_session("Default Session")
            else:
                # Get the first available session
                self.current_session_id = list(self.memory_manager.sessions.keys())[0]
                    
        except Exception as e:
            self.config_initialized = False
            self.connection_status = "Initialization Error"
            self.init_error = str(e)
            # Error will be handled in on_mount
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield HeaderWidget()
        
        with Horizontal(id="main-container"):
            yield SidebarWidget(id="sidebar")
            with Vertical(id="chat-container"):
                yield ChatMessagesWidget(id="chat-messages")
                yield ChatInputWidget(id="chat-input")
        
        yield FooterWidget()
    
    def on_mount(self) -> None:
        """Called when app starts."""
        self.title = self.TITLE
        self.sub_title = self.SUB_TITLE
        
        # Check if we need to show setup screen
        if not self.config_initialized:
            # Show setup screen first
            self.push_screen(SetupScreen())
        else:
            # Initialize UI with current session data
            self._load_current_session()
            
            # Show initialization errors if any
            if hasattr(self, 'init_error') and self.init_error:
                chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
                chat_widget.add_system_message(f"⚠️ Initialization warning: {self.init_error}")
            
            # Focus the input widget by default
            self.call_after_refresh(self._focus_input)
    
    def on_screen_resume(self, screen) -> None:
        """Called when returning from a screen."""
        # If returning from setup screen, reload session data
        if hasattr(screen, '__class__') and 'SetupScreen' in str(screen.__class__):
            if self.config_initialized:
                self._load_current_session()
                # Focus the input widget
                self.call_after_refresh(self._focus_input)
    
    def _load_current_session(self) -> None:
        """Load the current session data into the UI."""
        if not self.memory_manager or not self.current_session_id:
            return
            
        # Load session data into sidebar
        sidebar = self.query_one("#sidebar", SidebarWidget)
        sidebar.clear_sessions()
        
        for session_id, session in self.memory_manager.sessions.items():
            is_current = session_id == self.current_session_id
            sidebar.add_session(
                session_id, 
                session.name, 
                is_current=is_current,
                message_count=session.metadata.message_count,
                model_used=session.metadata.model_used
            )
        
        # Get current session model
        session = self.memory_manager.get_current_session()
        current_model = session.metadata.model_used if session else Config.CLAUDE_MODEL
        thinking_mode = "claude-3-7" in current_model if current_model else Config.THINKING_MODE
        
        # Update status information
        sidebar.update_status(
            connection_status=self.connection_status,
            current_model=current_model,
            thinking_mode=thinking_mode
        )
        
        # Update current model display in sidebar
        sidebar.update_current_model(current_model)
        
        # Update header
        header = self.query_one(HeaderWidget)
        header.update_connection_status(self.connection_status)
        header.update_model_info(current_model, thinking_mode)
        
        # Load messages into chat area
        chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
        chat_widget.clear_messages()
        
        if session:
            for message in session.messages:
                if message.role == "user":
                    chat_widget.add_user_message(message.content, message.timestamp)
                elif message.role == "assistant":
                    chat_widget.add_assistant_message(message.content, message.timestamp)
                elif message.role == "system":
                    chat_widget.add_system_message(message.content, message.timestamp)
    
    def _update_model_display(self) -> None:
        """Update the model display in sidebar and header to reflect current session."""
        if not self.memory_manager:
            return
        
        # Get current session model
        session = self.memory_manager.get_current_session()
        current_model = session.metadata.model_used if session else Config.CLAUDE_MODEL
        thinking_mode = "claude-3-7" in current_model if current_model else Config.THINKING_MODE
        
        # Update sidebar model display
        sidebar = self.query_one("#sidebar", SidebarWidget)
        sidebar.update_current_model(current_model)
        sidebar.update_status(
            current_model=current_model,
            thinking_mode=thinking_mode
        )
        
        # Update header model display
        header = self.query_one(HeaderWidget)
        header.update_model_info(current_model, thinking_mode)
    
    def on_chat_input_widget_send_message(self, message: ChatInputWidgetSendMessage) -> None:
        """Handle message sent from input widget."""
        if self.connection_status == "NO MODELS":
            chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
            chat_widget.add_system_message("❌ No models available. Please check your API key and internet connection.")
            return
            
        if not self.memory_manager or not self.llm_handler:
            chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
            chat_widget.add_system_message("❌ Backend not initialized. Please check configuration.")
            return
            
        if not self.current_session_id:
            chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
            chat_widget.add_system_message("❌ No active session. Creating default session...")
            # Try to create a default session
            if self.memory_manager:
                self.current_session_id = self.memory_manager.create_session("Default Session")
            else:
                chat_widget.add_system_message("❌ Memory manager not available.")
                return
            
        # Add user message to chat immediately
        chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
        chat_widget.add_user_message(message.content)
        
        # Process message through backend
        self._process_user_input(message.content)
    
    def on_chat_input_widget_toggle_thinking(self, message: ChatInputWidgetToggleThinking) -> None:
        """Handle thinking mode toggle from input widget."""
        # Toggle thinking mode directly in config
        from config import Config, toggle_thinking_mode
        toggle_thinking_mode()
        
        # Update the button state
        input_widget = self.query_one("#chat-input", ChatInputWidget)
        input_widget.update_thinking_button()
        
        # Show confirmation message
        chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
        status = "ON" if Config.THINKING_MODE else "OFF"
        chat_widget.add_system_message(f"🧠 Thinking mode: {status}")
        
        # Update header and sidebar
        header = self.query_one(HeaderWidget)
        header.update_model_info(Config.CLAUDE_MODEL, Config.THINKING_MODE)
        
        sidebar = self.query_one("#sidebar", SidebarWidget)
        sidebar.update_status(thinking_mode=Config.THINKING_MODE)
    
    def _process_user_input(self, user_input: str) -> None:
        """Process user input through the backend."""
        # Capture the current session ID to ensure response goes to the right session
        current_session_id = self.current_session_id
        # Use a worker to handle the async processing
        self.run_worker(self._handle_message_async(user_input, current_session_id), exclusive=True)
    
    async def _handle_message_async(self, user_input: str, session_id: str) -> None:
        """Handle message processing asynchronously."""
        typing_message_id = None
        try:
            chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
            
            # Show thinking indicator for Claude response
            typing_message_id = chat_widget.add_typing_indicator("🤔 Claude is thinking...")
            
            # Make sure we're on the right session for processing
            if session_id:
                self.memory_manager.switch_session(session_id)
            
            # Add a small delay to show thinking indicator
            await asyncio.sleep(0.5)
            chat_widget.update_typing_indicator(typing_message_id, "⚡ Claude is responding...")
            
            # Process regular chat message directly
            try:
                # Add user message to memory (to the specific session)
                self.memory_manager.add_message("user", user_input)
                
                # Get response from Claude using the session's model
                current_session = self.memory_manager.get_current_session()
                session_model = current_session.metadata.model_used
                message_objects = current_session.messages
                # Convert MessageData objects to dictionaries for LLM handler
                messages = [{"role": msg.role, "content": msg.content} for msg in message_objects]
                
                response = await asyncio.to_thread(
                    self.llm_handler.generate_response,
                    messages,
                    True,  # stream
                    session_model  # use session-specific model
                )
                
                # Add assistant response to memory (to the specific session)
                self.memory_manager.add_message("assistant", response)
                
                # Only show response if we're still on the same session
                if self.current_session_id == session_id:
                    result = {"response": response}
                else:
                    # Session changed during processing - don't show response in current view
                    result = {"response": None, "session_changed": True}
            except Exception as e:
                # Handle backend processing errors gracefully
                result = {"error": f"Backend processing error: {str(e)}"}
            
            # Remove typing indicator
            chat_widget.remove_message(typing_message_id)
            typing_message_id = None
            
            # Handle the result
            if result.get("error"):
                chat_widget.add_system_message(f"❌ Error: {result['error']}")
            elif result.get("session_changed"):
                # Session was changed during processing - response saved to original session
                chat_widget.add_system_message("📂 Response saved to previous session")
            elif result.get("response"):
                # Add Claude's response
                chat_widget.add_assistant_message(result["response"])
            
            # Reset button state after processing
            self._reset_input_button()
            
        except Exception as e:
            # Remove typing indicator if it exists
            if typing_message_id is not None:
                try:
                    chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
                    chat_widget.remove_message(typing_message_id)
                except:
                    pass
            chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
            chat_widget.add_system_message(f"❌ Error: {str(e)}")
            
            # Reset button state on error too
            self._reset_input_button()
    
# Removed _handle_command_result - no longer needed
    
    def on_sidebar_widget_session_selected(self, message) -> None:
        """Handle session selection from sidebar."""
        if self.memory_manager and message.session_id != self.current_session_id:
            # Get session name for confirmation
            session = self.memory_manager.sessions.get(message.session_id)
            session_name = session.name if session else "Unknown"
            
            self.current_session_id = message.session_id
            # Make sure memory manager switches to the same session
            self.memory_manager.switch_session(message.session_id)
            self._load_current_session()
            
            # Show confirmation that we switched
            chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
            chat_widget.add_system_message(f"📂 Switched to session: {session_name}")
    
    def on_switch_session_requested(self, message: SwitchSessionRequested) -> None:
        """Handle switch session request from sidebar."""
        if self.memory_manager and message.session_id != self.current_session_id:
            # Get session name for confirmation
            session = self.memory_manager.sessions.get(message.session_id)
            session_name = session.name if session else "Unknown"
            
            self.current_session_id = message.session_id
            # Make sure memory manager switches to the same session
            self.memory_manager.switch_session(message.session_id)
            self._load_current_session()
            
            # Explicitly update model display to ensure it reflects the new session
            self._update_model_display()
            
            # Show confirmation that we switched
            chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
            chat_widget.add_system_message(f"📂 Switched to session: {session_name}")
    
    def on_session_selected(self, message: SessionSelected) -> None:
        """Handle session selection from sidebar (clicking on session item)."""
        if self.memory_manager and message.session_id != self.current_session_id:
            # Get session name for confirmation
            session = self.memory_manager.sessions.get(message.session_id)
            session_name = session.name if session else "Unknown"
            
            self.current_session_id = message.session_id
            # Make sure memory manager switches to the same session
            self.memory_manager.switch_session(message.session_id)
            self._load_current_session()
            
            # Explicitly update model display to ensure it reflects the new session
            self._update_model_display()
            
            # Show confirmation that we switched
            chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
            chat_widget.add_system_message(f"📂 Switched to session: {session_name}")
    
    def on_new_session_requested(self, message: NewSessionRequested) -> None:
        """Handle new session request from sidebar."""
        if not self.memory_manager:
            return
            
        # Create a new session with a default name
        import time
        session_name = f"Chat {time.strftime('%H:%M')}"
        new_session_id = self.memory_manager.create_session(session_name)
        
        # Switch to the new session
        self.current_session_id = new_session_id
        # Make sure memory manager switches to the new session
        self.memory_manager.switch_session(new_session_id)
        self._load_current_session()
        
        # Show confirmation
        chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
        chat_widget.add_system_message(f"✅ Created new session: {session_name}")
    
    def on_delete_session_requested(self, message: DeleteSessionRequested) -> None:
        """Handle delete session request from sidebar."""
        if not self.memory_manager or not message.session_id:
            return
            
        # Don't delete if it's the only session
        if len(self.memory_manager.sessions) <= 1:
            chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
            chat_widget.add_system_message("❌ Cannot delete the last session")
            return
        
        # Get session name before deletion
        session = self.memory_manager.sessions.get(message.session_id)
        session_name = session.name if session else "Unknown"
        
        # Delete the session
        success = self.memory_manager.delete_session(message.session_id)
        
        if success:
            # If we deleted the current session, switch to another one
            if self.current_session_id == message.session_id:
                # Switch to the first available session
                self.current_session_id = list(self.memory_manager.sessions.keys())[0]
            
            # Reload the UI
            self._load_current_session()
            
            # Show confirmation
            chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
            chat_widget.add_system_message(f"✅ Deleted session: {session_name}")
        else:
            chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
            chat_widget.add_system_message("❌ Failed to delete session")
    
    def on_model_selection_requested(self, message: ModelSelectionRequested) -> None:
        """Handle model selection request from sidebar."""
        if self.connection_status == "NO MODELS":
            chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
            chat_widget.add_system_message("❌ No models available. Please check your API key and connection.")
            return
        
        if not self.memory_manager:
            return
        
        # Get available models
        from config import get_available_models
        available_models = get_available_models()
        
        if not available_models:
            chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
            chat_widget.add_system_message("❌ No models available")
            return
        
        # Get current session model
        current_model = self.memory_manager.get_session_model()
        
        # Convert to list of tuples for the screen
        model_list = [(model_id, description) for model_id, description in available_models.items()]
        
        # Show model selection screen
        model_screen = ModelSelectionScreen(model_list, current_model)
        self.push_screen(model_screen)
    
    def on_model_selected(self, message: ModelSelected) -> None:
        """Handle model selection completion."""
        if not self.memory_manager:
            return
        
        # Update the session model
        success = self.memory_manager.set_session_model(message.model_id)
        
        if success:
            # Update sidebar display
            sidebar = self.query_one("#sidebar", SidebarWidget)
            sidebar.update_current_model(message.model_id)
            
            # Update header display
            header = self.query_one(HeaderWidget)
            thinking_mode = "claude-3-7" in message.model_id
            header.update_model_info(message.model_id, thinking_mode)
            
            # Show confirmation message
            chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
            chat_widget.add_system_message(f"✅ Model changed to: {message.model_id}")
        else:
            chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
            chat_widget.add_system_message("❌ Failed to change model")
    
    def on_model_selection_cancelled(self, message: ModelSelectionCancelled) -> None:
        """Handle model selection cancellation."""
        # No action needed, just close the screen
        pass
    
# Removed command handling - no longer needed
    
    def action_help(self) -> None:
        """Show help screen."""
        self.push_screen(HelpScreen())
    
    def action_new_session(self) -> None:
        """Create a new session via keyboard shortcut."""
        if self.memory_manager:
            # Create a new session with timestamp name
            import time
            session_name = f"Chat {time.strftime('%H:%M')}"
            session_id = self.memory_manager.create_session(session_name)
            
            # Switch to the new session
            self.current_session_id = session_id
            self.memory_manager.switch_session(session_id)
            self._load_current_session()
            
            # Show confirmation
            chat_widget = self.query_one("#chat-messages", ChatMessagesWidget)
            chat_widget.add_system_message(f"✅ Created new session: {session_name}")
    
# Removed command actions - no longer needed
    
    def action_quit_app(self) -> None:
        """Quit the application."""
        # Direct exit for immediate response to quit shortcuts
        self.exit()
    
    def _reset_input_button(self) -> None:
        """Reset the input button to normal state."""
        try:
            input_widget = self.query_one("#chat-input", ChatInputWidget)
            input_widget.set_sending_state(False)
        except Exception:
            # Input widget might not exist or be ready
            pass
    
    def _focus_input(self) -> None:
        """Focus the input widget."""
        try:
            input_widget = self.query_one("#chat-input", ChatInputWidget)
            input_widget.focus()
        except Exception:
            # Widget might not be ready yet
            pass


def main():
    """Entry point for the Textual chat client."""
    app = ClaudeChatApp()
    app.run()


if __name__ == "__main__":
    main()
