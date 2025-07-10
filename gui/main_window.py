"""
Main window for the AI-driven test automation tool
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit, QLabel,
    QProgressBar, QSplitter, QGroupBox, QMessageBox, QToolBar,
    QStatusBar, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon, QFont

from gui.test_case_dialog import TestCaseDialog
from gui.crawler_dialog import CrawlerDialog
from gui.results_viewer import ResultsViewer
from crawler.site_crawler import SiteCrawler
from ai.test_generator import TestGenerator
from execution.test_runner import TestRunner
from storage.database import DatabaseManager

class CrawlerWorker(QThread):
    """Background worker for web crawling operations"""
    
    progress_updated = pyqtSignal(int, str)
    crawl_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, crawler_config, sf_config):
        super().__init__()
        self.crawler_config = crawler_config
        self.sf_config = sf_config
        self.crawler = None
        
    def run(self):
        """Run the crawling operation"""
        try:
            self.crawler = SiteCrawler(self.crawler_config)
            
            # Setup progress callback
            def progress_callback(current, total, message):
                progress = int((current / total) * 100) if total > 0 else 0
                self.progress_updated.emit(progress, message)
            
            # Start crawling
            self.progress_updated.emit(0, "Initializing crawler...")
            results = self.crawler.crawl_salesforce_site(
                self.sf_config, 
                progress_callback=progress_callback
            )
            
            self.crawl_completed.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            if self.crawler:
                self.crawler.close()

class TestGenerationWorker(QThread):
    """Background worker for AI test generation"""
    
    progress_updated = pyqtSignal(int, str)
    generation_completed = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, test_generator, page_data, requirements):
        super().__init__()
        self.test_generator = test_generator
        self.page_data = page_data
        self.requirements = requirements
        
    def run(self):
        """Run test generation"""
        try:
            self.progress_updated.emit(0, "Analyzing page structure...")
            
            generated_tests = []
            total_pages = len(self.page_data)
            
            for i, page in enumerate(self.page_data):
                self.progress_updated.emit(
                    int((i / total_pages) * 100), 
                    f"Generating tests for {page.get('title', 'Unknown Page')}..."
                )
                
                tests = self.test_generator.generate_tests_for_page(
                    page, self.requirements
                )
                generated_tests.extend(tests)
            
            self.progress_updated.emit(100, "Test generation completed")
            self.generation_completed.emit(generated_tests)
            
        except Exception as e:
            self.error_occurred.emit(str(e))

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, settings, db_manager: DatabaseManager):
        super().__init__()
        self.settings = settings
        self.db_manager = db_manager
        self.test_generator = None
        self.test_runner = None
        
        # Background workers
        self.crawler_worker = None
        self.test_gen_worker = None
        
        self.setup_ui()
        self.load_test_cases()
        
        # Initialize AI components
        self.initialize_ai_components()
        
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("AI-Driven Test Automation Tool")
        self.setGeometry(100, 100, self.settings.WINDOW_WIDTH, self.settings.WINDOW_HEIGHT)
        
        # Create menu bar and toolbar
        self.create_menu_bar()
        self.create_toolbar()
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QVBoxLayout(main_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_test_cases_tab()
        self.create_crawler_tab()
        self.create_results_tab()
        self.create_logs_tab()
        
        # Create status bar
        self.create_status_bar()
        
    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_test_action = QAction("New Test Case", self)
        new_test_action.setShortcut("Ctrl+N")
        new_test_action.triggered.connect(self.new_test_case)
        file_menu.addAction(new_test_action)
        
        import_action = QAction("Import Tests", self)
        import_action.triggered.connect(self.import_tests)
        file_menu.addAction(import_action)
        
        export_action = QAction("Export Tests", self)
        export_action.triggered.connect(self.export_tests)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        crawl_action = QAction("Crawl Site", self)
        crawl_action.triggered.connect(self.start_crawling)
        tools_menu.addAction(crawl_action)
        
        generate_action = QAction("Generate Tests", self)
        generate_action.triggered.connect(self.generate_tests)
        tools_menu.addAction(generate_action)
        
        run_tests_action = QAction("Run Tests", self)
        run_tests_action.triggered.connect(self.run_tests)
        tools_menu.addAction(run_tests_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_toolbar(self):
        """Create application toolbar"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Add test case button
        add_test_btn = QPushButton("New Test")
        add_test_btn.clicked.connect(self.new_test_case)
        toolbar.addWidget(add_test_btn)
        
        toolbar.addSeparator()
        
        # Crawl button
        crawl_btn = QPushButton("Crawl Site")
        crawl_btn.clicked.connect(self.start_crawling)
        toolbar.addWidget(crawl_btn)
        
        # Generate tests button
        generate_btn = QPushButton("Generate Tests")
        generate_btn.clicked.connect(self.generate_tests)
        toolbar.addWidget(generate_btn)
        
        toolbar.addSeparator()
        
        # Run tests button
        run_btn = QPushButton("Run Tests")
        run_btn.clicked.connect(self.run_tests)
        toolbar.addWidget(run_btn)
        
    def create_test_cases_tab(self):
        """Create test cases management tab"""
        test_cases_widget = QWidget()
        layout = QVBoxLayout(test_cases_widget)
        
        # Buttons row
        buttons_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Test Case")
        add_btn.clicked.connect(self.new_test_case)
        buttons_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit Selected")
        edit_btn.clicked.connect(self.edit_test_case)
        buttons_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self.delete_test_case)
        buttons_layout.addWidget(delete_btn)
        
        buttons_layout.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_test_cases)
        buttons_layout.addWidget(refresh_btn)
        
        layout.addLayout(buttons_layout)
        
        # Test cases table
        self.test_cases_table = QTableWidget()
        self.test_cases_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.test_cases_table.setAlternatingRowColors(True)
        self.test_cases_table.doubleClicked.connect(self.edit_test_case)
        
        # Set table headers
        headers = ["ID", "Title", "Type", "Priority", "Status", "Created", "Last Modified"]
        self.test_cases_table.setColumnCount(len(headers))
        self.test_cases_table.setHorizontalHeaderLabels(headers)
        
        # Configure table
        header = self.test_cases_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title column
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.test_cases_table)
        
        self.tab_widget.addTab(test_cases_widget, "Test Cases")
        
    def create_crawler_tab(self):
        """Create web crawler tab"""
        crawler_widget = QWidget()
        layout = QVBoxLayout(crawler_widget)
        
        # Crawler controls
        controls_group = QGroupBox("Crawler Controls")
        controls_layout = QVBoxLayout(controls_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        
        self.crawl_btn = QPushButton("Start Crawling")
        self.crawl_btn.clicked.connect(self.start_crawling)
        buttons_layout.addWidget(self.crawl_btn)
        
        self.stop_crawl_btn = QPushButton("Stop Crawling")
        self.stop_crawl_btn.clicked.connect(self.stop_crawling)
        self.stop_crawl_btn.setEnabled(False)
        buttons_layout.addWidget(self.stop_crawl_btn)
        
        config_btn = QPushButton("Configure")
        config_btn.clicked.connect(self.configure_crawler)
        buttons_layout.addWidget(config_btn)
        
        buttons_layout.addStretch()
        controls_layout.addLayout(buttons_layout)
        
        # Progress bar
        self.crawl_progress = QProgressBar()
        self.crawl_progress.setVisible(False)
        controls_layout.addWidget(self.crawl_progress)
        
        # Status label
        self.crawl_status = QLabel("Ready to crawl")
        controls_layout.addWidget(self.crawl_status)
        
        layout.addWidget(controls_group)
        
        # Crawled pages display
        pages_group = QGroupBox("Crawled Pages")
        pages_layout = QVBoxLayout(pages_group)
        
        self.crawled_pages_table = QTableWidget()
        self.crawled_pages_table.setColumnCount(4)
        self.crawled_pages_table.setHorizontalHeaderLabels(["URL", "Title", "Elements", "Status"])
        
        header = self.crawled_pages_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        pages_layout.addWidget(self.crawled_pages_table)
        layout.addWidget(pages_group)
        
        self.tab_widget.addTab(crawler_widget, "Site Crawler")
        
    def create_results_tab(self):
        """Create test results tab"""
        self.results_viewer = ResultsViewer(self.db_manager)
        self.tab_widget.addTab(self.results_viewer, "Test Results")
        
    def create_logs_tab(self):
        """Create logs display tab"""
        logs_widget = QWidget()
        layout = QVBoxLayout(logs_widget)
        
        # Log controls
        controls_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Clear Logs")
        clear_btn.clicked.connect(self.clear_logs)
        controls_layout.addWidget(clear_btn)
        
        refresh_logs_btn = QPushButton("Refresh")
        refresh_logs_btn.clicked.connect(self.refresh_logs)
        controls_layout.addWidget(refresh_logs_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Courier", 10))
        layout.addWidget(self.log_display)
        
        self.tab_widget.addTab(logs_widget, "Logs")
        
        # Setup log refresh timer
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.refresh_logs)
        self.log_timer.start(5000)  # Refresh every 5 seconds
        
    def create_status_bar(self):
        """Create application status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add status labels
        self.ai_status = QLabel("AI: Ready")
        self.db_status = QLabel("DB: Connected")
        self.crawler_status = QLabel("Crawler: Ready")
        
        self.status_bar.addWidget(self.ai_status)
        self.status_bar.addWidget(self.db_status)
        self.status_bar.addWidget(self.crawler_status)
        
        self.status_bar.showMessage("Ready")
        
    def initialize_ai_components(self):
        """Initialize AI components"""
        try:
            ai_config = self.settings.get_ai_config()
            self.test_generator = TestGenerator(ai_config, self.db_manager)
            self.ai_status.setText("AI: Ready")
            
            # Initialize test runner
            test_config = self.settings.get_test_config()
            self.test_runner = TestRunner(test_config, self.db_manager)
            
        except Exception as e:
            logging.error(f"Failed to initialize AI components: {e}")
            self.ai_status.setText("AI: Error")
            QMessageBox.warning(self, "AI Initialization", 
                              f"Failed to initialize AI components: {str(e)}")
    
    def load_test_cases(self):
        """Load test cases from database"""
        try:
            test_cases = self.db_manager.get_test_cases()
            
            self.test_cases_table.setRowCount(len(test_cases))
            
            for row, test_case in enumerate(test_cases):
                self.test_cases_table.setItem(row, 0, QTableWidgetItem(str(test_case['id'])))
                self.test_cases_table.setItem(row, 1, QTableWidgetItem(test_case['title']))
                self.test_cases_table.setItem(row, 2, QTableWidgetItem(test_case['type']))
                self.test_cases_table.setItem(row, 3, QTableWidgetItem(test_case['priority']))
                self.test_cases_table.setItem(row, 4, QTableWidgetItem(test_case['status']))
                self.test_cases_table.setItem(row, 5, QTableWidgetItem(test_case['created_at']))
                self.test_cases_table.setItem(row, 6, QTableWidgetItem(test_case['updated_at']))
                
        except Exception as e:
            logging.error(f"Failed to load test cases: {e}")
            QMessageBox.warning(self, "Database Error", 
                              f"Failed to load test cases: {str(e)}")
    
    def new_test_case(self):
        """Create a new test case"""
        dialog = TestCaseDialog(self)
        if dialog.exec() == TestCaseDialog.DialogCode.Accepted:
            test_case_data = dialog.get_test_case_data()
            try:
                self.db_manager.create_test_case(test_case_data)
                self.load_test_cases()
                self.status_bar.showMessage("Test case created successfully", 3000)
            except Exception as e:
                logging.error(f"Failed to create test case: {e}")
                QMessageBox.warning(self, "Database Error", 
                                  f"Failed to create test case: {str(e)}")
    
    def edit_test_case(self):
        """Edit selected test case"""
        current_row = self.test_cases_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "No Selection", "Please select a test case to edit")
            return
        
        test_case_id = int(self.test_cases_table.item(current_row, 0).text())
        
        try:
            test_case = self.db_manager.get_test_case(test_case_id)
            dialog = TestCaseDialog(self, test_case)
            
            if dialog.exec() == TestCaseDialog.DialogCode.Accepted:
                updated_data = dialog.get_test_case_data()
                updated_data['id'] = test_case_id
                self.db_manager.update_test_case(updated_data)
                self.load_test_cases()
                self.status_bar.showMessage("Test case updated successfully", 3000)
                
        except Exception as e:
            logging.error(f"Failed to edit test case: {e}")
            QMessageBox.warning(self, "Database Error", 
                              f"Failed to edit test case: {str(e)}")
    
    def delete_test_case(self):
        """Delete selected test case"""
        current_row = self.test_cases_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "No Selection", "Please select a test case to delete")
            return
        
        test_case_id = int(self.test_cases_table.item(current_row, 0).text())
        test_case_title = self.test_cases_table.item(current_row, 1).text()
        
        result = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete test case '{test_case_title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            try:
                self.db_manager.delete_test_case(test_case_id)
                self.load_test_cases()
                self.status_bar.showMessage("Test case deleted successfully", 3000)
            except Exception as e:
                logging.error(f"Failed to delete test case: {e}")
                QMessageBox.warning(self, "Database Error", 
                                  f"Failed to delete test case: {str(e)}")
    
    def start_crawling(self):
        """Start web crawling operation"""
        if not self.validate_salesforce_config():
            return
            
        # Show crawler configuration dialog
        dialog = CrawlerDialog(self, self.settings)
        if dialog.exec() != CrawlerDialog.DialogCode.Accepted:
            return
        
        crawler_config = dialog.get_crawler_config()
        sf_config = self.settings.get_salesforce_config()
        
        # Start crawler worker
        self.crawler_worker = CrawlerWorker(crawler_config, sf_config)
        self.crawler_worker.progress_updated.connect(self.update_crawl_progress)
        self.crawler_worker.crawl_completed.connect(self.crawl_completed)
        self.crawler_worker.error_occurred.connect(self.crawl_error)
        
        self.crawler_worker.start()
        
        # Update UI
        self.crawl_btn.setEnabled(False)
        self.stop_crawl_btn.setEnabled(True)
        self.crawl_progress.setVisible(True)
        self.crawl_progress.setValue(0)
        self.crawl_status.setText("Starting crawl...")
        
    def stop_crawling(self):
        """Stop crawling operation"""
        if self.crawler_worker and self.crawler_worker.isRunning():
            self.crawler_worker.terminate()
            self.crawler_worker.wait()
        
        self.crawl_btn.setEnabled(True)
        self.stop_crawl_btn.setEnabled(False)
        self.crawl_progress.setVisible(False)
        self.crawl_status.setText("Crawl stopped")
        
    def update_crawl_progress(self, progress: int, message: str):
        """Update crawling progress"""
        self.crawl_progress.setValue(progress)
        self.crawl_status.setText(message)
        
    def crawl_completed(self, results: dict):
        """Handle crawl completion"""
        self.crawl_btn.setEnabled(True)
        self.stop_crawl_btn.setEnabled(False)
        self.crawl_progress.setVisible(False)
        
        pages = results.get('pages', [])
        self.crawl_status.setText(f"Crawl completed. Found {len(pages)} pages.")
        
        # Update crawled pages table
        self.update_crawled_pages_table(pages)
        
        # Store crawl results
        try:
            self.db_manager.store_crawl_results(results)
        except Exception as e:
            logging.error(f"Failed to store crawl results: {e}")
        
        self.status_bar.showMessage(f"Crawl completed. {len(pages)} pages found.", 5000)
        
    def crawl_error(self, error_message: str):
        """Handle crawl error"""
        self.crawl_btn.setEnabled(True)
        self.stop_crawl_btn.setEnabled(False)
        self.crawl_progress.setVisible(False)
        self.crawl_status.setText(f"Crawl failed: {error_message}")
        
        QMessageBox.warning(self, "Crawl Error", f"Crawling failed: {error_message}")
        
    def update_crawled_pages_table(self, pages: list):
        """Update the crawled pages table"""
        self.crawled_pages_table.setRowCount(len(pages))
        
        for row, page in enumerate(pages):
            self.crawled_pages_table.setItem(row, 0, QTableWidgetItem(page.get('url', '')))
            self.crawled_pages_table.setItem(row, 1, QTableWidgetItem(page.get('title', '')))
            self.crawled_pages_table.setItem(row, 2, QTableWidgetItem(str(len(page.get('elements', [])))))
            self.crawled_pages_table.setItem(row, 3, QTableWidgetItem('Crawled'))
    
    def configure_crawler(self):
        """Configure crawler settings"""
        dialog = CrawlerDialog(self, self.settings)
        dialog.exec()
        
    def generate_tests(self):
        """Generate tests using AI"""
        if not self.test_generator:
            QMessageBox.warning(self, "AI Not Ready", "AI test generator is not initialized")
            return
            
        # Get crawled pages
        try:
            crawl_results = self.db_manager.get_latest_crawl_results()
            if not crawl_results or not crawl_results.get('pages'):
                QMessageBox.information(self, "No Data", 
                                      "No crawled pages found. Please crawl the site first.")
                return
                
            # Start test generation worker
            requirements = "Generate comprehensive test cases covering all UI elements and user interactions"
            
            self.test_gen_worker = TestGenerationWorker(
                self.test_generator, 
                crawl_results['pages'], 
                requirements
            )
            self.test_gen_worker.progress_updated.connect(self.update_generation_progress)
            self.test_gen_worker.generation_completed.connect(self.generation_completed)
            self.test_gen_worker.error_occurred.connect(self.generation_error)
            
            self.test_gen_worker.start()
            
            self.status_bar.showMessage("Generating tests...")
            
        except Exception as e:
            logging.error(f"Failed to start test generation: {e}")
            QMessageBox.warning(self, "Generation Error", 
                              f"Failed to start test generation: {str(e)}")
    
    def update_generation_progress(self, progress: int, message: str):
        """Update test generation progress"""
        self.status_bar.showMessage(f"{message} ({progress}%)")
        
    def generation_completed(self, generated_tests: list):
        """Handle test generation completion"""
        try:
            # Store generated tests
            for test in generated_tests:
                test['type'] = 'AI-Generated'
                test['status'] = 'Draft'
                self.db_manager.create_test_case(test)
            
            self.load_test_cases()
            self.status_bar.showMessage(f"Generated {len(generated_tests)} test cases", 5000)
            
            QMessageBox.information(self, "Generation Complete", 
                                  f"Successfully generated {len(generated_tests)} test cases")
            
        except Exception as e:
            logging.error(f"Failed to store generated tests: {e}")
            QMessageBox.warning(self, "Storage Error", 
                              f"Failed to store generated tests: {str(e)}")
    
    def generation_error(self, error_message: str):
        """Handle test generation error"""
        self.status_bar.showMessage("Test generation failed")
        QMessageBox.warning(self, "Generation Error", f"Test generation failed: {error_message}")
        
    def run_tests(self):
        """Run selected or all test cases"""
        if not self.test_runner:
            QMessageBox.warning(self, "Test Runner Not Ready", "Test runner is not initialized")
            return
            
        # Get selected test cases or all if none selected
        selected_rows = self.test_cases_table.selectionModel().selectedRows()
        
        if selected_rows:
            test_ids = []
            for row in selected_rows:
                test_id = int(self.test_cases_table.item(row.row(), 0).text())
                test_ids.append(test_id)
        else:
            # Run all test cases
            result = QMessageBox.question(
                self, "Run All Tests",
                "No tests selected. Run all test cases?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if result != QMessageBox.StandardButton.Yes:
                return
                
            test_ids = None
        
        try:
            # Run tests in background
            self.test_runner.run_tests_async(test_ids, self.test_execution_completed)
            self.status_bar.showMessage("Running tests...")
            
        except Exception as e:
            logging.error(f"Failed to run tests: {e}")
            QMessageBox.warning(self, "Execution Error", f"Failed to run tests: {str(e)}")
    
    def test_execution_completed(self, results: dict):
        """Handle test execution completion"""
        self.status_bar.showMessage(f"Test execution completed. {results.get('passed', 0)} passed, "
                                   f"{results.get('failed', 0)} failed", 5000)
        
        # Refresh results tab
        self.results_viewer.refresh_results()
        
        # Switch to results tab
        self.tab_widget.setCurrentWidget(self.results_viewer)
    
    def import_tests(self):
        """Import test cases from file"""
        # TODO: Implement test import functionality
        QMessageBox.information(self, "Feature Coming Soon", "Test import feature will be implemented")
    
    def export_tests(self):
        """Export test cases to file"""
        # TODO: Implement test export functionality
        QMessageBox.information(self, "Feature Coming Soon", "Test export feature will be implemented")
    
    def validate_salesforce_config(self) -> bool:
        """Validate Salesforce configuration"""
        errors = self.settings.validate_required_settings()
        if errors:
            error_msg = "Missing required configuration:\n"
            for field, message in errors.items():
                error_msg += f"- {message}\n"
            
            QMessageBox.warning(self, "Configuration Error", error_msg)
            return False
        return True
    
    def clear_logs(self):
        """Clear log display"""
        self.log_display.clear()
        
    def refresh_logs(self):
        """Refresh log display"""
        try:
            if self.settings.LOG_FILE.exists():
                with open(self.settings.LOG_FILE, 'r', encoding='utf-8') as f:
                    # Read last 1000 lines
                    lines = f.readlines()
                    if len(lines) > 1000:
                        lines = lines[-1000:]
                    
                    log_content = ''.join(lines)
                    
                    # Only update if content changed
                    current_content = self.log_display.toPlainText()
                    if log_content != current_content:
                        # Save current scroll position
                        scrollbar = self.log_display.verticalScrollBar()
                        at_bottom = scrollbar.value() == scrollbar.maximum()
                        
                        self.log_display.setPlainText(log_content)
                        
                        # Restore scroll position
                        if at_bottom:
                            scrollbar.setValue(scrollbar.maximum())
                            
        except Exception as e:
            logging.warning(f"Failed to refresh logs: {e}")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About AI Test Automation Tool",
                         "AI-Driven Test Automation Tool v1.0.0\n\n"
                         "An intelligent desktop application for automated test case "
                         "generation and execution on Salesforce Experience Cloud.\n\n"
                         "Features:\n"
                         "• AI-powered test generation\n"
                         "• Web crawling and DOM analysis\n"
                         "• Automated test execution\n"
                         "• Comprehensive reporting\n"
                         "• Offline and cloud LLM support")
