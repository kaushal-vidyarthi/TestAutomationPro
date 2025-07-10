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
        """Async implementation of Salesforce site crawling"""
        self.start_time = time.time()
        
        try:
            await self.initialize_browser()
            
            if progress_callback:
                progress_callback(0, 100, "Logging into Salesforce...")
            
            # Login to Salesforce
            login_success = await self.login_to_salesforce(sf_config)
            if not login_success:
                raise Exception("Failed to login to Salesforce")
            
            if progress_callback:
                progress_callback(10, 100, "Login successful, starting crawl...")
            
            # Get starting URL
            start_url = self.config.get('start_url') or sf_config.get('login_url')
            if not start_url:
                raise Exception("No starting URL provided")
            
            # Start crawling
            await self.crawl_site(start_url, progress_callback)
            
            # Compile results
            results = self.compile_crawl_results()
            
            if progress_callback:
                progress_callback(100, 100, f"Crawl completed. {len(self.crawled_pages)} pages found.")
            
            return results
            
        except Exception as e:
            logging.error(f"Crawling failed: {e}")
            if progress_callback:
                progress_callback(0, 100, f"Crawl failed: {str(e)}")
            raise
        finally:
            await self.close()
    
    async def login_to_salesforce(self, sf_config: Dict[str, Any]) -> bool:
        """Login to Salesforce using provided credentials"""
        try:
            page = await self.context.new_page()
            
            login_url = sf_config.get('login_url', 'https://login.salesforce.com')
            username = sf_config.get('username')
            password = sf_config.get('password')
            
            if not username or not password:
                raise Exception("Username and password are required")
            
            logging.info(f"Attempting login to {login_url}")
            
            # Navigate to login page
            await page.goto(login_url, wait_until='networkidle')
            await page.wait_for_timeout(5000)
            
            # Fill login form
            username_selector = 'input[autocomplete="username"]'
            password_selector = 'input[type="password"]'
            login_button_selector = '.comm-login-form__login-button'
            
            logging.info("Filling login form")
            logging.debug(f"Username selector: {username_selector}, Password selector: {password_selector}")
            logging.debug(f"Login button selector: {login_button_selector}")
            
            
            await page.fill(username_selector, username)
            await page.fill(password_selector, password)
            
            # Click login button
            await page.click(login_button_selector)
            
            # Wait for login to complete
            try:
                # Wait for either successful login or error
                await page.wait_for_url(lambda url: 'my.site.com' not in url, timeout=30000)
                logging.info("Login successful")
                
                # Handle any additional authentication prompts
                await self.handle_post_login_prompts(page)
                
                await page.close()
                return True
                
            except Exception as e:
                # Check for login errors
                error_elements = await page.query_selector_all('.loginError, .error, [id*="error"]')
                if error_elements:
                    error_text = await error_elements[0].text_content()
                    raise Exception(f"Login failed: {error_text}")
                else:
                    raise Exception(f"Login timeout or unknown error: {e}")
                    
        except Exception as e:
            logging.error(f"Salesforce login failed: {e}")
            return False
    
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
