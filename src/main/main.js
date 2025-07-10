const { app, BrowserWindow, ipcMain, dialog, Menu, shell } = require('electron');
const path = require('path');
const fs = require('fs-extra');
const Store = require('electron-store');
const winston = require('winston');
const { StealthPlaywrightEngine } = require('./engines/playwright-engine');
const { AITestGenerator } = require('./ai/test-generator');
const { DatabaseManager } = require('./storage/database-manager');
const { ReportGenerator } = require('./reporting/report-generator');
const { SalesforceConnector } = require('./connectors/salesforce-connector');
const { TestExecutor } = require('./execution/test-executor');
const { WebCrawler } = require('./crawling/web-crawler');
const { ConfigManager } = require('./config/config-manager');

class AITestAutomationPro {
  constructor() {
    this.mainWindow = null;
    this.isDevMode = process.argv.includes('--dev');
    
    // Core components
    this.store = new Store();
    this.config = new ConfigManager();
    this.logger = this.setupLogging();
    this.database = null;
    this.playwrightEngine = null;
    this.aiGenerator = null;
    this.reportGenerator = null;
    this.salesforceConnector = null;
    this.testExecutor = null;
    this.webCrawler = null;
    
    // Initialize application
    this.initializeApp();
  }

  setupLogging() {
    const logsDir = path.join(__dirname, '..', '..', 'logs');
    fs.ensureDirSync(logsDir);

    return winston.createLogger({
      level: this.isDevMode ? 'debug' : 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json()
      ),
      transports: [
        new winston.transports.File({ 
          filename: path.join(logsDir, 'app.log'),
          maxsize: 5242880, // 5MB
          maxFiles: 5
        })
      ]
    });
  }

  async initializeApp() {
    try {
      // Initialize core components
      await this.initializeComponents();
      
      // Setup application event handlers
      this.setupAppEvents();
      
      // Setup IPC handlers
      this.setupIpcHandlers();
      
      this.logger.info('AI Test Automation Pro initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize application:', error);
      app.quit();
    }
  }

  async initializeComponents() {
    // Initialize database
    this.database = new DatabaseManager();
    await this.database.initialize();
    
    // Initialize Playwright engine
    this.playwrightEngine = new StealthPlaywrightEngine(this.config);
    
    // Initialize AI components
    this.aiGenerator = new AITestGenerator(this.config, this.database);
    
    // Initialize report generator
    this.reportGenerator = new ReportGenerator(this.database);
    
    // Initialize Salesforce connector
    this.salesforceConnector = new SalesforceConnector(this.config);
    
    // Initialize test executor
    this.testExecutor = new TestExecutor(this.playwrightEngine, this.database);
    
    // Initialize web crawler
    this.webCrawler = new WebCrawler(this.playwrightEngine, this.config);
  }

  setupAppEvents() {
    app.whenReady().then(() =

class AITestAutomationPro {
  constructor() {
    this.mainWindow = null;
    this.store = new Store();
    this.testingEngine = new StealthPlaywrightEngine();

    // Initialize app
    this.initializeApp();
  }

  initializeApp() {
    // Create main application window and load content
    app.whenReady().then(() => {
      this.createMainWindow();

      app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) this.createMainWindow();
      });
    });

    // Quit when all windows are closed
    app.on('window-all-closed', () => {
      if (process.platform !== 'darwin') {
        app.quit();
      }
    });

    // Handle application errors
    process.on('uncaughtException', (error) => {
      console.error('Uncaught Exception:', error);
      app.quit();
    });
  }

  setupProgressHandlers() {
    // Listen for progress events from various components
    this.webCrawler.on('progress', (data) =
      this.mainWindow.show();
    });
  }
}

new AITestAutomationPro();

