#!/usr/bin/env python3
"""
AI-Driven Test Automation Tool for Salesforce Experience Cloud
Main application entry point with PyQt6 GUI
"""

import sys
import os
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import AppSettings
from gui.main_window import MainWindow
from storage.database import DatabaseManager
from utils.logger import setup_logging

class TestAutomationApp:
    """Main application class for AI-driven test automation tool"""
    
    def __init__(self):
        self.app = None
        self.main_window = None
        self.settings = AppSettings()
        self.db_manager = None
        
    def initialize(self):
        """Initialize the application components"""
        try:
            # Setup logging
            setup_logging(self.settings.LOG_LEVEL, self.settings.LOG_FILE)
            logging.info("Starting AI-driven Test Automation Tool")
            
            # Initialize database
            self.db_manager = DatabaseManager(self.settings.DATABASE_PATH)
            self.db_manager.initialize()
            
            # Create QApplication
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("AI Test Automation Tool")
            self.app.setApplicationVersion("1.0.0")
            self.app.setOrganizationName("AI Test Solutions")
            
            # Set application icon
            icon_path = project_root / "assets" / "app_icon.svg"
            if icon_path.exists():
                self.app.setWindowIcon(QIcon(str(icon_path)))
            
            # Load styles
            self.load_styles()
            
            # Create main window
            self.main_window = MainWindow(self.settings, self.db_manager)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize application: {e}")
            if self.app:
                QMessageBox.critical(None, "Initialization Error", 
                                   f"Failed to initialize application: {str(e)}")
            return False
    
    def load_styles(self):
        """Load QSS stylesheet for the application"""
        try:
            style_path = project_root / "gui" / "styles.qss"
            if style_path.exists():
                with open(style_path, 'r', encoding='utf-8') as f:
                    self.app.setStyleSheet(f.read())
        except Exception as e:
            logging.warning(f"Failed to load styles: {e}")
    
    def run(self):
        """Run the application main loop"""
        if not self.initialize():
            return 1
            
        try:
            # Show main window
            self.main_window.show()
            
            # Setup periodic tasks
            self.setup_periodic_tasks()
            
            # Start event loop
            return self.app.exec()
            
        except Exception as e:
            logging.error(f"Application runtime error: {e}")
            QMessageBox.critical(None, "Runtime Error", 
                               f"Application encountered an error: {str(e)}")
            return 1
    
    def setup_periodic_tasks(self):
        """Setup periodic background tasks"""
        # Cleanup timer for temporary files and old logs
        cleanup_timer = QTimer()
        cleanup_timer.timeout.connect(self.cleanup_periodic)
        cleanup_timer.start(300000)  # 5 minutes
    
    def cleanup_periodic(self):
        """Periodic cleanup of temporary files and old data"""
        try:
            # Clean old log files
            log_dir = Path(self.settings.LOG_FILE).parent
            if log_dir.exists():
                for log_file in log_dir.glob("*.log.*"):
                    if log_file.stat().st_mtime < (
                        self.settings.get_timestamp() - 7 * 24 * 3600
                    ):  # 7 days old
                        log_file.unlink()
            
            # Clean temporary test files
            temp_dir = Path(self.settings.TEMP_DIR)
            if temp_dir.exists():
                for temp_file in temp_dir.glob("test_*"):
                    if temp_file.stat().st_mtime < (
                        self.settings.get_timestamp() - 24 * 3600
                    ):  # 1 day old
                        if temp_file.is_file():
                            temp_file.unlink()
                        elif temp_file.is_dir():
                            import shutil
                            shutil.rmtree(temp_file, ignore_errors=True)
                            
        except Exception as e:
            logging.warning(f"Periodic cleanup failed: {e}")

def main():
    """Main entry point"""
    app = TestAutomationApp()
    return app.run()

if __name__ == "__main__":
    sys.exit(main())
