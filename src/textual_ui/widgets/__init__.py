"""Textual widgets for the chat application."""

from .chat_widget import ChatMessagesWidget
from .input_widget import ChatInputWidget
from .sidebar_widget import SidebarWidget
from .header_widget import HeaderWidget
from .footer_widget import FooterWidget

__all__ = [
    "ChatMessagesWidget",
    "ChatInputWidget", 
    "SidebarWidget",
    "HeaderWidget",
    "FooterWidget"
]