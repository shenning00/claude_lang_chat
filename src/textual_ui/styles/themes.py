"""Color themes for the chat application."""

from typing import Dict, Any

# Default dark theme (similar to the target screenshot)
DARK_THEME = {
    "name": "dark",
    "colors": {
        "primary": "#8B0000",          # Dark red (like target screenshot)
        "secondary": "#4A0000",        # Darker red
        "accent": "#FF6B6B",           # Light red accent
        "background": "#1A0000",       # Very dark red background
        "surface": "#2D0000",          # Dark red surface
        "text": "#FFFFFF",             # White text
        "text-muted": "#CCCCCC",       # Light gray muted text
        "border": "#4A0000",           # Dark red border
        "success": "#00FF00",          # Green for success
        "warning": "#FFA500",          # Orange for warnings
        "error": "#FF0000",            # Red for errors
    }
}

# Light theme alternative
LIGHT_THEME = {
    "name": "light", 
    "colors": {
        "primary": "#DC143C",          # Crimson
        "secondary": "#B22222",        # Fire brick
        "accent": "#FF69B4",           # Hot pink accent
        "background": "#FFFFFF",       # White background
        "surface": "#F5F5F5",          # Light gray surface
        "text": "#000000",             # Black text
        "text-muted": "#666666",       # Dark gray muted text
        "border": "#CCCCCC",           # Light gray border
        "success": "#008000",          # Green for success
        "warning": "#FF8C00",          # Dark orange for warnings
        "error": "#DC143C",            # Crimson for errors
    }
}

# High contrast theme
HIGH_CONTRAST_THEME = {
    "name": "high_contrast",
    "colors": {
        "primary": "#FFFFFF",          # White primary
        "secondary": "#000000",        # Black secondary
        "accent": "#FFFF00",           # Yellow accent
        "background": "#000000",       # Black background
        "surface": "#333333",          # Dark gray surface
        "text": "#FFFFFF",             # White text
        "text-muted": "#AAAAAA",       # Light gray muted text
        "border": "#FFFFFF",           # White border
        "success": "#00FF00",          # Bright green
        "warning": "#FFFF00",          # Bright yellow
        "error": "#FF0000",            # Bright red
    }
}

AVAILABLE_THEMES: Dict[str, Dict[str, Any]] = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
    "high_contrast": HIGH_CONTRAST_THEME,
}

def get_theme(theme_name: str = "dark") -> Dict[str, Any]:
    """Get a theme by name."""
    return AVAILABLE_THEMES.get(theme_name, DARK_THEME)

def get_theme_names() -> list[str]:
    """Get list of available theme names."""
    return list(AVAILABLE_THEMES.keys())