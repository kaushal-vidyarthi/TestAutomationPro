"""
Configuration settings for the AI-driven test automation tool
"""

import os
import time
from pathlib import Path
from typing import Dict, Any

class AppSettings:
    """Application configuration settings"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "data"
        self.temp_dir = self.project_root / "temp"
        self.logs_dir = self.project_root / "logs"
        
        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Database settings
        self.DATABASE_PATH = self.data_dir / "test_automation.db"
        self.VECTOR_DB_PATH = self.data_dir / "vector_store"
        
        # Logging settings
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE = self.logs_dir / "app.log"
        
        # AI/LLM settings
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.OPENAI_MODEL = "gpt-4o"  # newest OpenAI model released May 13, 2024
        self.LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama2")
        self.USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "true").lower() == "true"
        
        # Crawler settings - Enhanced for better reliability
        self.CRAWLER_TIMEOUT = int(os.getenv("CRAWLER_TIMEOUT", "60"))
        self.CRAWLER_HEADLESS = os.getenv("CRAWLER_HEADLESS", "false").lower() == "true"  # Default to visible for debugging
        self.MAX_PAGES_PER_CRAWL = int(os.getenv("MAX_PAGES_PER_CRAWL", "50"))
        
        # Salesforce settings - Test credentials provided by user
        self.SF_LOGIN_URL = os.getenv("SF_LOGIN_URL", "https://nosoftware-fun-47332-dev-ed.scratch.my.site.com/ESE25/login")
        self.SF_USERNAME = os.getenv("SF_USERNAME", "kaushal.vidyarthi@fantailtech.com")
        self.SF_PASSWORD = os.getenv("SF_PASSWORD", "Q@12345678")
        self.SF_SECURITY_TOKEN = os.getenv("SF_SECURITY_TOKEN", "")
        
        # Test execution settings
        self.TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "60"))
        self.PARALLEL_TESTS = int(os.getenv("PARALLEL_TESTS", "3"))
        self.SCREENSHOT_ON_FAILURE = os.getenv("SCREENSHOT_ON_FAILURE", "true").lower() == "true"
        
        # Report settings
        self.REPORTS_DIR = self.project_root / "reports"
        self.REPORTS_DIR.mkdir(exist_ok=True)
        self.ALLURE_RESULTS_DIR = self.REPORTS_DIR / "allure-results"
        self.HTML_REPORTS_DIR = self.REPORTS_DIR / "html"
        
        # GUI settings
        self.WINDOW_WIDTH = int(os.getenv("WINDOW_WIDTH", "1200"))
        self.WINDOW_HEIGHT = int(os.getenv("WINDOW_HEIGHT", "800"))
        self.THEME = os.getenv("THEME", "light")
        
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return {
            "database_path": str(self.DATABASE_PATH),
            "vector_db_path": str(self.VECTOR_DB_PATH),
            "backup_enabled": True,
            "backup_interval": 3600  # 1 hour
        }
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI/LLM configuration"""
        return {
            "use_local_llm": self.USE_LOCAL_LLM,
            "openai_api_key": self.OPENAI_API_KEY,
            "openai_model": self.OPENAI_MODEL,
            "local_model": self.LOCAL_LLM_MODEL,
            "max_tokens": 2000,
            "temperature": 0.3,
            "top_p": 0.9
        }
    
    def get_crawler_config(self) -> Dict[str, Any]:
        """Get web crawler configuration"""
        return {
            "timeout": self.CRAWLER_TIMEOUT,
            "headless": self.CRAWLER_HEADLESS,
            "max_pages": self.MAX_PAGES_PER_CRAWL,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "viewport": {"width": 1920, "height": 1080},
            "wait_for_load": 3000  # ms
        }
    
    def get_salesforce_config(self) -> Dict[str, Any]:
        """Get Salesforce configuration"""
        return {
            "login_url": self.SF_LOGIN_URL,
            "username": self.SF_USERNAME,
            "password": self.SF_PASSWORD,
            "security_token": self.SF_SECURITY_TOKEN,
            "domain": "login",  # or "test" for sandbox
            "api_version": "58.0"
        }
    
    def get_test_config(self) -> Dict[str, Any]:
        """Get test execution configuration"""
        return {
            "timeout": self.TEST_TIMEOUT,
            "parallel_workers": self.PARALLEL_TESTS,
            "screenshot_on_failure": self.SCREENSHOT_ON_FAILURE,
            "retry_count": 2,
            "retry_delay": 1.0
        }
    
    def get_timestamp(self) -> float:
        """Get current timestamp"""
        return time.time()
    
    def is_offline_mode(self) -> bool:
        """Check if application should run in offline mode"""
        return self.USE_LOCAL_LLM or not self.OPENAI_API_KEY
    
    def validate_required_settings(self) -> Dict[str, str]:
        """Validate required settings and return any errors"""
        errors = {}
        
        if not self.is_offline_mode() and not self.OPENAI_API_KEY:
            errors["openai_api_key"] = "OpenAI API key is required for cloud mode"
        
        if not self.SF_USERNAME:
            errors["sf_username"] = "Salesforce username is required"
        
        if not self.SF_PASSWORD:
            errors["sf_password"] = "Salesforce password is required"
        
        return errors
