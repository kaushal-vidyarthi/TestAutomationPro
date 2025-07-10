"""
Test execution engine for running automated test cases
"""

import asyncio
import logging
import json
import time
import uuid
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
import concurrent.futures
from dataclasses import dataclass
import subprocess
import tempfile

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from storage.database import DatabaseManager
from execution.pytest_generator import PytestGenerator
from reporting.html_reporter import HTMLReporter

@dataclass
class TestResult:
    """Test execution result"""
    test_case_id: int
    execution_id: str
    status: str  # 'Passed', 'Failed', 'Skipped', 'Error'
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    screenshots: List[str] = None
    logs: List[Dict[str, Any]] = None
    performance_metrics: Dict[str, Any] = None
    step_results: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.screenshots is None:
            self.screenshots = []
        if self.logs is None:
            self.logs = []
        if self.performance_metrics is None:
            self.performance_metrics = {}
        if self.step_results is None:
            self.step_results = []

class TestRunner:
    """Main test execution engine"""
    
    def __init__(self, config: Dict[str, Any], db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.pytest_generator = PytestGenerator(config)
        self.html_reporter = HTMLReporter(config)
        
        # Execution state
        self.current_executions = {}
        self.browser_pool = []
        self.max_parallel = config.get('parallel_workers', 3)
        
        # Directories
        self.temp_dir = Path(config.get('temp_dir', 'temp'))
        self.reports_dir = Path(config.get('reports_dir', 'reports'))
        self.screenshots_dir = self.reports_dir / 'screenshots'
        
        # Create directories
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Performance monitoring
        self.performance_enabled = config.get('performance_monitoring', True)
        
    async def initialize(self):
        """Initialize test runner resources"""
        try:
            # Initialize browser pool for parallel execution
            await self._initialize_browser_pool()
            logging.info("Test runner initialized successfully")
            
        except Exception as e:
            logging.error(f"Failed to initialize test runner: {e}")
            raise
    
    async def _initialize_browser_pool(self):
        """Initialize browser instances for parallel execution"""
        try:
            self.playwright = await async_playwright().start()
            
            browser_type = self.config.get('browser', 'chromium')
            headless = self.config.get('headless', True)
            
            for i in range(self.max_parallel):
                if browser_type == 'chromium':
                    browser = await self.playwright.chromium.launch(headless=headless)
                elif browser_type == 'firefox':
                    browser = await self.playwright.firefox.launch(headless=headless)
                elif browser_type == 'webkit':
                    browser = await self.playwright.webkit.launch(headless=headless)
                else:
                    browser = await self.playwright.chromium.launch(headless=headless)
                
                self.browser_pool.append(browser)
            
            logging.info(f"Initialized browser pool with {len(self.browser_pool)} instances")
            
        except Exception as e:
            logging.error(f"Failed to initialize browser pool: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup test runner resources"""
        try:
            # Close browser pool
            for browser in self.browser_pool:
                await browser.close()
            
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            
            logging.info("Test runner cleanup completed")
            
        except Exception as e:
            logging.warning(f"Error during test runner cleanup: {e}")
    
    def run_tests_async(self, test_case_ids: Optional[List[int]] = None, 
                       completion_callback: Optional[Callable] = None):
        """Run tests asynchronously"""
        asyncio.create_task(self._run_tests_async(test_case_ids, completion_callback))
    
    async def _run_tests_async(self, test_case_ids: Optional[List[int]] = None,
                              completion_callback: Optional[Callable] = None):
        """Internal async test execution"""
        try:
            await self.initialize()
            
            # Get test cases to run
            if test_case_ids:
                test_cases = []
                for test_id in test_case_ids:
                    test_case = self.db_manager.get_test_case(test_id)
                    if test_case:
                        test_cases.append(test_case)
            else:
                # Run all active test cases
                test_cases = self.db_manager.get_test_cases({
                    'status': 'Ready'
                })
            
            if not test_cases:
                logging.warning("No test cases found to execute")
                return
            
            # Execute tests
            execution_id = str(uuid.uuid4())
            results = await self.execute_test_suite(test_cases, execution_id)
            
            # Generate report
            report_path = await self.generate_execution_report(execution_id, results)
            
            # Call completion callback
            if completion_callback:
                summary = self._generate_execution_summary(results)
                summary['report_path'] = str(report_path)
                completion_callback(summary)
            
        except Exception as e:
            logging.error(f"Test execution failed: {e}")
            if completion_callback:
                completion_callback({'error': str(e)})
        finally:
            await self.cleanup()
    
    async def execute_test_suite(self, test_cases: List[Dict[str, Any]], 
                                execution_id: str) -> List[TestResult]:
        """Execute a suite of test cases"""
        logging.info(f"Starting execution of {len(test_cases)} test cases")
        
        # Create semaphore for parallel execution
        semaphore = asyncio.Semaphore(self.max_parallel)
        
        # Create execution tasks
        tasks = []
        for test_case in test_cases:
            task = self._execute_single_test_with_semaphore(
                semaphore, test_case, execution_id
            )
            tasks.append(task)
        
        # Execute tests in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        test_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logging.error(f"Test case {test_cases[i]['id']} failed with exception: {result}")
                # Create error result
                error_result = TestResult(
                    test_case_id=test_cases[i]['id'],
                    execution_id=execution_id,
                    status='Error',
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    error_message=str(result)
                )
                test_results.append(error_result)
            else:
                test_results.append(result)
        
        logging.info(f"Test suite execution completed. Results: {len(test_results)}")
        return test_results
    
    async def _execute_single_test_with_semaphore(self, semaphore: asyncio.Semaphore,
                                                 test_case: Dict[str, Any], 
                                                 execution_id: str) -> TestResult:
        """Execute single test with concurrency control"""
        async with semaphore:
            # Get available browser
            browser = self.browser_pool[0]  # Simple round-robin could be improved
            
            return await self.execute_single_test(test_case, execution_id, browser)
    
    async def execute_single_test(self, test_case: Dict[str, Any], 
                                 execution_id: str, browser: Browser) -> TestResult:
        """Execute a single test case"""
        test_result = TestResult(
            test_case_id=test_case['id'],
            execution_id=execution_id,
            status='Running',
            start_time=datetime.now()
        )
        
        context = None
        page = None
        
        try:
            logging.info(f"Executing test case: {test_case['title']}")
            
            # Create database execution record
            db_execution_id = self.db_manager.create_test_execution({
                'test_case_id': test_case['id'],
                'execution_id': execution_id,
                'status': 'Running',
                'start_time': test_result.start_time.isoformat(),
                'browser': self.config.get('browser', 'chromium'),
                'environment': test_case.get('environment', 'Testing')
            })
            
            # Create browser context
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                record_video_dir=str(self.temp_dir / 'videos') if self.config.get('record_video') else None
            )
            
            page = await context.new_page()
            
            # Setup page logging
            await self._setup_page_logging(page, test_result)
            
            # Execute test steps
            await self._execute_test_steps(test_case, page, test_result)
            
            # Verify assertions
            await self._verify_assertions(test_case, page, test_result)
            
            # Set success status
            test_result.status = 'Passed'
            test_result.end_time = datetime.now()
            test_result.duration = (test_result.end_time - test_result.start_time).total_seconds()
            
            # Collect performance metrics
            if self.performance_enabled:
                test_result.performance_metrics = await self._collect_performance_metrics(page)
            
            logging.info(f"Test case {test_case['title']} passed in {test_result.duration:.2f}s")
            
        except Exception as e:
            test_result.status = 'Failed'
            test_result.end_time = datetime.now()
            test_result.duration = (test_result.end_time - test_result.start_time).total_seconds()
            test_result.error_message = str(e)
            test_result.stack_trace = self._get_stack_trace()
            
            # Take failure screenshot
            if page:
                screenshot_path = await self._take_screenshot(page, f"failure_{test_case['id']}")
                if screenshot_path:
                    test_result.screenshots.append(screenshot_path)
            
            logging.error(f"Test case {test_case['title']} failed: {e}")
            
        finally:
            # Cleanup
            if page:
                await page.close()
            if context:
                await context.close()
            
            # Update database
            self._update_execution_record(db_execution_id, test_result)
        
        return test_result
    
    async def _setup_page_logging(self, page: Page, test_result: TestResult):
        """Setup page logging and monitoring"""
        # Console logging
        page.on('console', lambda msg: test_result.logs.append({
            'timestamp': datetime.now().isoformat(),
            'level': msg.type,
            'message': msg.text
        }))
        
        # Request logging
        page.on('request', lambda request: test_result.logs.append({
            'timestamp': datetime.now().isoformat(),
            'level': 'INFO',
            'message': f"Request: {request.method} {request.url}"
        }))
        
        # Response logging
        page.on('response', lambda response: test_result.logs.append({
            'timestamp': datetime.now().isoformat(),
            'level': 'INFO' if response.ok else 'ERROR',
            'message': f"Response: {response.status} {response.url}"
        }))
        
        # Error logging
        page.on('pageerror', lambda error: test_result.logs.append({
            'timestamp': datetime.now().isoformat(),
            'level': 'ERROR',
            'message': f"Page error: {error}"
        }))
    
    async def _execute_test_steps(self, test_case: Dict[str, Any], page: Page, test_result: TestResult):
        """Execute test case steps"""
        steps = test_case.get('steps', [])
        
        for i, step in enumerate(steps):
            step_start_time = datetime.now()
            step_result = {
                'step_number': i + 1,
                'description': step,
                'status': 'Running',
                'start_time': step_start_time.isoformat(),
                'notes': ''
            }
            
            try:
                # Parse and execute step
                await self._execute_step(step, page)
                
                step_result['status'] = 'Passed'
                step_result['end_time'] = datetime.now().isoformat()
                step_result['duration'] = (datetime.now() - step_start_time).total_seconds()
                
                # Take step screenshot if configured
                if self.config.get('screenshot_on_steps'):
                    screenshot_path = await self._take_screenshot(page, f"step_{i+1}")
                    if screenshot_path:
                        test_result.screenshots.append(screenshot_path)
                
            except Exception as e:
                step_result['status'] = 'Failed'
                step_result['end_time'] = datetime.now().isoformat()
                step_result['duration'] = (datetime.now() - step_start_time).total_seconds()
                step_result['notes'] = str(e)
                
                # Take failure screenshot
                screenshot_path = await self._take_screenshot(page, f"step_{i+1}_failure")
                if screenshot_path:
                    test_result.screenshots.append(screenshot_path)
                
                raise Exception(f"Step {i+1} failed: {e}")
            
            test_result.step_results.append(step_result)
    
    async def _execute_step(self, step: str, page: Page):
        """Execute a single test step"""
        # This is a simplified step execution - in a real implementation,
        # you would parse the step text and convert it to specific actions
        
        step_lower = step.lower().strip()
        
        try:
            if step_lower.startswith('navigate to') or step_lower.startswith('go to'):
                # Extract URL from step
                url = self._extract_url_from_step(step)
                if url:
                    await page.goto(url, wait_until='networkidle')
                else:
                    raise Exception(f"Could not extract URL from step: {step}")
            
            elif step_lower.startswith('click'):
                # Extract selector from step
                selector = self._extract_selector_from_step(step)
                if selector:
                    await page.click(selector)
                else:
                    # Try to find by text
                    text = self._extract_text_from_step(step)
                    if text:
                        await page.click(f'text="{text}"')
                    else:
                        raise Exception(f"Could not find element to click in step: {step}")
            
            elif step_lower.startswith('fill') or step_lower.startswith('enter') or step_lower.startswith('type'):
                # Extract field and value
                selector, value = self._extract_fill_info_from_step(step)
                if selector and value:
                    await page.fill(selector, value)
                else:
                    raise Exception(f"Could not extract fill information from step: {step}")
            
            elif step_lower.startswith('wait'):
                # Extract wait time or condition
                wait_time = self._extract_wait_time_from_step(step)
                if wait_time:
                    await page.wait_for_timeout(wait_time * 1000)
                else:
                    # Default wait
                    await page.wait_for_timeout(2000)
            
            elif step_lower.startswith('verify') or step_lower.startswith('check') or step_lower.startswith('assert'):
                # Handle verification steps in assertions
                pass
            
            else:
                # Generic step - log and continue
                logging.warning(f"Unknown step type: {step}")
            
            # Small delay between steps
            await page.wait_for_timeout(500)
            
        except Exception as e:
            raise Exception(f"Failed to execute step '{step}': {e}")
    
    def _extract_url_from_step(self, step: str) -> Optional[str]:
        """Extract URL from navigation step"""
        import re
        # Look for URL pattern
        url_pattern = r'https?://[^\s]+'
        match = re.search(url_pattern, step)
        if match:
            return match.group()
        
        # Look for quoted URL
        quote_pattern = r'["\']([^"\']+)["\']'
        match = re.search(quote_pattern, step)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_selector_from_step(self, step: str) -> Optional[str]:
        """Extract CSS selector from step"""
        import re
        
        # Look for CSS selector patterns
        selectors = [
            r'#[\w-]+',  # ID selector
            r'\.[\w-]+',  # Class selector
            r'\[[\w\-="\']+\]',  # Attribute selector
            r'[\w-]+\[[\w\-="\']+\]',  # Element with attribute
        ]
        
        for pattern in selectors:
            match = re.search(pattern, step)
            if match:
                return match.group()
        
        return None
    
    def _extract_text_from_step(self, step: str) -> Optional[str]:
        """Extract text content from step"""
        import re
        
        # Look for quoted text
        quote_patterns = [
            r'"([^"]+)"',
            r"'([^']+)'",
            r'button[^"]+"([^"]+)"',
            r'link[^"]+"([^"]+)"'
        ]
        
        for pattern in quote_patterns:
            match = re.search(pattern, step)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_fill_info_from_step(self, step: str) -> tuple:
        """Extract field selector and value from fill step"""
        import re
        
        # Pattern to match "fill field with value"
        patterns = [
            r'fill\s+["\']([^"\']+)["\']\s+with\s+["\']([^"\']+)["\']',
            r'enter\s+["\']([^"\']+)["\']\s+in\s+["\']([^"\']+)["\']',
            r'type\s+["\']([^"\']+)["\']\s+into\s+["\']([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, step, re.IGNORECASE)
            if match:
                # Return value, selector (order depends on pattern)
                if 'fill' in pattern:
                    return match.group(1), match.group(2)  # selector, value
                else:
                    return match.group(2), match.group(1)  # selector, value
        
        return None, None
    
    def _extract_wait_time_from_step(self, step: str) -> Optional[int]:
        """Extract wait time from step"""
        import re
        
        # Look for numbers followed by time units
        time_pattern = r'(\d+)\s*(second|sec|s|millisecond|ms|minute|min|m)'
        match = re.search(time_pattern, step, re.IGNORECASE)
        
        if match:
            value = int(match.group(1))
            unit = match.group(2).lower()
            
            if unit in ['second', 'sec', 's']:
                return value
            elif unit in ['millisecond', 'ms']:
                return value / 1000
            elif unit in ['minute', 'min', 'm']:
                return value * 60
        
        return None
    
    async def _verify_assertions(self, test_case: Dict[str, Any], page: Page, test_result: TestResult):
        """Verify test case assertions"""
        assertions = test_case.get('assertions', [])
        
        for assertion in assertions:
            try:
                await self._verify_single_assertion(assertion, page)
                
                test_result.logs.append({
                    'timestamp': datetime.now().isoformat(),
                    'level': 'INFO',
                    'message': f"Assertion passed: {assertion}"
                })
                
            except Exception as e:
                raise Exception(f"Assertion failed: {assertion} - {e}")
    
    async def _verify_single_assertion(self, assertion: str, page: Page):
        """Verify a single assertion"""
        assertion_lower = assertion.lower().strip()
        
        if 'element exists' in assertion_lower:
            selector = self._extract_selector_from_assertion(assertion)
            if not selector:
                raise Exception(f"Could not extract selector from assertion: {assertion}")
            
            element = await page.query_selector(selector)
            if not element:
                raise Exception(f"Element not found: {selector}")
        
        elif 'element visible' in assertion_lower or 'element is visible' in assertion_lower:
            selector = self._extract_selector_from_assertion(assertion)
            if not selector:
                raise Exception(f"Could not extract selector from assertion: {assertion}")
            
            element = await page.query_selector(selector)
            if not element:
                raise Exception(f"Element not found: {selector}")
            
            is_visible = await element.is_visible()
            if not is_visible:
                raise Exception(f"Element not visible: {selector}")
        
        elif 'text equals' in assertion_lower or 'text contains' in assertion_lower:
            selector, expected_text = self._extract_text_assertion_info(assertion)
            if not selector or not expected_text:
                raise Exception(f"Could not extract text assertion info: {assertion}")
            
            element = await page.query_selector(selector)
            if not element:
                raise Exception(f"Element not found: {selector}")
            
            actual_text = await element.text_content()
            
            if 'text equals' in assertion_lower:
                if actual_text != expected_text:
                    raise Exception(f"Text mismatch. Expected: '{expected_text}', Actual: '{actual_text}'")
            else:  # contains
                if expected_text not in actual_text:
                    raise Exception(f"Text not found. Expected: '{expected_text}' in '{actual_text}'")
        
        elif 'page title' in assertion_lower:
            expected_title = self._extract_text_from_step(assertion)
            if not expected_title:
                raise Exception(f"Could not extract expected title: {assertion}")
            
            actual_title = await page.title()
            
            if 'equals' in assertion_lower:
                if actual_title != expected_title:
                    raise Exception(f"Title mismatch. Expected: '{expected_title}', Actual: '{actual_title}'")
            elif 'contains' in assertion_lower:
                if expected_title not in actual_title:
                    raise Exception(f"Title does not contain expected text. Expected: '{expected_title}' in '{actual_title}'")
        
        else:
            logging.warning(f"Unknown assertion type: {assertion}")
    
    def _extract_selector_from_assertion(self, assertion: str) -> Optional[str]:
        """Extract selector from assertion"""
        import re
        
        # Look for quoted selectors
        quote_pattern = r'["\']([^"\']+)["\']'
        matches = re.findall(quote_pattern, assertion)
        
        for match in matches:
            # Check if it looks like a selector
            if any(char in match for char in ['#', '.', '[', ']']) or match.startswith(('input', 'button', 'div', 'span')):
                return match
        
        return None
    
    def _extract_text_assertion_info(self, assertion: str) -> tuple:
        """Extract selector and expected text from text assertion"""
        import re
        
        # Pattern to match selector and text
        pattern = r'["\']([^"\']+)["\']\s+.*\s+["\']([^"\']+)["\']'
        match = re.search(pattern, assertion)
        
        if match:
            return match.group(1), match.group(2)
        
        return None, None
    
    async def _collect_performance_metrics(self, page: Page) -> Dict[str, Any]:
        """Collect page performance metrics"""
        try:
            metrics = await page.evaluate('''
                () => {
                    const perfData = performance.getEntriesByType('navigation')[0];
                    const paintEntries = performance.getEntriesByType('paint');
                    
                    return {
                        load_time: perfData ? perfData.loadEventEnd - perfData.navigationStart : 0,
                        dom_ready: perfData ? perfData.domContentLoadedEventEnd - perfData.navigationStart : 0,
                        first_paint: paintEntries.find(entry => entry.name === 'first-paint')?.startTime || 0,
                        first_contentful_paint: paintEntries.find(entry => entry.name === 'first-contentful-paint')?.startTime || 0,
                        memory_usage: performance.memory ? performance.memory.usedJSHeapSize : 0
                    };
                }
            ''')
            
            return metrics
            
        except Exception as e:
            logging.debug(f"Could not collect performance metrics: {e}")
            return {}
    
    async def _take_screenshot(self, page: Page, name: str) -> Optional[str]:
        """Take page screenshot"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            screenshot_path = self.screenshots_dir / filename
            
            await page.screenshot(path=str(screenshot_path), full_page=True)
            
            return str(screenshot_path)
            
        except Exception as e:
            logging.error(f"Failed to take screenshot: {e}")
            return None
    
    def _get_stack_trace(self) -> str:
        """Get current stack trace"""
        import traceback
        return traceback.format_exc()
    
    def _update_execution_record(self, db_execution_id: int, test_result: TestResult):
        """Update database execution record"""
        try:
            update_data = {
                'status': test_result.status,
                'end_time': test_result.end_time.isoformat() if test_result.end_time else None,
                'duration': test_result.duration,
                'error_message': test_result.error_message,
                'stack_trace': test_result.stack_trace,
                'screenshots': test_result.screenshots,
                'logs': test_result.logs,
                'performance_metrics': test_result.performance_metrics
            }
            
            self.db_manager.update_test_execution(db_execution_id, update_data)
            
            # Store step results
            for step_result in test_result.step_results:
                self.db_manager.get_connection().execute("""
                    INSERT INTO test_execution_steps (
                        execution_id, step_number, description, status,
                        start_time, end_time, duration, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    db_execution_id,
                    step_result['step_number'],
                    step_result['description'],
                    step_result['status'],
                    step_result['start_time'],
                    step_result.get('end_time'),
                    step_result.get('duration'),
                    step_result.get('notes', '')
                ))
            
            self.db_manager.get_connection().commit()
            
        except Exception as e:
            logging.error(f"Failed to update execution record: {e}")
    
    async def generate_execution_report(self, execution_id: str, results: List[TestResult]) -> Path:
        """Generate HTML execution report"""
        try:
            report_data = {
                'execution_id': execution_id,
                'execution_time': datetime.now(),
                'results': results,
                'summary': self._generate_execution_summary(results)
            }
            
            report_path = await self.html_reporter.generate_execution_report(report_data)
            
            # Store report in database
            self.db_manager.get_connection().execute("""
                INSERT INTO test_reports (execution_id, report_type, report_path, summary)
                VALUES (?, ?, ?, ?)
            """, (
                execution_id,
                'HTML',
                str(report_path),
                json.dumps(report_data['summary'])
            ))
            self.db_manager.get_connection().commit()
            
            return report_path
            
        except Exception as e:
            logging.error(f"Failed to generate execution report: {e}")
            raise
    
    def _generate_execution_summary(self, results: List[TestResult]) -> Dict[str, Any]:
        """Generate execution summary statistics"""
        total = len(results)
        passed = sum(1 for r in results if r.status == 'Passed')
        failed = sum(1 for r in results if r.status == 'Failed')
        errors = sum(1 for r in results if r.status == 'Error')
        skipped = sum(1 for r in results if r.status == 'Skipped')
        
        total_duration = sum(r.duration or 0 for r in results)
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'skipped': skipped,
            'pass_rate': (passed / total * 100) if total > 0 else 0,
            'total_duration': total_duration,
            'average_duration': (total_duration / total) if total > 0 else 0
        }
    
    def run_pytest_tests(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run tests using pytest (alternative execution method)"""
        try:
            # Generate pytest files
            test_files = self.pytest_generator.generate_test_files(test_cases)
            
            # Run pytest
            results = self.pytest_generator.run_pytest(test_files)
            
            return results
            
        except Exception as e:
            logging.error(f"Failed to run pytest tests: {e}")
            return {'error': str(e)}
    
    def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get current execution status"""
        if execution_id in self.current_executions:
            return self.current_executions[execution_id]
        
        # Check database for completed executions
        try:
            conn = self.db_manager.get_connection()
            cursor = conn.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status = 'Passed' THEN 1 ELSE 0 END) as passed,
                       SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) as failed,
                       SUM(CASE WHEN status = 'Running' THEN 1 ELSE 0 END) as running
                FROM test_executions 
                WHERE execution_id = ?
            """, (execution_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'execution_id': execution_id,
                    'total': result['total'],
                    'passed': result['passed'],
                    'failed': result['failed'],
                    'running': result['running'],
                    'status': 'Completed' if result['running'] == 0 else 'Running'
                }
        
        except Exception as e:
            logging.error(f"Failed to get execution status: {e}")
        
        return {'execution_id': execution_id, 'status': 'Unknown'}
