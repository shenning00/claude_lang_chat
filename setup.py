"""Setup configuration for Claude Chat Client."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="claude-chat-client",
    version="0.1.0",
    author="Claude Chat Client Contributors",
    description="A terminal-based chat client for Anthropic's Claude AI with Textual UI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/claude-chat-client",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        "textual_ui.styles": ["*.tcss"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Communications :: Chat",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    python_requires=">=3.8",
    install_requires=[
        "langchain-anthropic>=0.3.18",
        "langchain-core>=0.3.0",
        "langchain-community>=0.3.0",
        "anthropic>=0.40.0",
        "python-dotenv>=1.0.0",
        "rich>=13.0.0",
        "colorama>=0.4.6",
        "textual>=5.2.0",
        "tiktoken>=0.5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "claude-chat=main:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/yourusername/claude-chat-client/issues",
        "Source": "https://github.com/yourusername/claude-chat-client",
    },
)