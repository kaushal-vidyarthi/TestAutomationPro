const { chromium } = require('playwright');
const EventEmitter = require('events');

class StealthPlaywrightEngine extends EventEmitter {
  constructor() {
    super();
    this.browser = null;
    this.context = null;
    this.page = null;
  }

  async initialize() {
    this.browser = await chromium.launch({ headless: true });
    this.context = await this.browser.newContext();
    this.page = await this.context.newPage();
  }

  async navigate(url) {
    try {
      await this.page.goto(url, { waitUntil: 'networkidle' });
      return true;
    } catch (error) {
      console.error('Navigation failed:', error);
      return false;
    }
  }

  async close() {
    await this.page.close();
    await this.context.close();
    await this.browser.close();
  }
}

module.exports = { StealthPlaywrightEngine };
