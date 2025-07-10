#!/usr/bin/env python3
"""
Demo script showing how to use the AI Test Automation Tool programmatically
"""

import sys
import asyncio
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import AppSettings
from storage.database import DatabaseManager
from crawler.site_crawler import SiteCrawler
from ai.test_generator import TestGenerator
from execution.test_runner import TestRunner

class TestAutomationDemo:
    """Demonstration of test automation workflow"""
    
    def __init__(self):
        self.settings = AppSettings()
        self.db_manager = DatabaseManager(self.settings.DATABASE_PATH)
        self.db_manager.initialize()
        
    def demonstrate_workflow(self):
        """Show complete workflow from crawling to test execution"""
        
        print("AI Test Automation Tool - Complete Workflow Demo")
        print("=" * 60)
        
        # 1. Configuration
        print("\n1. Configuration Setup")
        print(f"   Database: {self.settings.DATABASE_PATH}")
        print(f"   AI Model: {self.settings.OPENAI_MODEL}")
        print(f"   Test Timeout: {self.settings.TEST_TIMEOUT}s")
        print(f"   Max Pages: {self.settings.MAX_PAGES_PER_CRAWL}")
        
        # 2. Crawler Configuration
        print("\n2. Web Crawler Configuration")
        crawler_config = self.settings.get_crawler_config()
        crawler = SiteCrawler(crawler_config)
        
        print(f"   Headless Mode: {crawler_config['headless']}")
        print(f"   Viewport: {crawler_config['viewport']}")
        print(f"   User Agent: {crawler_config['user_agent'][:50]}...")
        
        # 3. Test Generator Setup
        print("\n3. AI Test Generator Setup")
        ai_config = self.settings.get_ai_config()
        test_generator = TestGenerator(ai_config, self.db_manager)
        
        print(f"   Local LLM: {'Enabled' if ai_config['use_local_llm'] else 'Disabled'}")
        print(f"   OpenAI Model: {ai_config['openai_model']}")
        print(f"   Temperature: {ai_config['temperature']}")
        
        # 4. Sample Page Analysis
        print("\n4. Sample Page Analysis")
        sample_page_data = {
            'url': 'https://example-salesforce-site.com/login',
            'title': 'Salesforce Login Page',
            'elements': [
                {
                    'type': 'input',
                    'id': 'username',
                    'name': 'username',
                    'placeholder': 'Enter username',
                    'required': True
                },
                {
                    'type': 'input',
                    'id': 'password',
                    'name': 'password',
                    'type': 'password',
                    'required': True
                },
                {
                    'type': 'button',
                    'class': 'login-btn',
                    'text': 'Log In',
                    'type': 'submit'
                }
            ]
        }
        
        print(f"   Page URL: {sample_page_data['url']}")
        print(f"   Elements Found: {len(sample_page_data['elements'])}")
        print(f"   Interactive Elements: {len([e for e in sample_page_data['elements'] if e['type'] in ['input', 'button']])}")
        
        # 5. Test Case Generation (simulated)
        print("\n5. Test Case Generation")
        sample_tests = [
            {
                'title': 'Valid User Login',
                'description': 'Test successful login with valid credentials',
                'type': 'Functional',
                'priority': 'High',
                'steps': [
                    'Navigate to login page',
                    'Enter valid username',
                    'Enter valid password',
                    'Click login button'
                ],
                'assertions': [
                    'User is redirected to dashboard',
                    'Welcome message is displayed',
                    'Logout button is visible'
                ]
            },
            {
                'title': 'Invalid Credentials Error',
                'description': 'Test error handling for invalid credentials',
                'type': 'Negative',
                'priority': 'Medium',
                'steps': [
                    'Navigate to login page',
                    'Enter invalid username',
                    'Enter invalid password',
                    'Click login button'
                ],
                'assertions': [
                    'Error message is displayed',
                    'User remains on login page',
                    'Form fields are cleared'
                ]
            }
        ]
        
        print(f"   Generated Tests: {len(sample_tests)}")
        for i, test in enumerate(sample_tests, 1):
            print(f"   {i}. {test['title']} ({test['type']}) - Priority: {test['priority']}")
        
        # 6. Test Execution Setup
        print("\n6. Test Execution Configuration")
        test_config = self.settings.get_test_config()
        
        print(f"   Parallel Workers: {test_config['parallel_workers']}")
        print(f"   Timeout: {test_config['timeout']}s")
        print(f"   Screenshots: {'Enabled' if test_config['screenshot_on_failure'] else 'Disabled'}")
        print(f"   Retry Count: {test_config['retry_count']}")
        
        # 7. Reporting
        print("\n7. Report Generation")
        print(f"   HTML Reports: {self.settings.HTML_REPORTS_DIR}")
        print(f"   Test Results: {self.settings.REPORTS_DIR}")
        
        return True
    
    def show_database_schema(self):
        """Display database schema information"""
        print("\n" + "=" * 60)
        print("Database Schema Information")
        print("=" * 60)
        
        # Test cases table structure
        print("\nTest Cases Table:")
        print("   - id (INTEGER PRIMARY KEY)")
        print("   - title (TEXT NOT NULL)")
        print("   - description (TEXT)")
        print("   - type (TEXT) # Functional, Integration, etc.")
        print("   - priority (TEXT) # High, Medium, Low")
        print("   - steps (JSON)")
        print("   - assertions (JSON)")
        print("   - environment (TEXT)")
        print("   - created_at (DATETIME)")
        print("   - updated_at (DATETIME)")
        
        print("\nExecution Results Table:")
        print("   - id (INTEGER PRIMARY KEY)")
        print("   - test_case_id (INTEGER FOREIGN KEY)")
        print("   - status (TEXT) # PASSED, FAILED, SKIPPED")
        print("   - duration (REAL)")
        print("   - error_message (TEXT)")
        print("   - screenshots (JSON)")
        print("   - executed_at (DATETIME)")
        
        print("\nCrawl Results Table:")
        print("   - id (INTEGER PRIMARY KEY)")
        print("   - url (TEXT)")
        print("   - title (TEXT)")
        print("   - elements (JSON)")
        print("   - crawled_at (DATETIME)")

def main():
    """Main demo function"""
    demo = TestAutomationDemo()
    
    try:
        # Run workflow demonstration
        demo.demonstrate_workflow()
        demo.show_database_schema()
        
        print("\n" + "=" * 60)
        print("Demo Complete - Tool Ready for Production Use!")
        print("=" * 60)
        
        print("\nNext Steps:")
        print("1. Configure Salesforce credentials in GUI")
        print("2. Set up target site URLs for crawling")
        print("3. Generate test cases using AI")
        print("4. Execute tests and review reports")
        print("5. Set up CI/CD integration if needed")
        
    except Exception as e:
        print(f"Demo failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()