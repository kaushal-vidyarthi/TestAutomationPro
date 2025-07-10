# AI-Driven Test Automation Tool for Salesforce Experience Cloud

## Overview

This is a comprehensive desktop application that automatically generates and executes test cases for Salesforce Experience Cloud sites using AI analysis. The tool combines PyQt6 GUI, Playwright browser automation, and OpenAI integration to provide intelligent test automation.

## Features

- **AI-Powered Test Generation**: Automatically creates test cases by analyzing page structures
- **Web Crawling**: Smart navigation through Salesforce sites with element extraction
- **Desktop GUI**: User-friendly PyQt6 interface for managing tests and viewing results
- **Web Dashboard**: Browser-based monitoring and control interface
- **Automated Execution**: Parallel test execution with comprehensive HTML reporting
- **Secure Storage**: SQLite database with encrypted credential storage

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Windows, macOS, or Linux
- Internet connection for AI features (optional for basic functionality)

### Installation

1. **Clone or download this repository**
   ```bash
   cd ai-test-automation-tool
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers**
   ```bash
   playwright install chromium
   ```

4. **Set up environment variables (optional)**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

### Running the Application

#### Desktop GUI Application
```bash
python main.py
```

#### Web Dashboard
```bash
python web_interface.py
```
Then open http://localhost:5000 in your browser

#### Demo and Testing
```bash
python demo_usage.py
python test_example.py
```

## Configuration

### Salesforce Setup
1. Launch the desktop application
2. Go to Settings → Salesforce Configuration
3. Enter your credentials:
   - Username
   - Password
   - Security Token (if required)
   - Login URL

### AI Configuration
- **OpenAI**: Set OPENAI_API_KEY environment variable
- **Local LLM**: Install Ollama and configure in settings

## Usage Workflow

1. **Configure Target Site**: Set up your Salesforce Experience Cloud URL
2. **Start Crawling**: Analyze site structure and extract UI elements
3. **Generate Tests**: AI creates comprehensive test scenarios automatically
4. **Execute Tests**: Run tests with real browser automation
5. **View Reports**: Review detailed HTML reports with screenshots

## Project Structure

```
ai-test-automation-tool/
├── ai/                     # AI components (test generation, LLM clients)
├── config/                 # Configuration management
├── crawler/                # Web crawling and DOM parsing
├── execution/              # Test execution and pytest integration
├── gui/                    # PyQt6 desktop interface
├── reporting/              # HTML report generation
├── storage/                # Database and vector store
├── utils/                  # Utilities and helpers
├── main.py                 # Desktop application entry point
├── web_interface.py        # Web dashboard server
├── demo_usage.py           # Demonstration script
└── requirements.txt        # Python dependencies
```

## Advanced Features

### Test Types Generated
- **Functional Tests**: Login, navigation, form submission
- **UI Tests**: Element visibility, layout validation
- **Accessibility Tests**: ARIA compliance, keyboard navigation
- **Performance Tests**: Page load times, resource usage
- **Negative Tests**: Error handling, edge cases

### Reporting
- HTML reports with screenshots
- Test execution metrics
- Performance benchmarks
- Failure analysis with visual debugging

### Integration Options
- CI/CD pipeline integration
- Custom test templates
- API endpoints for external tools
- Batch processing capabilities

## Troubleshooting

### Common Issues

**Application won't start**
- Ensure Python 3.8+ is installed
- Install all requirements: `pip install -r requirements.txt`
- On Linux: Install system dependencies for GUI

**OpenAI API errors**
- Check API key is set correctly
- Verify account has sufficient quota
- Application works with limited features without API key

**Playwright browser issues**
- Run: `playwright install chromium`
- Check internet connection for browser downloads
- Verify system permissions for browser installation

**Database errors**
- Check write permissions in application directory
- Ensure SQLite is available on system
- Delete existing database file to reset if corrupted

### Performance Optimization
- Limit concurrent crawling operations
- Adjust timeout settings for slow sites
- Use selective crawling for large applications
- Monitor system resource usage

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Code Style
```bash
black .
flake8 .
```

### Building Executable
```bash
pip install pyinstaller
pyinstaller --onefile main.py
```

## Support

- **Documentation**: See `quick_start.md` for detailed usage
- **Demo**: Run `demo_usage.py` for workflow demonstration
- **Configuration**: Check `config/settings.py` for all options
- **Logs**: Application logs saved to `logs/` directory

## License

This project is provided as-is for educational and development purposes.

## Version History

- **v1.0.0** (July 10, 2025): Initial release with full GUI and AI integration
  - Desktop application with PyQt6
  - Web dashboard interface
  - OpenAI and local LLM support
  - Comprehensive test generation and execution
  - HTML reporting with screenshots