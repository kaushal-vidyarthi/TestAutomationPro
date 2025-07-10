"""
Widget for viewing test execution results
"""

import logging
from typing import Dict, Any, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QTextEdit, QSplitter, QGroupBox, QLabel,
    QComboBox, QDateEdit, QHeaderView, QAbstractItemView, QMessageBox,
    QProgressBar, QTabWidget
)
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtGui import QFont, QColor, QBrush

from storage.database import DatabaseManager

class ResultsViewer(QWidget):
    """Widget for viewing and analyzing test execution results"""
    
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        
        self.setup_ui()
        self.load_results()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_results)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Create controls
        self.create_controls()
        layout.addWidget(self.controls_group)
        
        # Create splitter for results and details
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)
        
        # Create results table
        self.create_results_table()
        splitter.addWidget(self.results_group)
        
        # Create details tabs
        self.create_details_tabs()
        splitter.addWidget(self.details_tabs)
        
        # Set splitter proportions
        splitter.setSizes([400, 300])
        
    def create_controls(self):
        """Create control widgets"""
        self.controls_group = QGroupBox("Filters and Controls")
        layout = QHBoxLayout(self.controls_group)
        
        # Status filter
        layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Passed", "Failed", "Running", "Pending"])
        self.status_filter.currentTextChanged.connect(self.filter_results)
        layout.addWidget(self.status_filter)
        
        # Date filter
        layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_from.dateChanged.connect(self.filter_results)
        layout.addWidget(self.date_from)
        
        layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(self.filter_results)
        layout.addWidget(self.date_to)
        
        layout.addStretch()
        
        # Control buttons
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_results)
        layout.addWidget(refresh_btn)
        
        clear_btn = QPushButton("Clear Old Results")
        clear_btn.clicked.connect(self.clear_old_results)
        layout.addWidget(clear_btn)
        
        export_btn = QPushButton("Export Report")
        export_btn.clicked.connect(self.export_report)
        layout.addWidget(export_btn)
        
    def create_results_table(self):
        """Create results table"""
        self.results_group = QGroupBox("Test Results")
        layout = QVBoxLayout(self.results_group)
        
        # Summary info
        self.summary_layout = QHBoxLayout()
        
        self.total_label = QLabel("Total: 0")
        self.summary_layout.addWidget(self.total_label)
        
        self.passed_label = QLabel("Passed: 0")
        self.passed_label.setStyleSheet("color: green; font-weight: bold;")
        self.summary_layout.addWidget(self.passed_label)
        
        self.failed_label = QLabel("Failed: 0")
        self.failed_label.setStyleSheet("color: red; font-weight: bold;")
        self.summary_layout.addWidget(self.failed_label)
        
        self.running_label = QLabel("Running: 0")
        self.running_label.setStyleSheet("color: blue; font-weight: bold;")
        self.summary_layout.addWidget(self.running_label)
        
        self.summary_layout.addStretch()
        
        # Pass rate progress bar
        self.pass_rate_label = QLabel("Pass Rate:")
        self.summary_layout.addWidget(self.pass_rate_label)
        
        self.pass_rate_bar = QProgressBar()
        self.pass_rate_bar.setMaximumWidth(200)
        self.summary_layout.addWidget(self.pass_rate_bar)
        
        layout.addLayout(self.summary_layout)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.itemSelectionChanged.connect(self.on_result_selected)
        
        # Set table headers
        headers = [
            "ID", "Test Case", "Status", "Duration", "Start Time", 
            "End Time", "Error Message", "Browser", "Environment"
        ]
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        
        # Configure table
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Test Case column
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # Error Message column
        
        layout.addWidget(self.results_table)
        
    def create_details_tabs(self):
        """Create details tabs"""
        self.details_tabs = QTabWidget()
        
        # Execution details tab
        self.create_execution_details_tab()
        
        # Logs tab
        self.create_logs_tab()
        
        # Screenshots tab
        self.create_screenshots_tab()
        
        # Performance tab
        self.create_performance_tab()
        
    def create_execution_details_tab(self):
        """Create execution details tab"""
        details_widget = QWidget()
        layout = QVBoxLayout(details_widget)
        
        # Test case info
        info_group = QGroupBox("Test Case Information")
        info_layout = QVBoxLayout(info_group)
        
        self.test_info_text = QTextEdit()
        self.test_info_text.setReadOnly(True)
        self.test_info_text.setMaximumHeight(100)
        info_layout.addWidget(self.test_info_text)
        
        layout.addWidget(info_group)
        
        # Steps execution
        steps_group = QGroupBox("Step Execution Details")
        steps_layout = QVBoxLayout(steps_group)
        
        self.steps_table = QTableWidget()
        self.steps_table.setColumnCount(4)
        self.steps_table.setHorizontalHeaderLabels(["Step", "Status", "Duration", "Notes"])
        
        header = self.steps_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        steps_layout.addWidget(self.steps_table)
        layout.addWidget(steps_group)
        
        self.details_tabs.addTab(details_widget, "Execution Details")
        
    def create_logs_tab(self):
        """Create logs tab"""
        logs_widget = QWidget()
        layout = QVBoxLayout(logs_widget)
        
        # Log level filter
        log_controls = QHBoxLayout()
        
        log_controls.addWidget(QLabel("Log Level:"))
        self.log_level_filter = QComboBox()
        self.log_level_filter.addItems(["All", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_filter.currentTextChanged.connect(self.filter_logs)
        log_controls.addWidget(self.log_level_filter)
        
        log_controls.addStretch()
        
        clear_logs_btn = QPushButton("Clear")
        clear_logs_btn.clicked.connect(self.clear_log_display)
        log_controls.addWidget(clear_logs_btn)
        
        layout.addLayout(log_controls)
        
        # Log display
        self.logs_display = QTextEdit()
        self.logs_display.setReadOnly(True)
        self.logs_display.setFont(QFont("Courier", 10))
        layout.addWidget(self.logs_display)
        
        self.details_tabs.addTab(logs_widget, "Logs")
        
    def create_screenshots_tab(self):
        """Create screenshots tab"""
        screenshots_widget = QWidget()
        layout = QVBoxLayout(screenshots_widget)
        
        # Screenshot controls
        screenshot_controls = QHBoxLayout()
        
        screenshot_controls.addWidget(QLabel("Screenshot:"))
        self.screenshot_combo = QComboBox()
        self.screenshot_combo.currentTextChanged.connect(self.show_screenshot)
        screenshot_controls.addWidget(self.screenshot_combo)
        
        screenshot_controls.addStretch()
        
        save_screenshot_btn = QPushButton("Save Screenshot")
        save_screenshot_btn.clicked.connect(self.save_screenshot)
        screenshot_controls.addWidget(save_screenshot_btn)
        
        layout.addLayout(screenshot_controls)
        
        # Screenshot display
        self.screenshot_label = QLabel("No screenshot available")
        self.screenshot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screenshot_label.setStyleSheet("border: 1px solid gray; min-height: 200px;")
        layout.addWidget(self.screenshot_label)
        
        self.details_tabs.addTab(screenshots_widget, "Screenshots")
        
    def create_performance_tab(self):
        """Create performance tab"""
        performance_widget = QWidget()
        layout = QVBoxLayout(performance_widget)
        
        # Performance metrics
        metrics_group = QGroupBox("Performance Metrics")
        metrics_layout = QVBoxLayout(metrics_group)
        
        self.performance_text = QTextEdit()
        self.performance_text.setReadOnly(True)
        self.performance_text.setMaximumHeight(150)
        metrics_layout.addWidget(self.performance_text)
        
        layout.addWidget(metrics_group)
        
        # Timing breakdown
        timing_group = QGroupBox("Timing Breakdown")
        timing_layout = QVBoxLayout(timing_group)
        
        self.timing_table = QTableWidget()
        self.timing_table.setColumnCount(3)
        self.timing_table.setHorizontalHeaderLabels(["Action", "Duration (ms)", "Percentage"])
        
        header = self.timing_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        timing_layout.addWidget(self.timing_table)
        layout.addWidget(timing_group)
        
        self.details_tabs.addTab(performance_widget, "Performance")
        
    def load_results(self):
        """Load test results from database"""
        try:
            results = self.db_manager.get_test_results()
            self.populate_results_table(results)
            self.update_summary(results)
            
        except Exception as e:
            logging.error(f"Failed to load test results: {e}")
            QMessageBox.warning(self, "Database Error", 
                              f"Failed to load test results: {str(e)}")
    
    def populate_results_table(self, results: List[Dict[str, Any]]):
        """Populate the results table"""
        self.results_table.setRowCount(len(results))
        
        for row, result in enumerate(results):
            # ID
            self.results_table.setItem(row, 0, QTableWidgetItem(str(result.get('id', ''))))
            
            # Test Case
            test_case_name = result.get('test_case_title', result.get('test_case_id', ''))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(test_case_name)))
            
            # Status
            status = result.get('status', 'Unknown')
            status_item = QTableWidgetItem(status)
            
            # Color code status
            if status == 'Passed':
                status_item.setBackground(QBrush(QColor(200, 255, 200)))
            elif status == 'Failed':
                status_item.setBackground(QBrush(QColor(255, 200, 200)))
            elif status == 'Running':
                status_item.setBackground(QBrush(QColor(200, 200, 255)))
            
            self.results_table.setItem(row, 2, status_item)
            
            # Duration
            duration = result.get('duration', 0)
            if duration:
                duration_text = f"{duration:.2f}s"
            else:
                duration_text = "-"
            self.results_table.setItem(row, 3, QTableWidgetItem(duration_text))
            
            # Start Time
            start_time = result.get('start_time', '')
            self.results_table.setItem(row, 4, QTableWidgetItem(str(start_time)))
            
            # End Time
            end_time = result.get('end_time', '')
            self.results_table.setItem(row, 5, QTableWidgetItem(str(end_time)))
            
            # Error Message
            error_msg = result.get('error_message', '')
            self.results_table.setItem(row, 6, QTableWidgetItem(str(error_msg)))
            
            # Browser
            browser = result.get('browser', '')
            self.results_table.setItem(row, 7, QTableWidgetItem(str(browser)))
            
            # Environment
            environment = result.get('environment', '')
            self.results_table.setItem(row, 8, QTableWidgetItem(str(environment)))
    
    def update_summary(self, results: List[Dict[str, Any]]):
        """Update summary statistics"""
        total = len(results)
        passed = sum(1 for r in results if r.get('status') == 'Passed')
        failed = sum(1 for r in results if r.get('status') == 'Failed')
        running = sum(1 for r in results if r.get('status') == 'Running')
        
        self.total_label.setText(f"Total: {total}")
        self.passed_label.setText(f"Passed: {passed}")
        self.failed_label.setText(f"Failed: {failed}")
        self.running_label.setText(f"Running: {running}")
        
        # Calculate pass rate
        if total > 0:
            completed = passed + failed
            if completed > 0:
                pass_rate = (passed / completed) * 100
                self.pass_rate_bar.setValue(int(pass_rate))
                self.pass_rate_label.setText(f"Pass Rate: {pass_rate:.1f}%")
            else:
                self.pass_rate_bar.setValue(0)
                self.pass_rate_label.setText("Pass Rate: N/A")
        else:
            self.pass_rate_bar.setValue(0)
            self.pass_rate_label.setText("Pass Rate: N/A")
    
    def filter_results(self):
        """Filter results based on current filters"""
        status_filter = self.status_filter.currentText()
        date_from = self.date_from.date().toPython()
        date_to = self.date_to.date().toPython()
        
        try:
            results = self.db_manager.get_test_results(
                status_filter=status_filter if status_filter != "All" else None,
                date_from=date_from,
                date_to=date_to
            )
            self.populate_results_table(results)
            self.update_summary(results)
            
        except Exception as e:
            logging.error(f"Failed to filter results: {e}")
    
    def on_result_selected(self):
        """Handle result selection"""
        current_row = self.results_table.currentRow()
        if current_row < 0:
            return
            
        result_id = self.results_table.item(current_row, 0).text()
        self.show_result_details(int(result_id))
    
    def show_result_details(self, result_id: int):
        """Show details for selected result"""
        try:
            result = self.db_manager.get_test_result_details(result_id)
            if not result:
                return
                
            # Update execution details
            self.update_execution_details(result)
            
            # Update logs
            self.update_logs(result)
            
            # Update screenshots
            self.update_screenshots(result)
            
            # Update performance
            self.update_performance(result)
            
        except Exception as e:
            logging.error(f"Failed to load result details: {e}")
    
    def update_execution_details(self, result: Dict[str, Any]):
        """Update execution details tab"""
        # Test case info
        info_text = f"""
Test Case: {result.get('test_case_title', 'N/A')}
Status: {result.get('status', 'N/A')}
Duration: {result.get('duration', 0):.2f}s
Browser: {result.get('browser', 'N/A')}
Environment: {result.get('environment', 'N/A')}
Start Time: {result.get('start_time', 'N/A')}
End Time: {result.get('end_time', 'N/A')}
        """.strip()
        
        self.test_info_text.setPlainText(info_text)
        
        # Step details
        steps = result.get('steps', [])
        self.steps_table.setRowCount(len(steps))
        
        for row, step in enumerate(steps):
            self.steps_table.setItem(row, 0, QTableWidgetItem(step.get('description', '')))
            
            status = step.get('status', 'Unknown')
            status_item = QTableWidgetItem(status)
            
            if status == 'Passed':
                status_item.setBackground(QBrush(QColor(200, 255, 200)))
            elif status == 'Failed':
                status_item.setBackground(QBrush(QColor(255, 200, 200)))
                
            self.steps_table.setItem(row, 1, status_item)
            
            duration = step.get('duration', 0)
            self.steps_table.setItem(row, 2, QTableWidgetItem(f"{duration:.2f}s"))
            
            notes = step.get('notes', '')
            self.steps_table.setItem(row, 3, QTableWidgetItem(notes))
    
    def update_logs(self, result: Dict[str, Any]):
        """Update logs tab"""
        logs = result.get('logs', [])
        log_text = "\n".join([
            f"[{log.get('timestamp', '')}] {log.get('level', 'INFO')}: {log.get('message', '')}"
            for log in logs
        ])
        self.logs_display.setPlainText(log_text)
    
    def update_screenshots(self, result: Dict[str, Any]):
        """Update screenshots tab"""
        screenshots = result.get('screenshots', [])
        
        self.screenshot_combo.clear()
        for screenshot in screenshots:
            self.screenshot_combo.addItem(screenshot.get('name', 'Screenshot'))
        
        if screenshots:
            self.show_screenshot()
        else:
            self.screenshot_label.setText("No screenshots available")
    
    def show_screenshot(self):
        """Show selected screenshot"""
        # TODO: Implement screenshot display
        self.screenshot_label.setText("Screenshot display will be implemented")
    
    def update_performance(self, result: Dict[str, Any]):
        """Update performance tab"""
        performance = result.get('performance', {})
        
        # Performance metrics
        metrics_text = f"""
Total Duration: {performance.get('total_duration', 0):.2f}s
Page Load Time: {performance.get('page_load_time', 0):.2f}s
Script Execution Time: {performance.get('script_time', 0):.2f}s
Network Time: {performance.get('network_time', 0):.2f}s
Memory Usage: {performance.get('memory_usage', 0):.2f} MB
CPU Usage: {performance.get('cpu_usage', 0):.1f}%
        """.strip()
        
        self.performance_text.setPlainText(metrics_text)
        
        # Timing breakdown
        timings = performance.get('timings', [])
        self.timing_table.setRowCount(len(timings))
        
        total_time = sum(timing.get('duration', 0) for timing in timings)
        
        for row, timing in enumerate(timings):
            self.timing_table.setItem(row, 0, QTableWidgetItem(timing.get('action', '')))
            
            duration = timing.get('duration', 0)
            self.timing_table.setItem(row, 1, QTableWidgetItem(f"{duration:.2f}"))
            
            if total_time > 0:
                percentage = (duration / total_time) * 100
                self.timing_table.setItem(row, 2, QTableWidgetItem(f"{percentage:.1f}%"))
            else:
                self.timing_table.setItem(row, 2, QTableWidgetItem("0%"))
    
    def filter_logs(self):
        """Filter logs by level"""
        # TODO: Implement log filtering
        pass
    
    def clear_log_display(self):
        """Clear log display"""
        self.logs_display.clear()
    
    def save_screenshot(self):
        """Save current screenshot"""
        # TODO: Implement screenshot saving
        QMessageBox.information(self, "Feature Coming Soon", 
                              "Screenshot saving will be implemented")
    
    def refresh_results(self):
        """Refresh results display"""
        self.load_results()
    
    def clear_old_results(self):
        """Clear old test results"""
        result = QMessageBox.question(
            self, "Clear Old Results",
            "This will delete test results older than 30 days. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            try:
                count = self.db_manager.cleanup_old_results(days=30)
                QMessageBox.information(self, "Cleanup Complete", 
                                      f"Deleted {count} old test results")
                self.refresh_results()
                
            except Exception as e:
                logging.error(f"Failed to clear old results: {e}")
                QMessageBox.warning(self, "Cleanup Error", 
                                  f"Failed to clear old results: {str(e)}")
    
    def export_report(self):
        """Export test results report"""
        # TODO: Implement report export
        QMessageBox.information(self, "Feature Coming Soon", 
                              "Report export will be implemented")
