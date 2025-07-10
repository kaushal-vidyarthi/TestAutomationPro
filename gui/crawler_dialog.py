"""
Dialog for configuring web crawler settings
"""

from typing import Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTextEdit,
    QComboBox, QLabel, QFormLayout, QDialogButtonBox, QTabWidget, QWidget,
    QSpinBox, QCheckBox, QGroupBox, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt

class CrawlerDialog(QDialog):
    """Dialog for configuring web crawler settings"""
    
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.settings = settings
        
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("Crawler Configuration")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_basic_settings_tab()
        self.create_authentication_tab()
        self.create_crawling_options_tab()
        self.create_advanced_settings_tab()
        
        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
    def create_basic_settings_tab(self):
        """Create basic settings tab"""
        basic_widget = QWidget()
        layout = QFormLayout(basic_widget)
        
        # Starting URL
        self.start_url_edit = QLineEdit()
        self.start_url_edit.setPlaceholderText("https://your-experience-cloud.force.com")
        layout.addRow("Starting URL:", self.start_url_edit)
        
        # Timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)
        self.timeout_spin.setValue(30)
        self.timeout_spin.setSuffix(" seconds")
        layout.addRow("Page Timeout:", self.timeout_spin)
        
        # Max pages
        self.max_pages_spin = QSpinBox()
        self.max_pages_spin.setRange(1, 1000)
        self.max_pages_spin.setValue(50)
        layout.addRow("Max Pages:", self.max_pages_spin)
        
        # Crawl depth
        self.max_depth_spin = QSpinBox()
        self.max_depth_spin.setRange(1, 10)
        self.max_depth_spin.setValue(3)
        layout.addRow("Max Depth:", self.max_depth_spin)
        
        # Wait between requests
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 10)
        self.delay_spin.setValue(1)
        self.delay_spin.setSuffix(" seconds")
        layout.addRow("Delay Between Requests:", self.delay_spin)
        
        # Headless mode
        self.headless_check = QCheckBox("Run in headless mode")
        self.headless_check.setChecked(True)
        layout.addRow("", self.headless_check)
        
        # Take screenshots
        self.screenshots_check = QCheckBox("Take page screenshots")
        self.screenshots_check.setChecked(True)
        layout.addRow("", self.screenshots_check)
        
        self.tab_widget.addTab(basic_widget, "Basic Settings")
        
    def create_authentication_tab(self):
        """Create authentication tab"""
        auth_widget = QWidget()
        layout = QFormLayout(auth_widget)
        
        # Salesforce login URL
        self.login_url_edit = QLineEdit()
        self.login_url_edit.setPlaceholderText("https://login.salesforce.com")
        layout.addRow("Login URL:", self.login_url_edit)
        
        # Username
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("your-username@company.com")
        layout.addRow("Username:", self.username_edit)
        
        # Password
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Your password")
        layout.addRow("Password:", self.password_edit)
        
        # Security token
        self.security_token_edit = QLineEdit()
        self.security_token_edit.setPlaceholderText("Security token (if required)")
        layout.addRow("Security Token:", self.security_token_edit)
        
        # Domain type
        self.domain_combo = QComboBox()
        self.domain_combo.addItems(["login", "test"])
        layout.addRow("Domain:", self.domain_combo)
        
        # Test connection button
        test_conn_btn = QPushButton("Test Connection")
        test_conn_btn.clicked.connect(self.test_connection)
        layout.addRow("", test_conn_btn)
        
        self.tab_widget.addTab(auth_widget, "Authentication")
        
    def create_crawling_options_tab(self):
        """Create crawling options tab"""
        options_widget = QWidget()
        layout = QVBoxLayout(options_widget)
        
        # Include/exclude patterns
        patterns_group = QGroupBox("URL Patterns")
        patterns_layout = QVBoxLayout(patterns_group)
        
        # Include patterns
        include_label = QLabel("Include URL patterns (one per line):")
        patterns_layout.addWidget(include_label)
        
        self.include_patterns_edit = QTextEdit()
        self.include_patterns_edit.setPlaceholderText(
            "Example:\n/s/\n/apex/\n/lightning/"
        )
        self.include_patterns_edit.setMaximumHeight(80)
        patterns_layout.addWidget(self.include_patterns_edit)
        
        # Exclude patterns
        exclude_label = QLabel("Exclude URL patterns (one per line):")
        patterns_layout.addWidget(exclude_label)
        
        self.exclude_patterns_edit = QTextEdit()
        self.exclude_patterns_edit.setPlaceholderText(
            "Example:\n/setup/\n/admin/\n*.pdf\n*.zip"
        )
        self.exclude_patterns_edit.setMaximumHeight(80)
        patterns_layout.addWidget(self.exclude_patterns_edit)
        
        layout.addWidget(patterns_group)
        
        # Element extraction options
        extraction_group = QGroupBox("Element Extraction")
        extraction_layout = QVBoxLayout(extraction_group)
        
        self.extract_forms_check = QCheckBox("Extract forms and form fields")
        self.extract_forms_check.setChecked(True)
        extraction_layout.addWidget(self.extract_forms_check)
        
        self.extract_buttons_check = QCheckBox("Extract buttons and links")
        self.extract_buttons_check.setChecked(True)
        extraction_layout.addWidget(self.extract_buttons_check)
        
        self.extract_inputs_check = QCheckBox("Extract input fields")
        self.extract_inputs_check.setChecked(True)
        extraction_layout.addWidget(self.extract_inputs_check)
        
        self.extract_tables_check = QCheckBox("Extract tables")
        self.extract_tables_check.setChecked(True)
        extraction_layout.addWidget(self.extract_tables_check)
        
        self.extract_navigation_check = QCheckBox("Extract navigation elements")
        self.extract_navigation_check.setChecked(True)
        extraction_layout.addWidget(self.extract_navigation_check)
        
        layout.addWidget(extraction_group)
        
        self.tab_widget.addTab(options_widget, "Crawling Options")
        
    def create_advanced_settings_tab(self):
        """Create advanced settings tab"""
        advanced_widget = QWidget()
        layout = QFormLayout(advanced_widget)
        
        # Browser type
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["chromium", "firefox", "webkit"])
        layout.addRow("Browser Engine:", self.browser_combo)
        
        # User agent
        self.user_agent_edit = QLineEdit()
        self.user_agent_edit.setPlaceholderText("Custom user agent (optional)")
        layout.addRow("User Agent:", self.user_agent_edit)
        
        # Viewport size
        viewport_layout = QHBoxLayout()
        
        self.viewport_width_spin = QSpinBox()
        self.viewport_width_spin.setRange(320, 3840)
        self.viewport_width_spin.setValue(1920)
        viewport_layout.addWidget(self.viewport_width_spin)
        
        viewport_layout.addWidget(QLabel("x"))
        
        self.viewport_height_spin = QSpinBox()
        self.viewport_height_spin.setRange(240, 2160)
        self.viewport_height_spin.setValue(1080)
        viewport_layout.addWidget(self.viewport_height_spin)
        
        viewport_layout.addStretch()
        layout.addRow("Viewport Size:", viewport_layout)
        
        # JavaScript execution
        self.javascript_check = QCheckBox("Enable JavaScript")
        self.javascript_check.setChecked(True)
        layout.addRow("", self.javascript_check)
        
        # Load images
        self.load_images_check = QCheckBox("Load images")
        self.load_images_check.setChecked(False)
        layout.addRow("", self.load_images_check)
        
        # Parallel requests
        self.parallel_spin = QSpinBox()
        self.parallel_spin.setRange(1, 10)
        self.parallel_spin.setValue(3)
        layout.addRow("Parallel Requests:", self.parallel_spin)
        
        # Retry attempts
        self.retry_spin = QSpinBox()
        self.retry_spin.setRange(0, 5)
        self.retry_spin.setValue(2)
        layout.addRow("Retry Attempts:", self.retry_spin)
        
        # Output directory
        output_layout = QHBoxLayout()
        
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Output directory for crawl results")
        output_layout.addWidget(self.output_dir_edit)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(browse_btn)
        
        layout.addRow("Output Directory:", output_layout)
        
        self.tab_widget.addTab(advanced_widget, "Advanced")
        
    def load_settings(self):
        """Load settings from configuration"""
        if not self.settings:
            return
            
        # Basic settings
        crawler_config = self.settings.get_crawler_config()
        self.timeout_spin.setValue(crawler_config.get('timeout', 30))
        self.max_pages_spin.setValue(crawler_config.get('max_pages', 50))
        self.headless_check.setChecked(crawler_config.get('headless', True))
        
        # Authentication
        sf_config = self.settings.get_salesforce_config()
        self.login_url_edit.setText(sf_config.get('login_url', ''))
        self.username_edit.setText(sf_config.get('username', ''))
        self.password_edit.setText(sf_config.get('password', ''))
        self.security_token_edit.setText(sf_config.get('security_token', ''))
        
        domain = sf_config.get('domain', 'login')
        domain_index = self.domain_combo.findText(domain)
        if domain_index >= 0:
            self.domain_combo.setCurrentIndex(domain_index)
            
        # Advanced settings
        viewport = crawler_config.get('viewport', {})
        self.viewport_width_spin.setValue(viewport.get('width', 1920))
        self.viewport_height_spin.setValue(viewport.get('height', 1080))
        
    def test_connection(self):
        """Test Salesforce connection"""
        # Basic validation
        if not self.username_edit.text().strip():
            QMessageBox.warning(self, "Missing Information", "Username is required")
            return
            
        if not self.password_edit.text().strip():
            QMessageBox.warning(self, "Missing Information", "Password is required")
            return
            
        QMessageBox.information(self, "Test Connection", 
                              "Connection test will be implemented. "
                              "For now, please verify your credentials manually.")
    
    def browse_output_dir(self):
        """Browse for output directory"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.output_dir_edit.text()
        )
        if directory:
            self.output_dir_edit.setText(directory)
            
    def get_crawler_config(self) -> Dict[str, Any]:
        """Get crawler configuration from form"""
        # Parse include/exclude patterns
        include_patterns = [
            line.strip() for line in self.include_patterns_edit.toPlainText().split('\n')
            if line.strip()
        ]
        exclude_patterns = [
            line.strip() for line in self.exclude_patterns_edit.toPlainText().split('\n')
            if line.strip()
        ]
        
        return {
            # Basic settings
            'start_url': self.start_url_edit.text().strip(),
            'timeout': self.timeout_spin.value(),
            'max_pages': self.max_pages_spin.value(),
            'max_depth': self.max_depth_spin.value(),
            'delay': self.delay_spin.value(),
            'headless': self.headless_check.isChecked(),
            'take_screenshots': self.screenshots_check.isChecked(),
            
            # Authentication
            'login_url': self.login_url_edit.text().strip(),
            'username': self.username_edit.text().strip(),
            'password': self.password_edit.text().strip(),
            'security_token': self.security_token_edit.text().strip(),
            'domain': self.domain_combo.currentText(),
            
            # Crawling options
            'include_patterns': include_patterns,
            'exclude_patterns': exclude_patterns,
            'extract_forms': self.extract_forms_check.isChecked(),
            'extract_buttons': self.extract_buttons_check.isChecked(),
            'extract_inputs': self.extract_inputs_check.isChecked(),
            'extract_tables': self.extract_tables_check.isChecked(),
            'extract_navigation': self.extract_navigation_check.isChecked(),
            
            # Advanced settings
            'browser': self.browser_combo.currentText(),
            'user_agent': self.user_agent_edit.text().strip(),
            'viewport': {
                'width': self.viewport_width_spin.value(),
                'height': self.viewport_height_spin.value()
            },
            'javascript_enabled': self.javascript_check.isChecked(),
            'load_images': self.load_images_check.isChecked(),
            'parallel_requests': self.parallel_spin.value(),
            'retry_attempts': self.retry_spin.value(),
            'output_directory': self.output_dir_edit.text().strip()
        }
