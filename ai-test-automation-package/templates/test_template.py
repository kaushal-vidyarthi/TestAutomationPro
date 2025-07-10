"""
Templates for generating test code and scripts
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import re

class TestTemplateGenerator:
    """Generates test code from templates"""
    
    def __init__(self):
        self.templates = {
            'pytest_test': self._get_pytest_template(),
            'playwright_test': self._get_playwright_template(),
            'unittest_test': self._get_unittest_template(),
            'selenium_test': self._get_selenium_template(),
            'api_test': self._get_api_test_template(),
            'page_object': self._get_page_object_template(),
            'test_data': self._get_test_data_template(),
            'conftest': self._get_conftest_template()
        }
    
    def generate_test_code(self, template_name: str, test_case: Dict[str, Any], **kwargs) -> str:
        """Generate test code from template"""
        if template_name not in self.templates:
            raise ValueError(f"Unknown template: {template_name}")
        
        template = self.templates[template_name]
        
        # Prepare template variables
        variables = self._prepare_template_variables(test_case, **kwargs)
        
        # Replace placeholders in template
        generated_code = self._replace_template_variables(template, variables)
        
        return generated_code
    
    def _prepare_template_variables(self, test_case: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Prepare variables for template substitution"""
        
        # Sanitize test name for use as function/class name
        test_name = re.sub(r'[^\w]', '_', test_case.get('title', 'test_case')).lower()
        test_name = re.sub(r'_+', '_', test_name).strip('_')
        
        # Convert steps to code
        steps_code = self._generate_steps_code(test_case.get('steps', []))
        assertions_code = self._generate_assertions_code(test_case.get('assertions', []))
        
        variables = {
            'test_name': test_name,
            'test_title': test_case.get('title', 'Untitled Test'),
            'test_description': test_case.get('description', ''),
            'test_id': test_case.get('id', ''),
            'priority': test_case.get('priority', 'Medium'),
            'test_type': test_case.get('type', 'Functional'),
            'environment': test_case.get('environment', 'Testing'),
            'browser': test_case.get('browser', 'chromium'),
            'preconditions': test_case.get('preconditions', ''),
            'steps_code': steps_code,
            'assertions_code': assertions_code,
            'expected_result': test_case.get('expected_result', ''),
            'test_data': test_case.get('test_data', {}),
            'tags': test_case.get('tags', ''),
            'author': test_case.get('author', 'AI Generated'),
            'created_date': datetime.now().strftime('%Y-%m-%d'),
            'class_name': f"Test{test_name.title().replace('_', '')}",
            'timeout': kwargs.get('timeout', 30),
            'base_url': kwargs.get('base_url', ''),
            'screenshot_on_failure': kwargs.get('screenshot_on_failure', True)
        }
        
        # Add custom variables
        variables.update(kwargs)
        
        return variables
    
    def _replace_template_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """Replace template variables with actual values"""
        result = template
        
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        
        return result
    
    def _generate_steps_code(self, steps: List[str]) -> str:
        """Generate Python code for test steps"""
        if not steps:
            return "        pass  # No steps defined"
        
        code_lines = []
        
        for i, step in enumerate(steps):
            step_comment = f"        # Step {i + 1}: {step}"
            step_code = self._convert_step_to_code(step)
            
            code_lines.append(step_comment)
            code_lines.append(f"        {step_code}")
            code_lines.append("")  # Empty line for readability
        
        return "\n".join(code_lines)
    
    def _convert_step_to_code(self, step: str) -> str:
        """Convert a test step description to Python code"""
        step_lower = step.lower().strip()
        
        # Navigation steps
        if any(keyword in step_lower for keyword in ['navigate to', 'go to', 'visit']):
            url = self._extract_url(step)
            if url:
                return f'await page.goto("{url}")'
            else:
                return f'# TODO: Navigate to URL from step: {step}'
        
        # Click actions
        elif step_lower.startswith('click'):
            target = self._extract_click_target(step)
            if target:
                if target.startswith('#') or target.startswith('.') or '[' in target:
                    return f'await page.click("{target}")'
                else:
                    return f'await page.click(\'text="{target}"\')'
            else:
                return f'# TODO: Click target from step: {step}'
        
        # Input actions
        elif any(keyword in step_lower for keyword in ['fill', 'enter', 'type', 'input']):
            selector, value = self._extract_input_info(step)
            if selector and value:
                return f'await page.fill("{selector}", "{value}")'
            else:
                return f'# TODO: Fill input from step: {step}'
        
        # Select actions
        elif step_lower.startswith('select'):
            selector, option = self._extract_select_info(step)
            if selector and option:
                return f'await page.select_option("{selector}", "{option}")'
            else:
                return f'# TODO: Select option from step: {step}'
        
        # Wait actions
        elif step_lower.startswith('wait'):
            wait_time = self._extract_wait_time(step)
            if wait_time:
                return f'await page.wait_for_timeout({wait_time * 1000})'
            else:
                return f'await page.wait_for_timeout(2000)  # Default wait'
        
        # Verification steps (handled in assertions)
        elif any(keyword in step_lower for keyword in ['verify', 'check', 'assert', 'confirm']):
            return f'# Verification: {step} (handled in assertions)'
        
        # Generic step
        else:
            return f'# TODO: Implement step: {step}'
    
    def _generate_assertions_code(self, assertions: List[str]) -> str:
        """Generate Python code for assertions"""
        if not assertions:
            return "        # No assertions defined"
        
        code_lines = []
        
        for assertion in assertions:
            assertion_code = self._convert_assertion_to_code(assertion)
            code_lines.append(f"        {assertion_code}")
        
        return "\n".join(code_lines)
    
    def _convert_assertion_to_code(self, assertion: str) -> str:
        """Convert assertion description to Python code"""
        assertion_lower = assertion.lower().strip()
        
        # Element existence
        if 'element exists' in assertion_lower:
            selector = self._extract_selector(assertion)
            if selector:
                return f'assert await page.query_selector("{selector}") is not None'
            else:
                return f'# TODO: Assert element exists: {assertion}'
        
        # Element visibility
        elif 'element visible' in assertion_lower or 'element is visible' in assertion_lower:
            selector = self._extract_selector(assertion)
            if selector:
                return f'assert await page.is_visible("{selector}")'
            else:
                return f'# TODO: Assert element visible: {assertion}'
        
        # Text content
        elif 'text equals' in assertion_lower or 'text contains' in assertion_lower:
            selector, expected_text = self._extract_text_assertion(assertion)
            if selector and expected_text:
                if 'equals' in assertion_lower:
                    return f'assert await page.text_content("{selector}") == "{expected_text}"'
                else:
                    return f'assert "{expected_text}" in await page.text_content("{selector}")'
            else:
                return f'# TODO: Assert text content: {assertion}'
        
        # Page title
        elif 'page title' in assertion_lower:
            expected_title = self._extract_quoted_text(assertion)
            if expected_title:
                if 'equals' in assertion_lower:
                    return f'assert await page.title() == "{expected_title}"'
                else:
                    return f'assert "{expected_title}" in await page.title()'
            else:
                return f'# TODO: Assert page title: {assertion}'
        
        # URL
        elif 'url contains' in assertion_lower or 'url equals' in assertion_lower:
            expected_url = self._extract_quoted_text(assertion)
            if expected_url:
                if 'equals' in assertion_lower:
                    return f'assert page.url == "{expected_url}"'
                else:
                    return f'assert "{expected_url}" in page.url'
            else:
                return f'# TODO: Assert URL: {assertion}'
        
        # Generic assertion
        else:
            return f'# TODO: Implement assertion: {assertion}'
    
    def _extract_url(self, text: str) -> Optional[str]:
        """Extract URL from text"""
        import re
        
        # Look for HTTP/HTTPS URLs
        url_pattern = r'https?://[^\s]+'
        match = re.search(url_pattern, text)
        if match:
            return match.group()
        
        # Look for quoted text that might be a URL
        quoted = self._extract_quoted_text(text)
        if quoted and ('http' in quoted or quoted.startswith('/')):
            return quoted
        
        return None
    
    def _extract_click_target(self, text: str) -> Optional[str]:
        """Extract click target from text"""
        # Try selector first
        selector = self._extract_selector(text)
        if selector:
            return selector
        
        # Try quoted text
        return self._extract_quoted_text(text)
    
    def _extract_input_info(self, text: str) -> tuple:
        """Extract input selector and value from text"""
        import re
        
        patterns = [
            r'fill\s+["\']([^"\']+)["\']\s+with\s+["\']([^"\']+)["\']',
            r'enter\s+["\']([^"\']+)["\']\s+in(?:to)?\s+["\']([^"\']+)["\']',
            r'type\s+["\']([^"\']+)["\']\s+in(?:to)?\s+["\']([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if 'fill' in pattern:
                    return match.group(1), match.group(2)  # selector, value
                else:
                    return match.group(2), match.group(1)  # selector, value
        
        return None, None
    
    def _extract_select_info(self, text: str) -> tuple:
        """Extract select selector and option from text"""
        import re
        
        pattern = r'select\s+["\']([^"\']+)["\']\s+from\s+["\']([^"\']+)["\']'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            return match.group(2), match.group(1)  # selector, option
        
        return None, None
    
    def _extract_wait_time(self, text: str) -> Optional[float]:
        """Extract wait time in seconds from text"""
        import re
        
        pattern = r'(\d+(?:\.\d+)?)\s*(second|sec|s|millisecond|ms|minute|min|m)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = float(match.group(1))
            unit = match.group(2).lower()
            
            if unit in ['second', 'sec', 's']:
                return value
            elif unit in ['millisecond', 'ms']:
                return value / 1000
            elif unit in ['minute', 'min', 'm']:
                return value * 60
        
        return None
    
    def _extract_selector(self, text: str) -> Optional[str]:
        """Extract CSS selector from text"""
        import re
        
        # Look for quoted text that looks like a selector
        quoted_texts = re.findall(r'["\']([^"\']+)["\']', text)
        
        for quoted in quoted_texts:
            # Check if it looks like a CSS selector
            if any(char in quoted for char in ['#', '.', '[']) or \
               quoted.lower().startswith(('input', 'button', 'div', 'span', 'a', 'form')):
                return quoted
        
        return None
    
    def _extract_quoted_text(self, text: str) -> Optional[str]:
        """Extract text from quotes"""
        import re
        
        patterns = [r'"([^"]+)"', r"'([^']+)'"]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_text_assertion(self, text: str) -> tuple:
        """Extract selector and expected text from assertion"""
        import re
        
        patterns = [
            r'["\']([^"\']+)["\']\s+.*(?:equals|contains)\s+["\']([^"\']+)["\']',
            r'text\s+of\s+["\']([^"\']+)["\']\s+.*\s+["\']([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1), match.group(2)
        
        return None, None
    
    def _get_pytest_template(self) -> str:
        """Get pytest test template"""
        return '''"""
Test: {{test_title}}
Description: {{test_description}}
Generated: {{created_date}}
Author: {{author}}
"""

import pytest
import asyncio
from playwright.async_api import Page, Browser


@pytest.mark.asyncio
@pytest.mark.{{test_type.lower()}}
async def test_{{test_name}}(page: Page):
    """
    {{test_description}}
    
    Test ID: {{test_id}}
    Priority: {{priority}}
    Type: {{test_type}}
    Environment: {{environment}}
    Expected Result: {{expected_result}}
    """
    
    # Test metadata
    test_data = {{test_data}}
    
    try:
        # Preconditions
        # {{preconditions}}
        
        # Test steps
{{steps_code}}
        
        # Assertions
{{assertions_code}}
        
        # Test completed successfully
        print(f"Test {{test_name}} completed successfully")
        
    except Exception as e:
        # Take screenshot on failure
        await page.screenshot(path=f"screenshots/{{test_name}}_failure.png", full_page=True)
        raise e
'''
    
    def _get_playwright_template(self) -> str:
        """Get Playwright test template"""
        return '''"""
Playwright Test: {{test_title}}
"""

import asyncio
from playwright.async_api import async_playwright, Page, Browser


class {{class_name}}:
    """Test class for {{test_title}}"""
    
    def __init__(self):
        self.browser = None
        self.page = None
        self.context = None
    
    async def setup(self):
        """Setup test environment"""
        playwright = await async_playwright().start()
        self.browser = await playwright.{{browser}}.launch(headless=False)
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = await self.context.new_page()
        
        # Setup page logging
        self.page.on("console", lambda msg: print(f"Console: {msg.text}"))
        self.page.on("pageerror", lambda error: print(f"Page error: {error}"))
    
    async def teardown(self):
        """Cleanup test environment"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
    
    async def test_{{test_name}}(self):
        """
        {{test_description}}
        
        Priority: {{priority}}
        Expected: {{expected_result}}
        """
        
        try:
            # Test steps
{{steps_code}}
            
            # Assertions
{{assertions_code}}
            
            print("Test passed successfully")
            
        except Exception as e:
            # Take screenshot on failure
            await self.page.screenshot(path="failure_{{test_name}}.png")
            raise e


async def main():
    """Run the test"""
    test = {{class_name}}()
    
    try:
        await test.setup()
        await test.test_{{test_name}}()
    finally:
        await test.teardown()


if __name__ == "__main__":
    asyncio.run(main())
'''
    
    def _get_unittest_template(self) -> str:
        """Get unittest template"""
        return '''"""
Unit Test: {{test_title}}
"""

import unittest
import asyncio
from playwright.async_api import async_playwright


class {{class_name}}(unittest.TestCase):
    """Test class for {{test_title}}"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test class"""
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)
    
    async def async_setUp(self):
        """Async setup for each test"""
        playwright = await async_playwright().start()
        self.browser = await playwright.{{browser}}.launch()
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
    
    async def async_tearDown(self):
        """Async cleanup for each test"""
        await self.page.close()
        await self.context.close()
        await self.browser.close()
    
    def setUp(self):
        """Setup for each test"""
        self.loop.run_until_complete(self.async_setUp())
    
    def tearDown(self):
        """Cleanup for each test"""
        self.loop.run_until_complete(self.async_tearDown())
    
    def test_{{test_name}}(self):
        """
        {{test_description}}
        
        Test ID: {{test_id}}
        Expected: {{expected_result}}
        """
        
        async def async_test():
            # Test steps
{{steps_code}}
            
            # Assertions
{{assertions_code}}
        
        self.loop.run_until_complete(async_test())


if __name__ == "__main__":
    unittest.main()
'''
    
    def _get_selenium_template(self) -> str:
        """Get Selenium test template"""
        return '''"""
Selenium Test: {{test_title}}
"""

import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class {{class_name}}(unittest.TestCase):
    """Selenium test for {{test_title}}"""
    
    def setUp(self):
        """Setup test environment"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait({{timeout}})
        self.wait = WebDriverWait(self.driver, {{timeout}})
    
    def tearDown(self):
        """Cleanup test environment"""
        if self.driver:
            self.driver.quit()
    
    def test_{{test_name}}(self):
        """
        {{test_description}}
        
        Priority: {{priority}}
        Expected: {{expected_result}}
        """
        
        try:
            # Test steps (converted to Selenium)
            # {{steps_code}}
            
            # Assertions (converted to Selenium)
            # {{assertions_code}}
            
            print("Test completed successfully")
            
        except Exception as e:
            # Take screenshot on failure
            self.driver.save_screenshot("failure_{{test_name}}.png")
            raise e


if __name__ == "__main__":
    unittest.main()
'''
    
    def _get_api_test_template(self) -> str:
        """Get API test template"""
        return '''"""
API Test: {{test_title}}
"""

import requests
import json
import unittest
from typing import Dict, Any


class {{class_name}}(unittest.TestCase):
    """API test for {{test_title}}"""
    
    def setUp(self):
        """Setup test environment"""
        self.base_url = "{{base_url}}"
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "TestAutomation/1.0"
        })
    
    def tearDown(self):
        """Cleanup test environment"""
        self.session.close()
    
    def test_{{test_name}}(self):
        """
        {{test_description}}
        
        API Test
        Expected: {{expected_result}}
        """
        
        # Test data
        test_data = {{test_data}}
        
        # Test implementation
        # TODO: Implement API test steps
        
        self.assertTrue(True, "API test completed")


if __name__ == "__main__":
    unittest.main()
'''
    
    def _get_page_object_template(self) -> str:
        """Get Page Object Model template"""
        return '''"""
Page Object: {{test_title}}
"""

from playwright.async_api import Page


class {{class_name}}Page:
    """Page Object for {{test_title}}"""
    
    def __init__(self, page: Page):
        self.page = page
        
        # Page elements (selectors)
        self.selectors = {
            # TODO: Define page element selectors
        }
    
    async def navigate(self, url: str = ""):
        """Navigate to the page"""
        await self.page.goto(url)
        await self.page.wait_for_load_state("networkidle")
    
    async def is_loaded(self) -> bool:
        """Check if page is loaded"""
        # TODO: Implement page load verification
        return True
    
    # TODO: Add page-specific methods
    
    async def take_screenshot(self, name: str = "screenshot"):
        """Take page screenshot"""
        await self.page.screenshot(path=f"{name}.png", full_page=True)
'''
    
    def _get_test_data_template(self) -> str:
        """Get test data template"""
        return '''"""
Test Data for: {{test_title}}
"""

from typing import Dict, Any, List


class {{class_name}}TestData:
    """Test data for {{test_title}}"""
    
    # Valid test data
    VALID_DATA = {
        # TODO: Add valid test data
    }
    
    # Invalid test data
    INVALID_DATA = {
        # TODO: Add invalid test data
    }
    
    # Edge case data
    EDGE_CASE_DATA = {
        # TODO: Add edge case test data
    }
    
    @staticmethod
    def get_test_data(data_type: str = "valid") -> Dict[str, Any]:
        """Get test data by type"""
        data_map = {
            "valid": {{class_name}}TestData.VALID_DATA,
            "invalid": {{class_name}}TestData.INVALID_DATA,
            "edge_case": {{class_name}}TestData.EDGE_CASE_DATA
        }
        
        return data_map.get(data_type, {{class_name}}TestData.VALID_DATA)
    
    @staticmethod
    def get_all_data_sets() -> List[Dict[str, Any]]:
        """Get all test data sets"""
        return [
            {{class_name}}TestData.VALID_DATA,
            {{class_name}}TestData.INVALID_DATA,
            {{class_name}}TestData.EDGE_CASE_DATA
        ]
'''
    
    def _get_conftest_template(self) -> str:
        """Get conftest.py template"""
        return '''"""
Pytest configuration and fixtures
Generated: {{created_date}}
"""

import pytest
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def browser():
    """Create browser instance"""
    playwright = await async_playwright().start()
    browser = await playwright.{{browser}}.launch(
        headless={{screenshot_on_failure}},
        slow_mo=100
    )
    yield browser
    await browser.close()
    await playwright.stop()


@pytest.fixture
async def context(browser):
    """Create browser context"""
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080}
    )
    yield context
    await context.close()


@pytest.fixture
async def page(context):
    """Create page instance"""
    page = await context.new_page()
    
    # Setup page monitoring
    page.on("console", lambda msg: print(f"Console [{msg.type}]: {msg.text}"))
    page.on("pageerror", lambda error: print(f"Page error: {error}"))
    
    yield page
    await page.close()


@pytest.fixture(autouse=True)
async def screenshot_on_failure(request, page):
    """Take screenshot on test failure"""
    yield
    
    if request.node.rep_outcome.outcome == "failed":
        screenshots_dir = Path("screenshots")
        screenshots_dir.mkdir(exist_ok=True)
        
        screenshot_path = screenshots_dir / f"{request.node.name}_failure.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"Screenshot saved: {screenshot_path}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Make test outcome available to fixtures"""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


# Test configuration
pytest_plugins = [
    "pytest_asyncio",
    "pytest_html"
]
'''

# Convenience functions for common template usage
def generate_pytest_test(test_case: Dict[str, Any], **kwargs) -> str:
    """Generate pytest test code"""
    generator = TestTemplateGenerator()
    return generator.generate_test_code('pytest_test', test_case, **kwargs)

def generate_playwright_test(test_case: Dict[str, Any], **kwargs) -> str:
    """Generate Playwright test code"""
    generator = TestTemplateGenerator()
    return generator.generate_test_code('playwright_test', test_case, **kwargs)

def generate_page_object(test_case: Dict[str, Any], **kwargs) -> str:
    """Generate Page Object Model code"""
    generator = TestTemplateGenerator()
    return generator.generate_test_code('page_object', test_case, **kwargs)

def generate_test_data_class(test_case: Dict[str, Any], **kwargs) -> str:
    """Generate test data class"""
    generator = TestTemplateGenerator()
    return generator.generate_test_code('test_data', test_case, **kwargs)
