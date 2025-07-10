"""
Pytest test file generator for converting test cases to executable pytest code
"""

import logging
import json
import tempfile
import subprocess
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import uuid

class PytestGenerator:
    """Generates and executes pytest test files from test case data"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.temp_dir = Path(config.get('temp_dir', 'temp'))
        self.pytest_dir = self.temp_dir / 'pytest_tests'
        self.pytest_dir.mkdir(parents=True, exist_ok=True)
        
        # Pytest configuration
        self.pytest_config = {
            'timeout': config.get('test_timeout', 60),
            'browser': config.get('browser', 'chromium'),
            'headless': config.get('headless', True),
            'base_url': config.get('base_url', ''),
            'screenshot_on_failure': config.get('screenshot_on_failure', True)
        }
    
    def generate_test_files(self, test_cases: List[Dict[str, Any]]) -> List[Path]:
        """Generate pytest test files from test cases"""
        test_files = []
        
        try:
            # Generate conftest.py for shared fixtures
            conftest_path = self._generate_conftest()
            test_files.append(conftest_path)
            
            # Generate test files (group by type or create individual files)
            grouped_tests = self._group_test_cases(test_cases)
            
            for group_name, tests in grouped_tests.items():
                test_file_path = self._generate_test_file(group_name, tests)
                test_files.append(test_file_path)
            
            logging.info(f"Generated {len(test_files)} pytest test files")
            return test_files
            
        except Exception as e:
            logging.error(f"Failed to generate pytest test files: {e}")
            raise
    
    def _generate_conftest(self) -> Path:
        """Generate conftest.py with shared fixtures"""
        conftest_content = '''"""
Pytest configuration and shared fixtures for test automation
"""

import pytest
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime
from pathlib import Path

# Test configuration
BROWSER_TYPE = "{browser}"
HEADLESS = {headless}
BASE_URL = "{base_url}"
SCREENSHOT_DIR = Path("reports/screenshots")

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def browser():
    """Create browser instance for the session"""
    playwright = await async_playwright().start()
    
    if BROWSER_TYPE == "chromium":
        browser = await playwright.chromium.launch(headless=HEADLESS)
    elif BROWSER_TYPE == "firefox":
        browser = await playwright.firefox.launch(headless=HEADLESS)
    elif BROWSER_TYPE == "webkit":
        browser = await playwright.webkit.launch(headless=HEADLESS)
    else:
        browser = await playwright.chromium.launch(headless=HEADLESS)
    
    yield browser
    
    await browser.close()
    await playwright.stop()

@pytest.fixture
async def page(browser):
    """Create a new page for each test"""
    context = await browser.new_context(
        viewport={{"width": 1920, "height": 1080}},
        record_video_dir="reports/videos" if not HEADLESS else None
    )
    
    page = await context.new_page()
    
    yield page
    
    await context.close()

@pytest.fixture(autouse=True)
async def setup_test_logging(page, request):
    """Setup logging for each test"""
    test_name = request.node.name
    logs = []
    
    # Console logging
    page.on("console", lambda msg: logs.append({{
        "timestamp": datetime.now().isoformat(),
        "level": msg.type,
        "message": msg.text
    }}))
    
    # Request/Response logging
    page.on("request", lambda request: logs.append({{
        "timestamp": datetime.now().isoformat(),
        "level": "INFO",
        "message": f"→ {{request.method}} {{request.url}}"
    }}))
    
    page.on("response", lambda response: logs.append({{
        "timestamp": datetime.now().isoformat(),
        "level": "INFO" if response.ok else "ERROR",
        "message": f"← {{response.status}} {{response.url}}"
    }}))
    
    # Error logging
    page.on("pageerror", lambda error: logs.append({{
        "timestamp": datetime.now().isoformat(),
        "level": "ERROR",
        "message": f"Page error: {{error}}"
    }}))
    
    yield
    
    # Save logs after test
    if logs:
        log_file = Path(f"reports/logs/{{test_name}}.json")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'w') as f:
            import json
            json.dump(logs, f, indent=2)

@pytest.fixture(autouse=True)
async def screenshot_on_failure(page, request):
    """Take screenshot on test failure"""
    yield
    
    if request.node.rep_outcome.outcome == "failed":
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = SCREENSHOT_DIR / f"{{request.node.name}}_failure_{{timestamp}}.png"
        
        try:
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"Screenshot saved: {{screenshot_path}}")
        except Exception as e:
            print(f"Failed to take screenshot: {{e}}")

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Make test outcome available to fixtures"""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)

def wait_for_page_load(page, timeout=30000):
    """Helper function to wait for page load"""
    return page.wait_for_load_state("networkidle", timeout=timeout)

def safe_click(page, selector, timeout=10000):
    """Helper function for safe clicking with wait"""
    return page.click(selector, timeout=timeout)

def safe_fill(page, selector, value, timeout=10000):
    """Helper function for safe form filling"""
    return page.fill(selector, value, timeout=timeout)

def assert_element_visible(page, selector, timeout=10000):
    """Helper function to assert element visibility"""
    element = page.wait_for_selector(selector, timeout=timeout)
    assert element.is_visible(), f"Element {{selector}} is not visible"

def assert_text_content(page, selector, expected_text, timeout=10000):
    """Helper function to assert text content"""
    element = page.wait_for_selector(selector, timeout=timeout)
    actual_text = element.text_content()
    assert expected_text in actual_text, f"Expected '{{expected_text}}' not found in '{{actual_text}}'"
'''.format(
            browser=self.pytest_config['browser'],
            headless=str(self.pytest_config['headless']).lower(),
            base_url=self.pytest_config['base_url']
        )
        
        conftest_path = self.pytest_dir / 'conftest.py'
        with open(conftest_path, 'w', encoding='utf-8') as f:
            f.write(conftest_content)
        
        return conftest_path
    
    def _group_test_cases(self, test_cases: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group test cases by type or other criteria"""
        groups = {}
        
        for test_case in test_cases:
            # Group by test type
            test_type = test_case.get('type', 'Functional').lower().replace(' ', '_')
            
            if test_type not in groups:
                groups[test_type] = []
            
            groups[test_type].append(test_case)
        
        return groups
    
    def _generate_test_file(self, group_name: str, test_cases: List[Dict[str, Any]]) -> Path:
        """Generate a pytest test file for a group of test cases"""
        test_file_content = self._create_test_file_header(group_name)
        
        for test_case in test_cases:
            test_function = self._generate_test_function(test_case)
            test_file_content += test_function + '\n\n'
        
        # Sanitize filename
        safe_group_name = re.sub(r'[^\w\-_]', '_', group_name)
        test_file_path = self.pytest_dir / f'test_{safe_group_name}.py'
        
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_file_content)
        
        logging.info(f"Generated test file: {test_file_path}")
        return test_file_path
    
    def _create_test_file_header(self, group_name: str) -> str:
        """Create test file header with imports and metadata"""
        return f'''"""
Generated pytest test file for {group_name} tests
Generated on: {datetime.now().isoformat()}
"""

import pytest
import asyncio
from playwright.async_api import Page
from conftest import wait_for_page_load, safe_click, safe_fill, assert_element_visible, assert_text_content


'''
    
    def _generate_test_function(self, test_case: Dict[str, Any]) -> str:
        """Generate a pytest test function from test case data"""
        # Sanitize test name for function name
        test_name = re.sub(r'[^\w\-_]', '_', test_case.get('title', 'unnamed_test'))
        test_name = test_name.lower().strip('_')
        
        # Create test function
        function_code = f'''@pytest.mark.asyncio
async def test_{test_name}(page: Page):
    """
    {test_case.get('description', test_case.get('title', 'Generated test case'))}
    
    Priority: {test_case.get('priority', 'Medium')}
    Type: {test_case.get('type', 'Functional')}
    Environment: {test_case.get('environment', 'Testing')}
    """
    
    # Test case ID: {test_case.get('id')}
    test_start_time = asyncio.get_event_loop().time()
    
    try:
        # Preconditions
        {self._generate_preconditions_code(test_case)}
        
        # Test steps
        {self._generate_test_steps_code(test_case)}
        
        # Assertions
        {self._generate_assertions_code(test_case)}
        
        # Test passed
        test_end_time = asyncio.get_event_loop().time()
        test_duration = test_end_time - test_start_time
        print(f"Test completed successfully in {{test_duration:.2f}} seconds")
        
    except Exception as e:
        # Take screenshot on failure
        await page.screenshot(path=f"reports/screenshots/test_{test_name}_failure.png", full_page=True)
        raise e'''
        
        return function_code
    
    def _generate_preconditions_code(self, test_case: Dict[str, Any]) -> str:
        """Generate code for test preconditions"""
        preconditions = test_case.get('preconditions', '').strip()
        
        if not preconditions:
            return '# No preconditions specified'
        
        # Convert preconditions to code comments
        lines = preconditions.split('\n')
        code_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                code_lines.append(f'        # {line}')
        
        if not code_lines:
            return '        # No preconditions specified'
        
        return '\n'.join(code_lines)
    
    def _generate_test_steps_code(self, test_case: Dict[str, Any]) -> str:
        """Generate code for test steps"""
        steps = test_case.get('steps', [])
        
        if not steps:
            return '        # No test steps specified\n        pass'
        
        code_lines = []
        
        for i, step in enumerate(steps):
            step_code = self._convert_step_to_code(step, i + 1)
            code_lines.append(step_code)
        
        return '\n        \n'.join(code_lines)
    
    def _convert_step_to_code(self, step: str, step_number: int) -> str:
        """Convert a test step to Python/Playwright code"""
        step_lower = step.lower().strip()
        
        # Add step comment
        code = f'        # Step {step_number}: {step}\n'
        
        try:
            if step_lower.startswith('navigate to') or step_lower.startswith('go to'):
                url = self._extract_url_from_step(step)
                if url:
                    code += f'        await page.goto("{url}")\n'
                    code += f'        await wait_for_page_load(page)'
                else:
                    code += f'        # TODO: Extract URL from step: {step}'
            
            elif step_lower.startswith('click'):
                selector, text = self._extract_click_target(step)
                if selector:
                    code += f'        await safe_click(page, "{selector}")'
                elif text:
                    code += f'        await safe_click(page, \'text="{text}"\')'
                else:
                    code += f'        # TODO: Extract click target from step: {step}'
            
            elif any(keyword in step_lower for keyword in ['fill', 'enter', 'type', 'input']):
                selector, value = self._extract_fill_info(step)
                if selector and value:
                    code += f'        await safe_fill(page, "{selector}", "{value}")'
                else:
                    code += f'        # TODO: Extract fill information from step: {step}'
            
            elif step_lower.startswith('wait'):
                wait_time = self._extract_wait_time(step)
                if wait_time:
                    code += f'        await page.wait_for_timeout({wait_time * 1000})'
                else:
                    code += f'        await page.wait_for_timeout(2000)  # Default wait'
            
            elif step_lower.startswith('select'):
                selector, option = self._extract_select_info(step)
                if selector and option:
                    code += f'        await page.select_option("{selector}", "{option}")'
                else:
                    code += f'        # TODO: Extract select information from step: {step}'
            
            elif any(keyword in step_lower for keyword in ['verify', 'check', 'assert']):
                # These will be handled in assertions
                code += f'        # Verification step (handled in assertions): {step}'
            
            else:
                # Generic step
                code += f'        # TODO: Implement step: {step}\n'
                code += f'        pass'
            
        except Exception as e:
            code += f'        # Error parsing step: {e}\n'
            code += f'        pass'
        
        return code
    
    def _generate_assertions_code(self, test_case: Dict[str, Any]) -> str:
        """Generate code for test assertions"""
        assertions = test_case.get('assertions', [])
        expected_result = test_case.get('expected_result', '').strip()
        
        code_lines = []
        
        # Add expected result as comment
        if expected_result:
            code_lines.append(f'        # Expected Result: {expected_result}')
        
        if not assertions:
            code_lines.append('        # No specific assertions defined')
            return '\n'.join(code_lines)
        
        for assertion in assertions:
            assertion_code = self._convert_assertion_to_code(assertion)
            code_lines.append(assertion_code)
        
        return '\n        \n'.join(code_lines)
    
    def _convert_assertion_to_code(self, assertion: str) -> str:
        """Convert assertion to Python/Playwright code"""
        assertion_lower = assertion.lower().strip()
        
        try:
            if 'element exists' in assertion_lower:
                selector = self._extract_selector_from_text(assertion)
                if selector:
                    return f'        await page.wait_for_selector("{selector}", timeout=10000)'
                else:
                    return f'        # TODO: Extract selector from assertion: {assertion}'
            
            elif 'element visible' in assertion_lower or 'element is visible' in assertion_lower:
                selector = self._extract_selector_from_text(assertion)
                if selector:
                    return f'        assert_element_visible(page, "{selector}")'
                else:
                    return f'        # TODO: Extract selector from assertion: {assertion}'
            
            elif 'text equals' in assertion_lower or 'text contains' in assertion_lower:
                selector, expected_text = self._extract_text_assertion_info(assertion)
                if selector and expected_text:
                    return f'        assert_text_content(page, "{selector}", "{expected_text}")'
                else:
                    return f'        # TODO: Extract text assertion info: {assertion}'
            
            elif 'page title' in assertion_lower:
                expected_title = self._extract_quoted_text(assertion)
                if expected_title:
                    if 'equals' in assertion_lower:
                        return f'        assert await page.title() == "{expected_title}"'
                    else:  # contains
                        return f'        assert "{expected_title}" in await page.title()'
                else:
                    return f'        # TODO: Extract title from assertion: {assertion}'
            
            elif 'url contains' in assertion_lower:
                expected_url = self._extract_quoted_text(assertion)
                if expected_url:
                    return f'        assert "{expected_url}" in page.url'
                else:
                    return f'        # TODO: Extract URL from assertion: {assertion}'
            
            else:
                return f'        # TODO: Implement assertion: {assertion}'
                
        except Exception as e:
            return f'        # Error parsing assertion: {e}'
    
    def _extract_url_from_step(self, step: str) -> Optional[str]:
        """Extract URL from step text"""
        import re
        
        # Look for URL pattern
        url_pattern = r'https?://[^\s]+'
        match = re.search(url_pattern, step)
        if match:
            return match.group()
        
        # Look for quoted text that might be a URL
        quoted_text = self._extract_quoted_text(step)
        if quoted_text and ('http' in quoted_text or '/' in quoted_text):
            return quoted_text
        
        return None
    
    def _extract_click_target(self, step: str) -> tuple:
        """Extract click target (selector or text) from step"""
        # Try to extract selector first
        selector = self._extract_selector_from_text(step)
        if selector:
            return selector, None
        
        # Try to extract text
        text = self._extract_quoted_text(step)
        return None, text
    
    def _extract_fill_info(self, step: str) -> tuple:
        """Extract field selector and value from fill step"""
        import re
        
        # Pattern to match various fill formats
        patterns = [
            r'fill\s+["\']([^"\']+)["\']\s+with\s+["\']([^"\']+)["\']',
            r'enter\s+["\']([^"\']+)["\']\s+in(?:to)?\s+["\']([^"\']+)["\']',
            r'type\s+["\']([^"\']+)["\']\s+in(?:to)?\s+["\']([^"\']+)["\']',
            r'input\s+["\']([^"\']+)["\']\s+in(?:to)?\s+["\']([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, step, re.IGNORECASE)
            if match:
                if 'fill' in pattern or 'type' in pattern:
                    return match.group(1), match.group(2)  # selector, value
                else:
                    return match.group(2), match.group(1)  # selector, value
        
        return None, None
    
    def _extract_select_info(self, step: str) -> tuple:
        """Extract selector and option from select step"""
        import re
        
        pattern = r'select\s+["\']([^"\']+)["\']\s+from\s+["\']([^"\']+)["\']'
        match = re.search(pattern, step, re.IGNORECASE)
        
        if match:
            return match.group(2), match.group(1)  # selector, option
        
        return None, None
    
    def _extract_wait_time(self, step: str) -> Optional[float]:
        """Extract wait time from step"""
        import re
        
        # Look for numbers with time units
        pattern = r'(\d+(?:\.\d+)?)\s*(second|sec|s|millisecond|ms|minute|min|m)'
        match = re.search(pattern, step, re.IGNORECASE)
        
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
    
    def _extract_selector_from_text(self, text: str) -> Optional[str]:
        """Extract CSS selector from text"""
        import re
        
        # Look for common selector patterns in quotes
        quoted_texts = re.findall(r'["\']([^"\']+)["\']', text)
        
        for quoted in quoted_texts:
            # Check if it looks like a selector
            if any(char in quoted for char in ['#', '.', '[', ']']) or \
               quoted.startswith(('input', 'button', 'div', 'span', 'a', 'form')):
                return quoted
        
        return None
    
    def _extract_quoted_text(self, text: str) -> Optional[str]:
        """Extract text from quotes"""
        import re
        
        # Try different quote patterns
        patterns = [r'"([^"]+)"', r"'([^']+)'"]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_text_assertion_info(self, assertion: str) -> tuple:
        """Extract selector and expected text from text assertion"""
        import re
        
        # Pattern to match selector and expected text
        patterns = [
            r'["\']([^"\']+)["\']\s+.*(?:equals|contains)\s+["\']([^"\']+)["\']',
            r'text\s+of\s+["\']([^"\']+)["\']\s+.*\s+["\']([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, assertion, re.IGNORECASE)
            if match:
                return match.group(1), match.group(2)
        
        return None, None
    
    def run_pytest(self, test_files: List[Path], output_format: str = 'json') -> Dict[str, Any]:
        """Run pytest with generated test files"""
        try:
            # Prepare pytest command
            cmd = [
                'python', '-m', 'pytest',
                '--tb=short',
                '--verbose',
                '--capture=no'
            ]
            
            # Add output format
            if output_format == 'json':
                json_report_path = self.pytest_dir / 'pytest_report.json'
                cmd.extend(['--json-report', f'--json-report-file={json_report_path}'])
            
            # Add HTML report
            html_report_path = self.pytest_dir / 'pytest_report.html'
            cmd.extend(['--html', str(html_report_path), '--self-contained-html'])
            
            # Add test files (excluding conftest.py)
            test_file_paths = [str(f) for f in test_files if f.name != 'conftest.py']
            cmd.extend(test_file_paths)
            
            # Set working directory
            cwd = self.pytest_dir
            
            logging.info(f"Running pytest command: {' '.join(cmd)}")
            
            # Run pytest
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self.pytest_config['timeout'] * len(test_file_paths)
            )
            
            # Parse results
            results = {
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'html_report_path': str(html_report_path) if html_report_path.exists() else None
            }
            
            # Parse JSON report if available
            if output_format == 'json' and json_report_path.exists():
                try:
                    with open(json_report_path, 'r') as f:
                        json_data = json.load(f)
                        results['json_report'] = json_data
                        results['summary'] = self._parse_pytest_summary(json_data)
                except Exception as e:
                    logging.warning(f"Failed to parse JSON report: {e}")
            
            logging.info(f"Pytest execution completed with return code: {result.returncode}")
            return results
            
        except subprocess.TimeoutExpired:
            logging.error("Pytest execution timed out")
            return {'error': 'Pytest execution timed out'}
        except Exception as e:
            logging.error(f"Failed to run pytest: {e}")
            return {'error': str(e)}
    
    def _parse_pytest_summary(self, json_report: Dict[str, Any]) -> Dict[str, Any]:
        """Parse pytest JSON report to extract summary"""
        try:
            summary = json_report.get('summary', {})
            
            return {
                'total': summary.get('total', 0),
                'passed': summary.get('passed', 0),
                'failed': summary.get('failed', 0),
                'skipped': summary.get('skipped', 0),
                'errors': summary.get('error', 0),
                'duration': json_report.get('duration', 0),
                'pass_rate': (summary.get('passed', 0) / summary.get('total', 1)) * 100
            }
            
        except Exception as e:
            logging.error(f"Failed to parse pytest summary: {e}")
            return {}
    
    def cleanup_test_files(self, test_files: List[Path]):
        """Clean up generated test files"""
        try:
            for test_file in test_files:
                if test_file.exists():
                    test_file.unlink()
            
            # Clean up pytest cache and reports
            cache_dir = self.pytest_dir / '.pytest_cache'
            if cache_dir.exists():
                import shutil
                shutil.rmtree(cache_dir, ignore_errors=True)
            
            logging.info("Cleaned up generated test files")
            
        except Exception as e:
            logging.warning(f"Failed to cleanup test files: {e}")
    
    def generate_requirements_txt(self) -> Path:
        """Generate requirements.txt for pytest execution"""
        requirements = [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'pytest-html>=3.1.0',
            'pytest-json-report>=1.5.0',
            'playwright>=1.30.0',
            'pytest-timeout>=2.1.0'
        ]
        
        requirements_path = self.pytest_dir / 'requirements.txt'
        with open(requirements_path, 'w') as f:
            f.write('\n'.join(requirements))
        
        return requirements_path
