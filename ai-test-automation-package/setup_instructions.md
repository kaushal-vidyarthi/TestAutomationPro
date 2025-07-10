# AI Test Automation Tool - Setup Instructions

## Complete Installation Guide

This guide provides step-by-step instructions to set up and run the AI Test Automation Tool on any system.

## System Requirements

- **Operating System**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 18.04+)
- **Python**: Version 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: 2GB free space for application and browser dependencies
- **Network**: Internet connection for AI features and browser installation

## Installation Steps

### Step 1: Download and Extract

1. Download the complete project package
2. Extract all files to a folder (e.g., `ai-test-automation-tool`)
3. Open terminal/command prompt in that folder

### Step 2: Python Environment Setup

**Option A: Using Virtual Environment (Recommended)**
```bash
# Create virtual environment
python -m venv test_automation_env

# Activate environment
# On Windows:
test_automation_env\Scripts\activate
# On macOS/Linux:
source test_automation_env/bin/activate
```

**Option B: System Python**
```bash
# Make sure you have Python 3.8+ installed
python --version
```

### Step 3: Install Dependencies

```bash
# Install all required packages
pip install PyQt6==6.7.1
pip install playwright==1.45.1
pip install openai==1.35.10
pip install beautifulsoup4==4.12.3
pip install aiofiles==23.2.0
pip install jinja2==3.1.4
pip install pandas==2.2.2
pip install numpy==1.26.4
pip install scipy==1.13.1
pip install pytest==8.2.2
pip install pytest-asyncio==0.23.7
pip install pytest-html==4.1.1
pip install pytest-playwright==0.5.1
pip install cryptography==42.0.8
pip install keyring==25.2.1
pip install psutil==6.0.0
pip install packaging==24.1
```

### Step 4: Install Playwright Browsers

```bash
# Install browser for automation
playwright install chromium
```

### Step 5: System Dependencies (Linux only)

If you're on Linux, install GUI dependencies:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y qt6-base-dev python3-pyqt6 xvfb

# CentOS/RHEL
sudo yum install -y qt6-qtbase-devel python3-qt6 xorg-x11-server-Xvfb
```

### Step 6: Environment Configuration (Optional)

Create a `.env` file in the project directory:
```bash
# OpenAI API Key (optional but recommended for full AI features)
OPENAI_API_KEY=your_api_key_here

# Application Settings
LOG_LEVEL=INFO
DATABASE_PATH=./data/test_automation.db
REPORTS_DIR=./reports
```

## Running the Application

### Desktop GUI Application
```bash
python main.py
```

### Web Dashboard
```bash
python web_interface.py
```
Then open: http://localhost:5000

### Testing Installation
```bash
# Run demo to verify setup
python demo_usage.py

# Run basic tests
python test_example.py
```

## First-Time Configuration

### 1. Launch Desktop Application
```bash
python main.py
```

### 2. Configure OpenAI (Optional)
- If you have an OpenAI API key, set it as environment variable
- Without API key, application runs with limited AI features

### 3. Set Up Salesforce Connection
- Open application GUI
- Navigate to Settings → Salesforce Configuration  
- Enter your credentials:
  - **Username**: Your Salesforce username
  - **Password**: Your Salesforce password
  - **Security Token**: From Salesforce (if required)
  - **Login URL**: https://login.salesforce.com (or your custom domain)

### 4. Configure Target Site
- Go to Crawler → Site Configuration
- Enter your Salesforce Experience Cloud URL
- Set crawling parameters:
  - **Max Pages**: 50 (default)
  - **Depth**: 3 levels
  - **Timeout**: 30 seconds per page

## Basic Usage Workflow

### 1. Start Web Crawling
1. Configure your Salesforce site URL
2. Click "Start Crawling" in the GUI
3. Monitor progress in the logs panel
4. Wait for crawling to complete

### 2. Generate AI Test Cases
1. Review crawled pages in the main table
2. Select pages for test generation
3. Click "Generate Tests" button
4. AI will create comprehensive test scenarios

### 3. Execute Tests
1. Review generated test cases
2. Select tests to run
3. Click "Execute Selected Tests"
4. Monitor execution progress
5. View results in HTML reports

## Troubleshooting Common Issues

### Python Installation Issues
```bash
# Check Python version
python --version

# If python3 needed instead of python
python3 --version
```

### Package Installation Failures
```bash
# Upgrade pip first
pip install --upgrade pip

# Install packages one by one if bulk install fails
pip install PyQt6
pip install playwright
# ... continue with each package
```

### GUI Not Starting (Linux)
```bash
# Install additional GUI dependencies
sudo apt install -y python3-pyqt6 python3-pyqt6.qtwidgets

# Run with virtual display if needed
xvfb-run -a python main.py
```

### Playwright Browser Issues
```bash
# Reinstall browsers
playwright install --force chromium

# Check browser installation
playwright install --help
```

### OpenAI API Issues
- Verify API key is correct
- Check account billing and usage limits
- Application works without API key (limited features)

### Permission Issues
```bash
# Make sure you have write permissions
chmod 755 .
mkdir -p data logs reports
```

## Performance Optimization

### For Large Sites
- Limit max pages to crawl (default: 50)
- Increase timeout for slow pages
- Use selective crawling patterns

### For Better AI Performance
- Provide OpenAI API key with sufficient quota
- Use specific, detailed test requirements
- Review and refine generated tests

### System Resources
- Close other applications during test execution
- Monitor memory usage for large test suites
- Use parallel execution judiciously

## Advanced Configuration

### Custom Test Templates
Edit `/templates/test_template.py` to customize:
- Test case structure
- Assertion patterns
- Reporting format

### Database Configuration
Modify `/config/settings.py` for:
- Database location
- Connection settings
- Backup policies

### Logging Configuration
Adjust logging in `/utils/logger.py`:
- Log levels
- Output formats
- File rotation

## Integration Options

### CI/CD Integration
```bash
# Example Jenkins pipeline step
python main.py --batch --config config.json

# Example GitHub Actions
- name: Run Test Automation
  run: python main.py --headless --report-format junit
```

### External Tool Integration
- Export test cases to Excel/CSV
- Import requirements from Jira
- Send reports via email/Slack

## Getting Help

### Log Files
- Application logs: `logs/app.log`
- Test execution logs: `reports/`
- Error details: Check console output

### Common Commands
```bash
# View application status
python -c "from config.settings import AppSettings; print(AppSettings().validate_required_settings())"

# Test database connection
python -c "from storage.database import DatabaseManager; db = DatabaseManager('./data/test_automation.db'); db.initialize(); print('Database OK')"

# Verify AI integration
python -c "from ai.cloud_llm import CloudLLMClient; print('AI client ready')"
```

### Support Resources
- Check `README.md` for overview
- Review `quick_start.md` for basic usage
- Run `demo_usage.py` for workflow examples
- Examine log files for error details

## Success Verification

After setup, you should be able to:
1. ✅ Launch desktop application without errors
2. ✅ Access web dashboard at http://localhost:5000
3. ✅ Connect to Salesforce with your credentials
4. ✅ Crawl at least one page successfully
5. ✅ Generate basic test cases (with or without AI)
6. ✅ Execute a simple test and view results

If all steps complete successfully, your installation is ready for production use!