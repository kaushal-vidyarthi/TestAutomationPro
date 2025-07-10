const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Application APIs
  getVersion: () => ipcRenderer.invoke('app:get-version'),
  
  // Test execution APIs
  runTests: (config) => ipcRenderer.invoke('tests:run', config),
  stopTests: () => ipcRenderer.invoke('tests:stop'),
  
  // Web crawling APIs
  startCrawler: (config) => ipcRenderer.invoke('crawler:start', config),
  stopCrawler: () => ipcRenderer.invoke('crawler:stop'),
  
  // AI test generation APIs
  generateAITests: (config) => ipcRenderer.invoke('ai:generate-tests', config),
  
  // File operations
  selectDirectory: () => ipcRenderer.invoke('files:select-directory'),
  selectFile: (options) => ipcRenderer.invoke('files:select-file', options),
  saveFile: (options) => ipcRenderer.invoke('files:save-file', options),
  
  // Event listeners for menu actions and progress updates
  onMenuAction: (callback) => {
    ipcRenderer.on('menu-new-test-suite', callback);
    ipcRenderer.on('menu-crawl-website', callback);
    ipcRenderer.on('menu-generate-tests', callback);
    ipcRenderer.on('menu-run-all-tests', callback);
    ipcRenderer.on('menu-stop-tests', callback);
    ipcRenderer.on('menu-view-dashboard', callback);
    ipcRenderer.on('menu-view-tests', callback);
    ipcRenderer.on('menu-view-results', callback);
    ipcRenderer.on('menu-view-reports', callback);
    ipcRenderer.on('menu-settings', callback);
    ipcRenderer.on('menu-database', callback);
    ipcRenderer.on('menu-logs', callback);
    ipcRenderer.on('menu-shortcuts', callback);
    ipcRenderer.on('menu-about', callback);
  },
  
  // Progress event listeners
  onCrawlerProgress: (callback) => ipcRenderer.on('crawler:progress', callback),
  onTestProgress: (callback) => ipcRenderer.on('tests:progress', callback),
  onAIProgress: (callback) => ipcRenderer.on('ai:progress', callback),
  
  // Test suite operations
  onTestSuiteLoaded: (callback) => ipcRenderer.on('test-suite:loaded', callback),
  onTestSuiteSave: (callback) => ipcRenderer.on('test-suite:save', callback),
  onTestsImport: (callback) => ipcRenderer.on('tests:import', callback),
  onResultsExport: (callback) => ipcRenderer.on('results:export', callback),
  
  // Remove listeners
  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel),
  
  // Utility functions
  platform: process.platform,
  nodeVersion: process.versions.node,
  electronVersion: process.versions.electron
});
