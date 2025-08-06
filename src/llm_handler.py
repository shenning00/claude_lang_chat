"""LLM Handler for integrating with Anthropic Claude via LangChain."""

import time
from typing import List, Dict, Any, Optional, Iterator
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.callbacks import BaseCallbackHandler
from config import Config
import logging


class StreamingCallbackHandler(BaseCallbackHandler):
    """Callback handler for streaming responses."""
    
    def __init__(self):
        self.tokens = []
        self.is_thinking = False
        self.thinking_tokens = 0
        
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Handle new token from LLM."""
        # Check if this is thinking mode content
        if token.startswith("<thinking>"):
            self.is_thinking = True
            return
        elif token.endswith("</thinking>"):
            self.is_thinking = False
            return
        
        if self.is_thinking:
            self.thinking_tokens += 1
        else:
            self.tokens.append(token)
            print(token, end="", flush=True)
    
    def get_response(self) -> str:
        """Get the complete response."""
        return "".join(self.tokens)
    
    def reset(self):
        """Reset the handler for next response."""
        self.tokens = []
        self.is_thinking = False
        self.thinking_tokens = 0


class LLMHandler:
    """Handles communication with Claude LLM via LangChain."""
    
    def __init__(self):
        self.client = None
        self.current_model = Config.CLAUDE_MODEL
        self.system_prompt = None
        self.callback_handler = StreamingCallbackHandler()
        self.logger = logging.getLogger(__name__)
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize the ChatAnthropic client."""
        try:
            config = Config.get_model_config()
            
            # Create the client with thinking mode if supported
            client_kwargs = {
                "api_key": Config.ANTHROPIC_API_KEY,
                "model": config["model"],
                "max_tokens": config["max_tokens"],
                "temperature": config["temperature"],
                "streaming": True,
                "callbacks": [self.callback_handler]
            }
            
            # Add thinking configuration if available
            if "thinking" in config:
                client_kwargs["thinking"] = config["thinking"]
            
            self.client = ChatAnthropic(**client_kwargs)
            self.logger.info(f"Initialized Claude client with model: {config['model']}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Claude client: {e}")
            raise
    
    def switch_model(self, model_name: str) -> bool:
        """Switch to a different Claude model."""
        from config import get_available_models
        available_models = get_available_models()
        if model_name not in available_models:
            return False
        
        try:
            old_model = self.current_model
            self.current_model = model_name
            Config.CLAUDE_MODEL = model_name
            self._initialize_client()
            self.logger.info(f"Switched model from {old_model} to {model_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to switch model to {model_name}: {e}")
            # Revert to old model
            self.current_model = old_model
            Config.CLAUDE_MODEL = old_model
            self._initialize_client()
            return False
    
    def set_system_prompt(self, prompt: str) -> None:
        """Set a custom system prompt."""
        self.system_prompt = prompt
        self.logger.info("System prompt updated")
    
    def clear_system_prompt(self) -> None:
        """Clear the custom system prompt."""
        self.system_prompt = None
        self.logger.info("System prompt cleared")
    
    def _prepare_messages(self, messages: List[Dict[str, str]]) -> List:
        """Convert message history to LangChain message format."""
        langchain_messages = []
        
        # Add system prompt if set
        if self.system_prompt:
            langchain_messages.append(SystemMessage(content=self.system_prompt))
        
        # Convert messages
        for msg in messages:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))
        
        return langchain_messages
    
    def generate_response(self, messages: List[Dict[str, str]], stream: bool = True, model: str = None) -> str:
        """Generate a response from Claude with optional model override."""
        if not self.client:
            raise ValueError("LLM client not initialized")
        
        # Switch model temporarily if specified
        original_model = None
        if model and model != self.current_model:
            original_model = self.current_model
            if not self.switch_model(model):
                self.logger.warning(f"Failed to switch to model {model}, using {self.current_model}")
        
        try:
            # Reset callback handler
            self.callback_handler.reset()
            
            # Prepare messages
            langchain_messages = self._prepare_messages(messages)
            
            # Log the request
            self.logger.debug(f"Generating response with {len(messages)} messages using model {self.current_model}")
            
            if stream:
                # Show thinking indicator if thinking mode is enabled
                if Config.THINKING_MODE and "claude-3-7" in self.current_model:
                    print("🤔 Claude is thinking...", end="", flush=True)
                
                print("\n⚡ Claude is responding...\n", flush=True)
                
                # Generate streaming response
                start_time = time.time()
                response = self.client.invoke(langchain_messages)
                response_time = time.time() - start_time
                
                # Get the response content
                content = self.callback_handler.get_response()
                if not content and hasattr(response, 'content'):
                    content = response.content
                
                print(f"\n\n⏱️  Response time: {response_time:.2f}s", flush=True)
                
                # Log thinking tokens if available
                if self.callback_handler.thinking_tokens > 0:
                    print(f"🧠 Thinking tokens: {self.callback_handler.thinking_tokens}")
                
                return content
            else:
                # Non-streaming response
                response = self.client.invoke(langchain_messages)
                return response.content
                
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            error_msg = self._handle_api_error(e)
            raise RuntimeError(error_msg)
        finally:
            # Restore original model if we switched
            if original_model and original_model != self.current_model:
                self.switch_model(original_model)
    
    def _handle_api_error(self, error: Exception) -> str:
        """Handle and format API errors."""
        error_str = str(error).lower()
        
        if "rate limit" in error_str:
            return "Rate limit exceeded. Please wait a moment before trying again."
        elif "invalid api key" in error_str or "authentication" in error_str:
            return "Invalid API key. Please check your Anthropic API key."
        elif "network" in error_str or "connection" in error_str:
            return "Network error. Please check your internet connection."
        elif "timeout" in error_str:
            return "Request timeout. Please try again."
        elif "tokens" in error_str and "exceed" in error_str:
            return "Message too long. Please reduce the message length or clear conversation history."
        else:
            return f"API error: {str(error)}"
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        # Rough estimation: 1 token ≈ 4 characters for English text
        return len(text) // 4
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        from config import get_available_models
        available_models = get_available_models()
        return {
            "model": self.current_model,
            "description": available_models.get(self.current_model, "Unknown"),
            "thinking_mode": Config.THINKING_MODE and "claude-3-7" in self.current_model,
            "max_tokens": Config.MAX_TOKENS,
            "temperature": Config.TEMPERATURE,
            "system_prompt": bool(self.system_prompt)
        }
    
    def test_connection(self) -> bool:
        """Test the connection to Claude API."""
        try:
            test_messages = [{"role": "user", "content": "Hello"}]
            response = self.generate_response(test_messages, stream=False)
            return bool(response)
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def get_available_models(self) -> Dict[str, str]:
        """Get available Claude models."""
        from config import get_available_models
        return get_available_models().copy()
    
    def supports_thinking_mode(self) -> bool:
        """Check if current model supports thinking mode."""
        return "claude-3-7" in self.current_model