const { app, BrowserWindow, ipcMain, dialog, Menu, shell } = require('electron');
const path = require('path');
const fs = require('fs-extra');
const Store = require('electron-store');
const winston = require('winston');

class AITestAutomationPro {
  constructor() {
    this.mainWindow = null;
    this.isDevMode = process.argv.includes('--dev');
    
    // Core components
    this.store = new Store();
    this.logger = this.setupLogging();
    this.components = {};
    
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
        }),
        new winston.transports.Console({
          format: winston.format.simple()
        })
      ]
    });
  }

  async initializeApp() {
    try {
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

  setupAppEvents() {
    app.whenReady().then(() => {
      this.createMainWindow();
      this.createApplicationMenu();

      app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
          this.createMainWindow();
        }
      });
    });

    app.on('window-all-closed', () => {
      if (process.platform !== 'darwin') {
        this.cleanup();
        app.quit();
      }
    });

    app.on('before-quit', async () => {
      await this.cleanup();
    });

    // Handle protocol for deep linking
    app.setAsDefaultProtocolClient('aitestpro');
  }

  createMainWindow() {
    this.mainWindow = new BrowserWindow({
      width: 1400,
      height: 1000,
      minWidth: 1200,
      minHeight: 800,
      icon: this.getAppIcon(),
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        enableRemoteModule: false,
        preload: path.join(__dirname, 'preload.js'),
        webSecurity: true
      },
      titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
      show: false
    });

    // Load the main UI
    this.mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

    if (this.isDevMode) {
      this.mainWindow.webContents.openDevTools();
    }

    this.mainWindow.once('ready-to-show', () => {
      this.mainWindow.show();
      this.mainWindow.focus();
    });

    this.mainWindow.on('closed', () => {
      this.mainWindow = null;
    });

    // Handle external links
    this.mainWindow.webContents.setWindowOpenHandler(({ url }) => {
      shell.openExternal(url);
      return { action: 'deny' };
    });
  }

  getAppIcon() {
    const iconName = process.platform === 'win32' ? 'app.ico' : 
                    process.platform === 'darwin' ? 'app.icns' : 'app.png';
    return path.join(__dirname, '..', '..', 'assets', 'icons', iconName);
  }

  createApplicationMenu() {
    const template = [
      {
        label: 'File',
        submenu: [
          {
            label: 'New Test Suite',
            accelerator: 'CmdOrCtrl+N',
            click: () => this.sendToRenderer('menu-new-test-suite')
          },
          {
            label: 'Open Test Suite',
            accelerator: 'CmdOrCtrl+O',
            click: () => this.openTestSuite()
          },
          {
            label: 'Save Test Suite',
            accelerator: 'CmdOrCtrl+S',
            click: () => this.saveTestSuite()
          },
          { type: 'separator' },
          {
            label: 'Import Tests',
            click: () => this.importTests()
          },
          {
            label: 'Export Results',
            accelerator: 'CmdOrCtrl+E',
            click: () => this.exportResults()
          },
          { type: 'separator' },
          {
            role: 'quit'
          }
        ]
      },
      {
        label: 'Tests',
        submenu: [
          {
            label: 'Crawl Website',
            accelerator: 'CmdOrCtrl+Shift+C',
            click: () => this.sendToRenderer('menu-crawl-website')
          },
          {
            label: 'Generate AI Tests',
            accelerator: 'CmdOrCtrl+G',
            click: () => this.sendToRenderer('menu-generate-tests')
          },
          {
            label: 'Run All Tests',
            accelerator: 'CmdOrCtrl+R',
            click: () => this.sendToRenderer('menu-run-all-tests')
          },
          {
            label: 'Stop Tests',
            accelerator: 'CmdOrCtrl+.',
            click: () => this.sendToRenderer('menu-stop-tests')
          }
        ]
      },
      {
        label: 'View',
        submenu: [
          {
            label: 'Dashboard',
            accelerator: 'CmdOrCtrl+1',
            click: () => this.sendToRenderer('menu-view-dashboard')
          },
          {
            label: 'Test Cases',
            accelerator: 'CmdOrCtrl+2',
            click: () => this.sendToRenderer('menu-view-tests')
          },
          {
            label: 'Results',
            accelerator: 'CmdOrCtrl+3',
            click: () => this.sendToRenderer('menu-view-results')
          },
          {
            label: 'Reports',
            accelerator: 'CmdOrCtrl+4',
            click: () => this.sendToRenderer('menu-view-reports')
          },
          { type: 'separator' },
          {
            label: 'Reload',
            accelerator: 'CmdOrCtrl+F5',
            click: () => this.mainWindow.reload()
          },
          {
            label: 'Toggle Developer Tools',
            accelerator: 'F12',
            click: () => this.mainWindow.webContents.toggleDevTools()
          }
        ]
      },
      {
        label: 'Tools',
        submenu: [
          {
            label: 'Settings',
            accelerator: 'CmdOrCtrl+,',
            click: () => this.sendToRenderer('menu-settings')
          },
          {
            label: 'Database Management',
            click: () => this.sendToRenderer('menu-database')
          },
          {
            label: 'Log Viewer',
            click: () => this.sendToRenderer('menu-logs')
          }
        ]
      },
      {
        label: 'Help',
        submenu: [
          {
            label: 'Documentation',
            click: () => shell.openExternal('https://docs.aitestautomationpro.com')
          },
          {
            label: 'Keyboard Shortcuts',
            click: () => this.sendToRenderer('menu-shortcuts')
          },
          { type: 'separator' },
          {
            label: 'About',
            click: () => this.sendToRenderer('menu-about')
          }
        ]
      }
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
  }

  setupIpcHandlers() {
    // Application lifecycle
    ipcMain.handle('app:get-version', () => app.getVersion());
    
    // Test execution placeholder
    ipcMain.handle('tests:run', async (event, config) => {
      try {
        this.logger.info('Running tests with config:', config);
        // Simulate test execution
        await new Promise(resolve => setTimeout(resolve, 2000));
        return { success: true, results: { passed: 5, failed: 1, total: 6 } };
      } catch (error) {
        this.logger.error('Test execution failed:', error);
        return { success: false, error: error.message };
      }
    });

    // Web crawling placeholder
    ipcMain.handle('crawler:start', async (event, config) => {
      try {
        this.logger.info('Starting crawler with config:', config);
        // Simulate crawling
        await new Promise(resolve => setTimeout(resolve, 3000));
        return { success: true, results: { pages: 15, elements: 342 } };
      } catch (error) {
        this.logger.error('Crawling failed:', error);
        return { success: false, error: error.message };
      }
    });

    // AI test generation placeholder
    ipcMain.handle('ai:generate-tests', async (event, config) => {
      try {
        this.logger.info('Generating AI tests with config:', config);
        // Simulate AI generation
        await new Promise(resolve => setTimeout(resolve, 4000));
        return { success: true, tests: [
          { name: 'Login Test', type: 'functional' },
          { name: 'Navigation Test', type: 'ui' },
          { name: 'Form Submission Test', type: 'functional' }
        ]};
      } catch (error) {
        this.logger.error('AI test generation failed:', error);
        return { success: false, error: error.message };
      }
    });

    // File operations
    ipcMain.handle('files:select-directory', async () => {
      const result = await dialog.showOpenDialog(this.mainWindow, {
        properties: ['openDirectory']
      });
      return result.canceled ? null : result.filePaths[0];
    });

    ipcMain.handle('files:select-file', async (event, options) => {
      const result = await dialog.showOpenDialog(this.mainWindow, {
        properties: ['openFile'],
        filters: options.filters || []
      });
      return result.canceled ? null : result.filePaths[0];
    });

    ipcMain.handle('files:save-file', async (event, options) => {
      const result = await dialog.showSaveDialog(this.mainWindow, options);
      return result.canceled ? null : result.filePath;
    });
  }

  sendToRenderer(channel, data) {
    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      this.mainWindow.webContents.send(channel, data);
    }
  }

  async openTestSuite() {
    const result = await dialog.showOpenDialog(this.mainWindow, {
      properties: ['openFile'],
      filters: [
        { name: 'Test Suite Files', extensions: ['json'] },
        { name: 'All Files', extensions: ['*'] }
      ]
    });

    if (!result.canceled && result.filePaths.length > 0) {
      try {
        const filePath = result.filePaths[0];
        const testSuite = await fs.readJSON(filePath);
        this.sendToRenderer('test-suite:loaded', testSuite);
      } catch (error) {
        this.logger.error('Failed to open test suite:', error);
        dialog.showErrorBox('Error', 'Failed to open test suite file');
      }
    }
  }

  async saveTestSuite() {
    const result = await dialog.showSaveDialog(this.mainWindow, {
      filters: [
        { name: 'Test Suite Files', extensions: ['json'] },
        { name: 'All Files', extensions: ['*'] }
      ]
    });

    if (!result.canceled) {
      this.sendToRenderer('test-suite:save', result.filePath);
    }
  }

  async importTests() {
    const result = await dialog.showOpenDialog(this.mainWindow, {
      properties: ['openFile'],
      filters: [
        { name: 'Test Files', extensions: ['json', 'csv', 'xlsx'] },
        { name: 'All Files', extensions: ['*'] }
      ]
    });

    if (!result.canceled && result.filePaths.length > 0) {
      this.sendToRenderer('tests:import', result.filePaths[0]);
    }
  }

  async exportResults() {
    const result = await dialog.showSaveDialog(this.mainWindow, {
      filters: [
        { name: 'HTML Report', extensions: ['html'] },
        { name: 'PDF Report', extensions: ['pdf'] },
        { name: 'JSON Data', extensions: ['json'] },
        { name: 'CSV Data', extensions: ['csv'] }
      ]
    });

    if (!result.canceled) {
      this.sendToRenderer('results:export', result.filePath);
    }
  }

  async cleanup() {
    try {
      this.logger.info('Cleaning up application...');
      this.logger.info('Application cleanup completed');
    } catch (error) {
      this.logger.error('Error during cleanup:', error);
    }
  }
}

// Initialize application
const aiTestApp = new AITestAutomationPro();

// Export for testing
module.exports = AITestAutomationPro;
