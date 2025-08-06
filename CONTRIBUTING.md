# Contributing to Claude Chat Client

Thank you for your interest in contributing to Claude Chat Client! We welcome contributions from the community.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/yourusername/claude-chat-client.git
   cd claude-chat-client
   ```
3. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
4. Create a branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Process

### Code Style

- We use **Black** for code formatting (line length: 88)
- We use **Flake8** for linting
- We use **MyPy** for type checking
- Follow PEP 8 guidelines

Run code quality checks:
```bash
black src/ tests/
flake8 src/ tests/
mypy src/
```

### Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Aim for good test coverage

Run tests:
```bash
pytest tests/
pytest tests/ --cov=src  # With coverage
```

### Commit Messages

Follow conventional commit format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Test additions or fixes
- `chore:` Maintenance tasks

Example:
```
feat: add export to PDF functionality
fix: resolve session switching bug
docs: update installation instructions
```

## Pull Request Process

1. Update the README.md with details of changes if needed
2. Update tests as appropriate
3. Ensure all tests pass
4. Update documentation if you're changing functionality
5. The PR will be reviewed by maintainers

### PR Checklist

- [ ] Tests pass locally
- [ ] Code follows project style guidelines
- [ ] Commit messages are clear and descriptive
- [ ] Documentation is updated if needed
- [ ] No sensitive data (API keys, passwords) included

## Types of Contributions

### Bug Reports

- Use GitHub Issues
- Describe the bug clearly
- Include steps to reproduce
- Include system information (OS, Python version)
- Include error messages/tracebacks

### Feature Requests

- Use GitHub Issues with "enhancement" label
- Describe the feature and use case
- Explain why it would be useful

### Code Contributions

We especially welcome:
- Bug fixes
- Performance improvements
- New export formats
- UI/UX improvements
- Documentation improvements
- Test coverage improvements

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Accept constructive criticism gracefully
- Focus on what's best for the community

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information

## Questions?

Feel free to open an issue for any questions about contributing.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.