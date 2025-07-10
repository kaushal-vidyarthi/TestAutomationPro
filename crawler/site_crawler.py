"""
Web crawler for Salesforce Experience Cloud sites using Playwright
"""

import asyncio
import logging
import time
import json
import re
from typing import Dict, Any, List, Callable, Optional
from pathlib import Path
from urllib.parse import urljoin, urlparse
import urllib.parse
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from bs4 import BeautifulSoup

from crawler.dom_parser import DOMParser

class SiteCrawler:
    """Web crawler for extracting page structures and UI elements"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.dom_parser = DOMParser()
        
        # Crawling state
        self.visited_urls = set()
        self.crawled_pages = []
        self.failed_pages = []
        self.current_depth = 0
        
        # Statistics
        self.start_time = None
        self.pages_crawled = 0
        self.errors_count = 0
        
    async def initialize_browser(self):
        """Initialize Playwright browser"""
        try:
            self.playwright = await async_playwright().start()
            
            browser_type = self.config.get('browser', 'chromium')
            browser_options = {
                'headless': self.config.get('headless', True),
                'args': [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            }
            
            if browser_type == 'chromium':
                self.browser = await self.playwright.chromium.launch(**browser_options)
            elif browser_type == 'firefox':
                self.browser = await self.playwright.firefox.launch(**browser_options)
            elif browser_type == 'webkit':
                self.browser = await self.playwright.webkit.launch(**browser_options)
            else:
                raise ValueError(f"Unsupported browser type: {browser_type}")
            
            # Create browser context
            context_options = {
                'viewport': self.config.get('viewport', {'width': 1920, 'height': 1080}),
                'user_agent': self.config.get('user_agent', ''),
                'ignore_https_errors': True,
                'java_script_enabled': self.config.get('javascript_enabled', True)
            }
            
            if not self.config.get('load_images', False):
                context_options['bypass_csp'] = True
            
            self.context = await self.browser.new_context(**context_options)
            
            # Block unnecessary resources for faster crawling
            if not self.config.get('load_images', False):
                await self.context.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2}", 
                                        lambda route: route.abort())
            
            logging.info(f"Browser initialized: {browser_type}")
            
        except Exception as e:
            logging.error(f"Failed to initialize browser: {e}")
            raise
    
    async def close(self):
        """Close browser and cleanup resources"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
                
            logging.info("Browser closed successfully")
            
        except Exception as e:
            logging.warning(f"Error during browser cleanup: {e}")
    
    def crawl_salesforce_site(self, sf_config: Dict[str, Any], 
                             progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Main entry point for crawling Salesforce site"""
        return asyncio.run(self._crawl_salesforce_site_async(sf_config, progress_callback))
    
    async def _crawl_salesforce_site_async(self, sf_config: Dict[str, Any], 
                                          progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Async implementation of Salesforce site crawling with intelligent fallback"""
        self.start_time = time.time()
        
        try:
            await self.initialize_browser()
            
            if progress_callback:
                progress_callback(0, 100, "Analyzing target site...")
            
            # Smart login detection and handling
            login_url = sf_config.get('login_url')
            base_url = self.extract_base_url(login_url)
            
            # Check if login is required
            login_required = await self.detect_login_requirement(login_url)
            
            if login_required:
                if progress_callback:
                    progress_callback(10, 100, "Login required - attempting authentication...")
                
                login_success = await self.smart_login_to_salesforce(sf_config)
                
                if not login_success:
                    logging.warning("Login failed, attempting to crawl public pages...")
                    if progress_callback:
                        progress_callback(20, 100, "Login failed, exploring accessible pages...")
                    
                    # Try to find and crawl public pages
                    public_urls = await self.discover_public_pages(base_url)
                    await self.crawl_public_pages(public_urls, progress_callback)
                else:
                    if progress_callback:
                        progress_callback(30, 100, "Login successful, starting comprehensive crawl...")
                    
                    # Full authenticated crawl
                    start_url = self.config.get('start_url') or login_url
                    await self.crawl_site(start_url, progress_callback)
            else:
                if progress_callback:
                    progress_callback(20, 100, "No login required, starting direct crawl...")
                
                # Direct crawl without login
                start_url = self.config.get('start_url') or login_url
                await self.crawl_site(start_url, progress_callback)
            
            # Compile results
            results = self.compile_crawl_results()
            
            if progress_callback:
                progress_callback(100, 100, f"Crawl completed. {len(self.crawled_pages)} pages analyzed.")
            
            return results
            
        except Exception as e:
            logging.error(f"Crawling failed: {e}")
            if progress_callback:
                progress_callback(0, 100, f"Crawl failed: {str(e)}")
            
            # Attempt fallback crawling
            try:
                if progress_callback:
                    progress_callback(10, 100, "Attempting fallback crawling...")
                
                base_url = self.extract_base_url(sf_config.get('login_url', ''))
                public_urls = await self.discover_public_pages(base_url)
                await self.crawl_public_pages(public_urls, progress_callback)
                
                return self.compile_crawl_results()
            except:
                raise e
        finally:
            await self.close()
    
    async def detect_login_requirement(self, url: str) -> bool:
        """Detect if login is required for the target site"""
        try:
            page = await self.context.new_page()
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Check for login indicators
            login_indicators = [
                'input[name="username"]', 'input[name="email"]', 'input[id*="username"]',
                'input[type="email"]', '#username', '#email', '#login', '.login-form',
                'button[type="submit"]', 'input[type="submit"]'
            ]
            
            for indicator in login_indicators:
                element = await page.query_selector(indicator)
                if element:
                    await page.close()
                    return True
            
            # Check page content for login keywords
            content = await page.content()
            login_keywords = ['sign in', 'log in', 'login', 'authentication', 'username', 'password']
            
            if any(keyword in content.lower() for keyword in login_keywords):
                await page.close()
                return True
            
            await page.close()
            return False
            
        except Exception as e:
            logging.warning(f"Could not detect login requirement: {e}")
            return True  # Assume login required if uncertain

    async def smart_login_to_salesforce(self, sf_config: Dict[str, Any]) -> bool:
        """Enhanced login handling for Salesforce Experience Cloud"""
        page = None
        try:
            page = await self.context.new_page()
            
            login_url = sf_config.get('login_url')
            username = sf_config.get('username')
            password = sf_config.get('password')
            
            if not username or not password:
                logging.error("Username and password are required")
                return False
            
            logging.info(f"Attempting enhanced login to {login_url}")
            
            # Navigate to login page with increased timeout
            await page.goto(login_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(5000)  # Wait for dynamic content
            
            # Take screenshot for debugging
            await page.screenshot(path='login_page_debug.png', full_page=True)
            
            # Try multiple selector strategies for username field
            username_selectors = [
                'input[name="username"]', 'input[name="email"]', 'input[id*="username"]',
                'input[id*="email"]', '#username', '#email', '#user', '.username',
                'input[type="email"]', 'input[placeholder*="username"]', 'input[placeholder*="email"]'
            ]
            
            username_filled = False
            for selector in username_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.clear()
                        await element.fill(username)
                        username_filled = True
                        logging.info(f"Username filled using selector: {selector}")
                        break
                except:
                    continue
            
            if not username_filled:
                logging.error("Could not find username field")
                return False
            
            # Try multiple selector strategies for password field
            password_selectors = [
                'input[name="password"]', 'input[type="password"]', '#password',
                '#pass', '.password', 'input[id*="password"]'
            ]
            
            password_filled = False
            for selector in password_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.clear()
                        await element.fill(password)
                        password_filled = True
                        logging.info(f"Password filled using selector: {selector}")
                        break
                except:
                    continue
            
            if not password_filled:
                logging.error("Could not find password field")
                return False
            
            # Wait a moment before submitting
            await page.wait_for_timeout(1000)
            
            # Try multiple login button strategies
            login_button_selectors = [
                'button[type="submit"]', 'input[type="submit"]', '#Login', '#login',
                '.login-button', '.btn-login', 'button:has-text("Log In")',
                'button:has-text("Sign In")', 'input[value*="Log"]', 'input[value*="Sign"]'
            ]
            
            login_clicked = False
            for selector in login_button_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.click()
                        login_clicked = True
                        logging.info(f"Login button clicked using selector: {selector}")
                        break
                except:
                    continue
            
            if not login_clicked:
                # Try form submission as fallback
                try:
                    await page.keyboard.press('Enter')
                    login_clicked = True
                    logging.info("Form submitted using Enter key")
                except:
                    logging.error("Could not submit login form")
                    return False
            
            # Wait for login to process with multiple success indicators
            try:
                # Wait for any of these success conditions
                await page.wait_for_function(
                    """() => {
                        return window.location.href !== arguments[0] || 
                               document.querySelector('.app') || 
                               document.querySelector('[data-aura-app]') ||
                               document.querySelector('.slds-') ||
                               !document.querySelector('input[type="password"]');
                    }""",
                    arg=login_url,
                    timeout=30000
                )
                
                # Additional wait for page to stabilize
                await page.wait_for_timeout(3000)
                
                # Check if we're still on the login page
                current_url = page.url
                if login_url in current_url and 'login' in current_url.lower():
                    # Check for error messages
                    error_elements = await page.query_selector_all(
                        '.error, .loginError, .errorMsg, [role="alert"], .alert-error'
                    )
                    
                    if error_elements:
                        error_text = await error_elements[0].text_content()
                        logging.error(f"Login failed with error: {error_text}")
                        return False
                    else:
                        logging.warning("Still on login page but no error found")
                        return False
                
                logging.info(f"Login successful - redirected to: {current_url}")
                
                # Handle post-login prompts
                await self.handle_enhanced_post_login_prompts(page)
                
                return True
                
            except Exception as e:
                logging.error(f"Login timeout or error: {e}")
                # Take screenshot for debugging
                await page.screenshot(path='login_failed_debug.png', full_page=True)
                return False
                
        except Exception as e:
            logging.error(f"Enhanced Salesforce login failed: {e}")
            return False
        finally:
            if page:
                await page.close()
    
    async def handle_post_login_prompts(self, page: Page):
        """Handle post-login prompts like MFA, verification, etc."""
        try:
            # Wait a bit for any redirects
            await page.wait_for_timeout(3000)
            
            # Check for common post-login prompts
            current_url = page.url
            
            # Skip MFA setup if prompted
            if 'verificationCode' in current_url or 'verification' in current_url.lower():
                skip_selectors = [
                    'a[href*="skip"]',
                    'button:has-text("Skip")',
                    'a:has-text("Skip")',
                    '.skipLink'
                ]
                
                for selector in skip_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            await element.click()
                            await page.wait_for_timeout(2000)
                            break
                    except:
                        continue
            
            # Handle app launcher or home page
            await page.wait_for_timeout(2000)
            
        except Exception as e:
            logging.warning(f"Error handling post-login prompts: {e}")

    async def handle_enhanced_post_login_prompts(self, page: Page):
        """Enhanced handling of post-login prompts with multiple strategies"""
        try:
            await page.wait_for_timeout(3000)
            current_url = page.url
            
            # Handle various post-login scenarios
            prompts_handled = []
            
            # MFA/Verification prompts
            if any(keyword in current_url.lower() for keyword in ['verify', 'mfa', 'verification', 'authenticator']):
                prompts_handled.append('MFA_VERIFICATION')
                
                skip_options = [
                    'button:has-text("Skip")', 'a:has-text("Skip")', '.skip-button',
                    'button:has-text("Not now")', 'a:has-text("Not now")',
                    'button:has-text("Later")', 'a:has-text("Later")',
                    '[data-action="skip"]', '.skip-link'
                ]
                
                for option in skip_options:
                    try:
                        element = await page.query_selector(option)
                        if element and await element.is_visible():
                            await element.click()
                            await page.wait_for_timeout(2000)
                            break
                    except:
                        continue
            
            # App launcher or home page redirection
            if 'lightning' in current_url.lower() or 'setup' in current_url.lower():
                prompts_handled.append('LIGHTNING_SETUP')
                
                # Try to navigate to a more accessible page
                home_selectors = [
                    'a[title*="Home"]', 'a[href*="home"]', '.home-link',
                    'button:has-text("Home")', '.nav-home'
                ]
                
                for selector in home_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element and await element.is_visible():
                            await element.click()
                            await page.wait_for_timeout(3000)
                            break
                    except:
                        continue
            
            # Terms of service or privacy notices
            terms_selectors = [
                'button:has-text("Accept")', 'button:has-text("Agree")',
                'button:has-text("Continue")', '.accept-button', '.agree-button'
            ]
            
            for selector in terms_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.click()
                        prompts_handled.append('TERMS_ACCEPTED')
                        await page.wait_for_timeout(2000)
                        break
                except:
                    continue
            
            if prompts_handled:
                logging.info(f"Post-login prompts handled: {', '.join(prompts_handled)}")
            
        except Exception as e:
            logging.warning(f"Error in enhanced post-login handling: {e}")
    
    def extract_base_url(self, url: str) -> str:
        """Extract base URL from full URL"""
        try:
            parsed = urlparse(url)
            return f"{parsed.scheme}://{parsed.netloc}"
        except:
            return url
    
    async def discover_public_pages(self, base_url: str) -> List[str]:
        """Discover publicly accessible pages"""
        public_urls = []
        
        try:
            # Common public page patterns for Salesforce Experience Cloud
            common_paths = [
                '/', '/home', '/about', '/contact', '/help', '/support',
                '/products', '/services', '/news', '/events', '/resources',
                '/documentation', '/api', '/status'
            ]
            
            page = await self.context.new_page()
            
            for path in common_paths:
                try:
                    test_url = f"{base_url.rstrip('/')}{path}"
                    response = await page.goto(test_url, wait_until='domcontentloaded', timeout=10000)
                    
                    if response and response.status < 400:
                        # Check if page requires login
                        content = await page.content()
                        if not any(keyword in content.lower() for keyword in ['sign in', 'log in', 'login', 'authentication']):
                            public_urls.append(test_url)
                            logging.info(f"Found public page: {test_url}")
                    
                except Exception as e:
                    logging.debug(f"Could not access {test_url}: {e}")
                    continue
                
                await page.wait_for_timeout(1000)  # Rate limiting
            
            await page.close()
            
        except Exception as e:
            logging.warning(f"Error discovering public pages: {e}")
        
        return public_urls[:10]  # Limit to first 10 found
    
    async def crawl_public_pages(self, urls: List[str], progress_callback: Optional[Callable] = None):
        """Crawl publicly accessible pages"""
        if not urls:
            logging.info("No public pages found to crawl")
            return
        
        logging.info(f"Crawling {len(urls)} public pages")
        
        for i, url in enumerate(urls):
            try:
                if progress_callback:
                    progress = 20 + (i / len(urls)) * 60
                    progress_callback(int(progress), 100, f"Crawling public page: {url}")
                
                page_data = await self.crawl_page(url, 0)
                if page_data:
                    page_data['access_type'] = 'public'
                    self.crawled_pages.append(page_data)
                    self.pages_crawled += 1
                
                await asyncio.sleep(2)  # Respectful crawling delay
                
            except Exception as e:
                logging.error(f"Failed to crawl public page {url}: {e}")
                self.failed_pages.append({'url': url, 'error': str(e), 'access_type': 'public'})
    
    async def crawl_site(self, start_url: str, progress_callback: Optional[Callable] = None):
        """Crawl the site starting from the given URL"""
        max_pages = self.config.get('max_pages', 50)
        max_depth = self.config.get('max_depth', 3)
        
        # Initialize crawling queue
        crawl_queue = [(start_url, 0)]  # (url, depth)
        
        while crawl_queue and len(self.crawled_pages) < max_pages:
            url, depth = crawl_queue.pop(0)
            
            if url in self.visited_urls or depth > max_depth:
                continue
            
            try:
                if progress_callback:
                    progress = 10 + (len(self.crawled_pages) / max_pages) * 85
                    progress_callback(int(progress), 100, f"Crawling: {url}")
                
                page_data = await self.crawl_page(url, depth)
                
                if page_data:
                    self.crawled_pages.append(page_data)
                    self.pages_crawled += 1
                    
                    # Extract links for further crawling
                    if depth < max_depth:
                        links = page_data.get('links', [])
                        for link in links:
                            if self.should_crawl_url(link):
                                crawl_queue.append((link, depth + 1))
                
                self.visited_urls.add(url)
                
                # Add delay between requests
                delay = self.config.get('delay', 1)
                if delay > 0:
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logging.error(f"Failed to crawl {url}: {e}")
                self.failed_pages.append({'url': url, 'error': str(e)})
                self.errors_count += 1
    
    async def crawl_page(self, url: str, depth: int) -> Optional[Dict[str, Any]]:
        """Crawl a single page and extract its structure"""
        try:
            page = await self.context.new_page()
            
            # Navigate to page
            timeout = self.config.get('timeout', 30) * 1000
            await page.goto(url, wait_until='networkidle', timeout=timeout)
            
            # Wait for dynamic content
            wait_time = self.config.get('wait_for_load', 3000)
            await page.wait_for_timeout(wait_time)
            
            # Get page content
            content = await page.content()
            title = await page.title()
            
            # Take screenshot if configured
            screenshot_path = None
            if self.config.get('take_screenshots', False):
                screenshot_dir = Path(self.config.get('output_directory', 'temp')) / 'screenshots'
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                screenshot_path = screenshot_dir / f"page_{len(self.crawled_pages)}.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
            
            # Parse DOM and extract elements
            page_data = await self.extract_page_data(page, url, title, content, depth)
            page_data['screenshot_path'] = str(screenshot_path) if screenshot_path else None
            
            await page.close()
            
            logging.info(f"Successfully crawled: {url}")
            return page_data
            
        except Exception as e:
            logging.error(f"Error crawling page {url}: {e}")
            if 'page' in locals():
                try:
                    await page.close()
                except:
                    pass
            return None
    
    async def extract_page_data(self, page: Page, url: str, title: str, 
                               content: str, depth: int) -> Dict[str, Any]:
        """Extract structured data from a page"""
        # Parse with BeautifulSoup for additional processing
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract basic page info
        page_data = {
            'url': url,
            'title': title,
            'depth': depth,
            'crawl_time': time.time(),
            'content_length': len(content)
        }
        
        # Extract UI elements using DOM parser
        elements = await self.extract_ui_elements(page)
        page_data['elements'] = elements
        
        # Extract links
        links = await self.extract_links(page)
        page_data['links'] = links
        
        # Extract forms
        forms = await self.extract_forms(page)
        page_data['forms'] = forms
        
        # Extract navigation elements
        navigation = await self.extract_navigation(page)
        page_data['navigation'] = navigation
        
        # Extract page structure
        structure = self.dom_parser.parse_page_structure(soup)
        page_data['structure'] = structure
        
        # Extract accessibility tree
        accessibility_tree = await self.extract_accessibility_tree(page)
        page_data['accessibility_tree'] = accessibility_tree
        
        # Extract performance metrics
        performance = await self.extract_performance_metrics(page)
        page_data['performance'] = performance
        
        return page_data
    
    async def extract_ui_elements(self, page: Page) -> List[Dict[str, Any]]:
        """Extract interactive UI elements from the page"""
        elements = []
        
        # Define selectors for different element types
        element_selectors = {
            'button': 'button, input[type="button"], input[type="submit"], [role="button"]',
            'input': 'input:not([type="button"]):not([type="submit"]), textarea',
            'link': 'a[href]',
            'select': 'select',
            'checkbox': 'input[type="checkbox"]',
            'radio': 'input[type="radio"]',
            'table': 'table',
            'form': 'form',
            'image': 'img',
            'heading': 'h1, h2, h3, h4, h5, h6',
            'list': 'ul, ol',
            'modal': '[role="dialog"], .modal, .popup',
            'tab': '[role="tab"], .tab',
            'menu': '[role="menu"], .menu, nav'
        }
        
        for element_type, selector in element_selectors.items():
            try:
                element_handles = await page.query_selector_all(selector)
                
                for handle in element_handles:
                    try:
                        element_data = await self.extract_element_data(handle, element_type)
                        if element_data:
                            elements.append(element_data)
                    except Exception as e:
                        logging.debug(f"Error extracting {element_type} element: {e}")
                        
            except Exception as e:
                logging.debug(f"Error finding {element_type} elements: {e}")
        
        return elements
    
    async def extract_element_data(self, element, element_type: str) -> Optional[Dict[str, Any]]:
        """Extract data from a single element"""
        try:
            # Get element properties
            tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
            
            # Get text content
            text_content = await element.text_content()
            text_content = text_content.strip() if text_content else ''
            
            # Get attributes
            attributes = await element.evaluate('''
                el => {
                    const attrs = {};
                    for (let attr of el.attributes) {
                        attrs[attr.name] = attr.value;
                    }
                    return attrs;
                }
            ''')
            
            # Get bounding box
            bounding_box = await element.bounding_box()
            
            # Get computed styles for visibility
            is_visible = await element.is_visible()
            is_enabled = await element.is_enabled() if element_type in ['button', 'input', 'select'] else True
            
            # Generate selectors
            css_selector = await self.generate_css_selector(element)
            xpath_selector = await self.generate_xpath_selector(element)
            
            element_data = {
                'type': element_type,
                'tag': tag_name,
                'text': text_content,
                'attributes': attributes,
                'visible': is_visible,
                'enabled': is_enabled,
                'bounding_box': bounding_box,
                'css_selector': css_selector,
                'xpath_selector': xpath_selector,
                'aria_label': attributes.get('aria-label', ''),
                'id': attributes.get('id', ''),
                'class': attributes.get('class', ''),
                'name': attributes.get('name', ''),
                'placeholder': attributes.get('placeholder', ''),
                'title': attributes.get('title', ''),
                'role': attributes.get('role', ''),
                'href': attributes.get('href', '') if element_type == 'link' else '',
                'src': attributes.get('src', '') if element_type == 'image' else ''
            }
            
            return element_data
            
        except Exception as e:
            logging.debug(f"Error extracting element data: {e}")
            return None
    
    async def generate_css_selector(self, element) -> str:
        """Generate a CSS selector for the element"""
        try:
            selector = await element.evaluate('''
                el => {
                    if (el.id) return '#' + el.id;
                    
                    let selector = el.tagName.toLowerCase();
                    
                    if (el.className) {
                        const classes = el.className.split(' ').filter(c => c && !c.includes(' '));
                        if (classes.length > 0) {
                            selector += '.' + classes.slice(0, 2).join('.');
                        }
                    }
                    
                    // Add attribute selectors for common attributes
                    if (el.name) selector += `[name="${el.name}"]`;
                    else if (el.getAttribute('data-id')) selector += `[data-id="${el.getAttribute('data-id')}"]`;
                    else if (el.type) selector += `[type="${el.type}"]`;
                    
                    return selector;
                }
            ''')
            return selector
        except:
            return ''
    
    async def generate_xpath_selector(self, element) -> str:
        """Generate an XPath selector for the element"""
        try:
            xpath = await element.evaluate('''
                el => {
                    if (el.id) return `//*[@id="${el.id}"]`;
                    
                    let path = '';
                    for (; el && el.nodeType === 1; el = el.parentNode) {
                        let idx = 0;
                        for (let sibling = el.previousSibling; sibling; sibling = sibling.previousSibling) {
                            if (sibling.nodeType === 1 && sibling.tagName === el.tagName) idx++;
                        }
                        
                        const tagName = el.tagName.toLowerCase();
                        const position = idx > 0 ? `[${idx + 1}]` : '';
                        path = '/' + tagName + position + path;
                    }
                    
                    return path;
                }
            ''')
            return xpath
        except:
            return ''
    
    async def extract_links(self, page: Page) -> List[str]:
        """Extract all links from the page"""
        try:
            links = await page.evaluate('''
                () => {
                    const links = [];
                    document.querySelectorAll('a[href]').forEach(link => {
                        const href = link.href;
                        if (href && !href.startsWith('javascript:') && !href.startsWith('mailto:')) {
                            links.push(href);
                        }
                    });
                    return [...new Set(links)];
                }
            ''')
            return links
        except:
            return []
    
    async def extract_forms(self, page: Page) -> List[Dict[str, Any]]:
        """Extract form information from the page"""
        if not self.config.get('extract_forms', True):
            return []
        
        try:
            forms = await page.evaluate('''
                () => {
                    const forms = [];
                    document.querySelectorAll('form').forEach((form, index) => {
                        const formData = {
                            index: index,
                            action: form.action || '',
                            method: form.method || 'get',
                            id: form.id || '',
                            class: form.className || '',
                            fields: []
                        };
                        
                        form.querySelectorAll('input, select, textarea').forEach(field => {
                            formData.fields.push({
                                type: field.type || field.tagName.toLowerCase(),
                                name: field.name || '',
                                id: field.id || '',
                                placeholder: field.placeholder || '',
                                required: field.required || false,
                                value: field.type === 'password' ? '' : field.value || ''
                            });
                        });
                        
                        forms.push(formData);
                    });
                    return forms;
                }
            ''')
            return forms
        except:
            return []
    
    async def extract_navigation(self, page: Page) -> Dict[str, Any]:
        """Extract navigation elements from the page"""
        if not self.config.get('extract_navigation', True):
            return {}
        
        try:
            navigation = await page.evaluate('''
                () => {
                    const nav = {
                        main_nav: [],
                        breadcrumbs: [],
                        sidebar: [],
                        footer: []
                    };
                    
                    // Main navigation
                    document.querySelectorAll('nav a, .nav a, .navigation a, .navbar a').forEach(link => {
                        if (link.href && link.textContent.trim()) {
                            nav.main_nav.push({
                                text: link.textContent.trim(),
                                href: link.href
                            });
                        }
                    });
                    
                    // Breadcrumbs
                    document.querySelectorAll('.breadcrumb a, .breadcrumbs a, [aria-label*="breadcrumb"] a').forEach(link => {
                        nav.breadcrumbs.push({
                            text: link.textContent.trim(),
                            href: link.href
                        });
                    });
                    
                    // Sidebar navigation
                    document.querySelectorAll('.sidebar a, .side-nav a, aside a').forEach(link => {
                        if (link.href && link.textContent.trim()) {
                            nav.sidebar.push({
                                text: link.textContent.trim(),
                                href: link.href
                            });
                        }
                    });
                    
                    return nav;
                }
            ''')
            return navigation
        except:
            return {}
    
    async def extract_accessibility_tree(self, page: Page) -> Dict[str, Any]:
        """Extract accessibility tree for AI processing"""
        try:
            # Get accessibility snapshot
            accessibility_tree = await page.accessibility.snapshot()
            
            # Simplify the tree for AI consumption
            simplified_tree = self.simplify_accessibility_tree(accessibility_tree)
            
            return simplified_tree
        except Exception as e:
            logging.debug(f"Could not extract accessibility tree: {e}")
            return {}
    
    def simplify_accessibility_tree(self, tree: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify accessibility tree for AI processing"""
        if not tree:
            return {}
        
        simplified = {
            'role': tree.get('role', ''),
            'name': tree.get('name', ''),
            'description': tree.get('description', ''),
            'value': tree.get('value', ''),
            'children': []
        }
        
        # Recursively process children
        for child in tree.get('children', []):
            simplified_child = self.simplify_accessibility_tree(child)
            if simplified_child.get('role') or simplified_child.get('name'):
                simplified['children'].append(simplified_child)
        
        return simplified
    
    async def extract_performance_metrics(self, page: Page) -> Dict[str, Any]:
        """Extract page performance metrics"""
        try:
            performance = await page.evaluate('''
                () => {
                    const perf = performance.getEntriesByType('navigation')[0];
                    if (!perf) return {};
                    
                    return {
                        load_time: perf.loadEventEnd - perf.navigationStart,
                        dom_ready: perf.domContentLoadedEventEnd - perf.navigationStart,
                        first_paint: performance.getEntriesByName('first-paint')[0]?.startTime || 0,
                        first_contentful_paint: performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0
                    };
                }
            ''')
            return performance
        except:
            return {}
    
    def should_crawl_url(self, url: str) -> bool:
        """Determine if a URL should be crawled"""
        try:
            # Parse URL
            parsed = urlparse(url)
            
            # Skip external domains
            if parsed.netloc and parsed.netloc not in url:
                return False
            
            # Check include patterns
            include_patterns = self.config.get('include_patterns', [])
            if include_patterns:
                for pattern in include_patterns:
                    if re.search(pattern, url):
                        break
                else:
                    return False
            
            # Check exclude patterns
            exclude_patterns = self.config.get('exclude_patterns', [])
            for pattern in exclude_patterns:
                if re.search(pattern, url):
                    return False
            
            # Skip common file types
            skip_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.exe']
            for ext in skip_extensions:
                if url.lower().endswith(ext):
                    return False
            
            return True
            
        except Exception as e:
            logging.debug(f"Error checking URL {url}: {e}")
            return False
    
    def compile_crawl_results(self) -> Dict[str, Any]:
        """Compile final crawl results"""
        end_time = time.time()
        duration = end_time - self.start_time if self.start_time else 0
        
        results = {
            'crawl_summary': {
                'start_time': self.start_time,
                'end_time': end_time,
                'duration': duration,
                'pages_crawled': len(self.crawled_pages),
                'pages_failed': len(self.failed_pages),
                'total_urls_visited': len(self.visited_urls),
                'errors_count': self.errors_count
            },
            'pages': self.crawled_pages,
            'failed_pages': self.failed_pages,
            'config': self.config
        }
        
        logging.info(f"Crawl completed: {len(self.crawled_pages)} pages in {duration:.2f}s")
        
        return results
