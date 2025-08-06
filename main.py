#!/usr/bin/env python3
"""
Simple launcher for the Textual UI that handles Python path setup.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))


def main():
    """Launch the Textual chat client."""
    try:
        # Import and run the app
        from textual_ui.app import ClaudeChatApp

        print("🚀 Starting Claude Chat Client (Textual UI)...")
        print("💡 Keyboard shortcuts:")
        print("   • Enter: Send message")
        print("   • Shift+Enter: New line")
        print("   • Ctrl+Q: Quit")
        print("   • Ctrl+H/F1: Help")
        print("   • Ctrl+N: New session")
        print("   • Ctrl+S: Sessions list")
        print("   • ESC/Ctrl+L: Clear input")
        print("   • /help: Show commands")
        print()

        app = ClaudeChatApp()
        app.run()

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error starting application: {e}")

        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
