# AI-Driven Test Automation Tool for Salesforce Experience Cloud

## Overview

This is a PyQt6-based desktop application that provides AI-driven test automation for Salesforce Experience Cloud sites. The application combines local AI models (via Ollama) with optional cloud integration (OpenAI), web crawling capabilities (Playwright), and automated test generation and execution. It features a user-friendly GUI that allows non-technical users to create and manage test cases while leveraging AI to automatically generate tests from crawled page content.

**Status: ✅ Successfully Running** (July 10, 2025)
- Desktop application running with virtual display support
- Database and vector store systems operational
- OpenAI integration configured (requires valid API key with quota)
- Core architecture validated and tested

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

The application follows a modular desktop architecture with these key layers:

### Frontend Layer
- **PyQt6 GUI**: Desktop application with tabs for test management, crawler configuration, and results viewing
- **Main Window**: Central hub with test case table, crawler controls, and execution monitoring
- **Dialog Components**: Specialized dialogs for test case creation, crawler settings, and result analysis

### AI Processing Layer
- **Dual LLM Support**: Local LLM (Ollama) for offline operation and Cloud LLM (OpenAI GPT-4o) for enhanced capabilities
- **Test Generator**: AI-powered component that analyzes crawled page content and generates test cases
- **Vector Store**: Semantic search using sentence-transformers and ChromaDB for UI element matching

### Web Automation Layer
- **Site Crawler**: Playwright-based crawler for navigating Salesforce Experience Cloud sites
- **DOM Parser**: Extracts structured information from web pages including interactive elements and content blocks
- **Test Runner**: Executes generated tests using pytest framework with Playwright integration

### Data Management Layer
- **SQLite Database**: Stores test cases, execution results, and metadata
- **Vector Database**: Handles semantic embeddings for AI-powered element matching
- **Encryption Manager**: Protects sensitive data like Salesforce credentials

## Key Components

### GUI Components (`gui/`)
- **MainWindow**: Primary interface with test management and execution controls
- **TestCaseDialog**: Form for creating/editing individual test cases
- **CrawlerDialog**: Configuration interface for web crawling settings
- **ResultsViewer**: Display and analysis of test execution results

### AI Components (`ai/`)
- **TestGenerator**: Central AI engine that coordinates LLM calls and test generation
- **LocalLLMClient**: Interface to Ollama for offline AI processing
- **CloudLLMClient**: Interface to OpenAI API for cloud-based AI processing

### Crawler Components (`crawler/`)
- **SiteCrawler**: Main crawling engine using Playwright for browser automation
- **DOMParser**: Extracts structured data from HTML documents

### Execution Components (`execution/`)
- **TestRunner**: Orchestrates test execution with parallel processing support
- **PytestGenerator**: Converts test case data into executable pytest code

### Storage Components (`storage/`)
- **DatabaseManager**: SQLite operations with thread-safe connection management
- **VectorStore**: Semantic search capabilities for AI-driven element matching

## Data Flow

1. **Configuration**: User configures Salesforce credentials and crawler settings through GUI dialogs
2. **Crawling**: Playwright-based crawler navigates target site, extracting page structures and UI elements
3. **AI Analysis**: Test generator feeds page content to LLM (local or cloud) for test case generation
4. **Storage**: Generated tests and page metadata stored in SQLite database with vector embeddings
5. **Execution**: pytest framework executes tests with real browser automation
6. **Reporting**: HTML reports generated with detailed results, screenshots, and performance metrics

## External Dependencies

### Core Technologies
- **PyQt6**: Desktop GUI framework
- **Playwright**: Browser automation for crawling and test execution
- **SQLite**: Local database storage
- **OpenAI API**: Cloud-based AI processing (optional)
- **Ollama**: Local LLM inference (optional)

### AI/ML Libraries
- **sentence-transformers**: Text embeddings for semantic search
- **chromadb**: Vector database for similarity matching
- **beautifulsoup4**: HTML parsing and DOM analysis

### Testing Framework
- **pytest**: Test execution framework
- **Jinja2**: Template engine for test code and report generation

### Security
- **cryptography**: Encryption for sensitive credentials
- **keyring**: Secure credential storage

## Deployment Strategy

### Local Deployment
- **Standalone Application**: Runs entirely on user's machine with local SQLite database
- **Offline Capability**: Uses Ollama for local LLM inference when internet unavailable
- **Data Privacy**: All sensitive data remains on local machine with encryption

### Hybrid Cloud Integration
- **Optional Cloud AI**: Can leverage OpenAI API for enhanced AI capabilities when available
- **Local-First Design**: Degrades gracefully to local-only operation
- **Flexible Configuration**: Environment variables control cloud vs local operation

### Installation Requirements
- Python 3.8+ with PyQt6 support
- Playwright browsers (automatically installable)
- Optional: Ollama for local LLM support
- Optional: OpenAI API key for cloud AI features

The architecture prioritizes user privacy and offline capability while providing optional cloud enhancements for improved AI performance.

## Recent Changes (July 10, 2025)

### Application Successfully Deployed
- ✅ Installed Python 3.11 and all required dependencies including PyQt6, Playwright, OpenAI
- ✅ Configured system dependencies for GUI support (Mesa, Qt6, X11 libraries)
- ✅ Set up virtual display (Xvfb) for headless GUI operation
- ✅ Application now running successfully with all core systems operational
- ✅ Database initialization working (SQLite + Vector Store)
- ✅ Configuration management validated
- ✅ Logging system active and comprehensive
- ✅ OpenAI API integration configured (requires API key with sufficient quota)
- ✅ Playwright browser automation ready (Chromium installing in background)

### Technical Implementation Notes
- Uses virtual display for GUI in server environment
- Graceful degradation when ML dependencies unavailable
- Fallback vector store when ChromaDB/sentence-transformers unavailable
- Comprehensive error handling and logging throughout