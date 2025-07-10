"""
Dialog for creating and editing test cases
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTextEdit,
    QComboBox, QLabel, QFormLayout, QDialogButtonBox, QTabWidget, QWidget,
    QSpinBox, QCheckBox, QGroupBox, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class TestCaseDialog(QDialog):
    """Dialog for creating and editing test cases"""
    
    def __init__(self, parent=None, test_case: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.test_case = test_case
        self.is_editing = test_case is not None
        
        self.setup_ui()
        self.load_data()
        
    def setup_ui(self):
        """Setup the user interface"""
        title = "Edit Test Case" if self.is_editing else "New Test Case"
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_basic_info_tab()
        self.create_steps_tab()
        self.create_assertions_tab()
        self.create_metadata_tab()
        
        # Dialog buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
    def create_basic_info_tab(self):
        """Create basic information tab"""
        basic_widget = QWidget()
        layout = QFormLayout(basic_widget)
        
        # Title
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Enter test case title")
        layout.addRow("Title:", self.title_edit)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Enter test case description")
        self.description_edit.setMaximumHeight(100)
        layout.addRow("Description:", self.description_edit)
        
        # Type
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Functional", "UI", "Integration", "End-to-End", 
            "Regression", "Smoke", "AI-Generated"
        ])
        layout.addRow("Type:", self.type_combo)
        
        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Critical"])
        self.priority_combo.setCurrentText("Medium")
        layout.addRow("Priority:", self.priority_combo)
        
        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems([
            "Draft", "Ready", "In Progress", "Passed", "Failed", "Blocked"
        ])
        layout.addRow("Status:", self.status_combo)
        
        # Tags
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Enter tags separated by commas")
        layout.addRow("Tags:", self.tags_edit)
        
        # Estimated duration
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 999)
        self.duration_spin.setValue(5)
        self.duration_spin.setSuffix(" minutes")
        layout.addRow("Estimated Duration:", self.duration_spin)
        
        # Automation enabled
        self.automation_check = QCheckBox("Enable automation")
        self.automation_check.setChecked(True)
        layout.addRow("", self.automation_check)
        
        self.tab_widget.addTab(basic_widget, "Basic Info")
        
    def create_steps_tab(self):
        """Create test steps tab"""
        steps_widget = QWidget()
        layout = QVBoxLayout(steps_widget)
        
        # Preconditions
        precond_group = QGroupBox("Preconditions")
        precond_layout = QVBoxLayout(precond_group)
        
        self.preconditions_edit = QTextEdit()
        self.preconditions_edit.setPlaceholderText("Enter test preconditions")
        self.preconditions_edit.setMaximumHeight(80)
        precond_layout.addWidget(self.preconditions_edit)
        
        layout.addWidget(precond_group)
        
        # Test steps
        steps_group = QGroupBox("Test Steps")
        steps_layout = QVBoxLayout(steps_group)
        
        # Step buttons
        step_buttons = QHBoxLayout()
        
        add_step_btn = QPushButton("Add Step")
        add_step_btn.clicked.connect(self.add_test_step)
        step_buttons.addWidget(add_step_btn)
        
        remove_step_btn = QPushButton("Remove Step")
        remove_step_btn.clicked.connect(self.remove_test_step)
        step_buttons.addWidget(remove_step_btn)
        
        move_up_btn = QPushButton("Move Up")
        move_up_btn.clicked.connect(self.move_step_up)
        step_buttons.addWidget(move_up_btn)
        
        move_down_btn = QPushButton("Move Down")
        move_down_btn.clicked.connect(self.move_step_down)
        step_buttons.addWidget(move_down_btn)
        
        step_buttons.addStretch()
        steps_layout.addLayout(step_buttons)
        
        # Steps list
        self.steps_list = QListWidget()
        self.steps_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        steps_layout.addWidget(self.steps_list)
        
        # Step input
        step_input_layout = QHBoxLayout()
        
        self.step_input = QLineEdit()
        self.step_input.setPlaceholderText("Enter test step")
        self.step_input.returnPressed.connect(self.add_test_step)
        step_input_layout.addWidget(self.step_input)
        
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_test_step)
        step_input_layout.addWidget(add_btn)
        
        steps_layout.addLayout(step_input_layout)
        
        layout.addWidget(steps_group)
        
        # Expected result
        result_group = QGroupBox("Expected Result")
        result_layout = QVBoxLayout(result_group)
        
        self.expected_result_edit = QTextEdit()
        self.expected_result_edit.setPlaceholderText("Enter expected test result")
        self.expected_result_edit.setMaximumHeight(80)
        result_layout.addWidget(self.expected_result_edit)
        
        layout.addWidget(result_group)
        
        self.tab_widget.addTab(steps_widget, "Test Steps")
        
    def create_assertions_tab(self):
        """Create assertions tab"""
        assertions_widget = QWidget()
        layout = QVBoxLayout(assertions_widget)
        
        # Assertions group
        assertions_group = QGroupBox("Test Assertions")
        assertions_layout = QVBoxLayout(assertions_group)
        
        # Assertion buttons
        assertion_buttons = QHBoxLayout()
        
        add_assertion_btn = QPushButton("Add Assertion")
        add_assertion_btn.clicked.connect(self.add_assertion)
        assertion_buttons.addWidget(add_assertion_btn)
        
        remove_assertion_btn = QPushButton("Remove Assertion")
        remove_assertion_btn.clicked.connect(self.remove_assertion)
        assertion_buttons.addWidget(remove_assertion_btn)
        
        assertion_buttons.addStretch()
        assertions_layout.addLayout(assertion_buttons)
        
        # Assertions list
        self.assertions_list = QListWidget()
        assertions_layout.addWidget(self.assertions_list)
        
        # Assertion input
        assertion_input_layout = QVBoxLayout()
        
        # Assertion type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        
        self.assertion_type_combo = QComboBox()
        self.assertion_type_combo.addItems([
            "Element Exists", "Element Visible", "Element Text Equals",
            "Element Text Contains", "Element Attribute Equals", "Page Title Equals",
            "Page URL Contains", "Element Count Equals", "Element Enabled",
            "Element Selected"
        ])
        type_layout.addWidget(self.assertion_type_combo)
        type_layout.addStretch()
        
        assertion_input_layout.addLayout(type_layout)
        
        # Assertion selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Selector:"))
        
        self.assertion_selector_edit = QLineEdit()
        self.assertion_selector_edit.setPlaceholderText("CSS selector or XPath")
        selector_layout.addWidget(self.assertion_selector_edit)
        
        assertion_input_layout.addLayout(selector_layout)
        
        # Assertion value
        value_layout = QHBoxLayout()
        value_layout.addWidget(QLabel("Expected Value:"))
        
        self.assertion_value_edit = QLineEdit()
        self.assertion_value_edit.setPlaceholderText("Expected value (if applicable)")
        value_layout.addWidget(self.assertion_value_edit)
        
        add_assertion_final_btn = QPushButton("Add")
        add_assertion_final_btn.clicked.connect(self.add_assertion)
        value_layout.addWidget(add_assertion_final_btn)
        
        assertion_input_layout.addLayout(value_layout)
        
        assertions_layout.addLayout(assertion_input_layout)
        
        layout.addWidget(assertions_group)
        
        self.tab_widget.addTab(assertions_widget, "Assertions")
        
    def create_metadata_tab(self):
        """Create metadata tab"""
        metadata_widget = QWidget()
        layout = QFormLayout(metadata_widget)
        
        # Test environment
        self.environment_combo = QComboBox()
        self.environment_combo.addItems(["Development", "Testing", "Staging", "Production"])
        layout.addRow("Environment:", self.environment_combo)
        
        # Browser requirements
        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["Any", "Chrome", "Firefox", "Safari", "Edge"])
        layout.addRow("Browser:", self.browser_combo)
        
        # Device type
        self.device_combo = QComboBox()
        self.device_combo.addItems(["Desktop", "Mobile", "Tablet", "Any"])
        layout.addRow("Device Type:", self.device_combo)
        
        # Test data requirements
        self.test_data_edit = QTextEdit()
        self.test_data_edit.setPlaceholderText("Describe required test data")
        self.test_data_edit.setMaximumHeight(80)
        layout.addRow("Test Data:", self.test_data_edit)
        
        # Dependencies
        self.dependencies_edit = QTextEdit()
        self.dependencies_edit.setPlaceholderText("List test dependencies")
        self.dependencies_edit.setMaximumHeight(80)
        layout.addRow("Dependencies:", self.dependencies_edit)
        
        # Author
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("Test case author")
        layout.addRow("Author:", self.author_edit)
        
        self.tab_widget.addTab(metadata_widget, "Metadata")
        
    def add_test_step(self):
        """Add a test step"""
        step_text = self.step_input.text().strip()
        if step_text:
            step_number = self.steps_list.count() + 1
            item = QListWidgetItem(f"{step_number}. {step_text}")
            self.steps_list.addItem(item)
            self.step_input.clear()
            
    def remove_test_step(self):
        """Remove selected test step"""
        current_row = self.steps_list.currentRow()
        if current_row >= 0:
            self.steps_list.takeItem(current_row)
            self.renumber_steps()
            
    def move_step_up(self):
        """Move selected step up"""
        current_row = self.steps_list.currentRow()
        if current_row > 0:
            item = self.steps_list.takeItem(current_row)
            self.steps_list.insertItem(current_row - 1, item)
            self.steps_list.setCurrentRow(current_row - 1)
            self.renumber_steps()
            
    def move_step_down(self):
        """Move selected step down"""
        current_row = self.steps_list.currentRow()
        if current_row < self.steps_list.count() - 1:
            item = self.steps_list.takeItem(current_row)
            self.steps_list.insertItem(current_row + 1, item)
            self.steps_list.setCurrentRow(current_row + 1)
            self.renumber_steps()
            
    def renumber_steps(self):
        """Renumber all test steps"""
        for i in range(self.steps_list.count()):
            item = self.steps_list.item(i)
            text = item.text()
            # Remove existing number and add new one
            if '. ' in text:
                text = '. '.join(text.split('. ')[1:])
            item.setText(f"{i + 1}. {text}")
            
    def add_assertion(self):
        """Add a test assertion"""
        assertion_type = self.assertion_type_combo.currentText()
        selector = self.assertion_selector_edit.text().strip()
        value = self.assertion_value_edit.text().strip()
        
        if not selector:
            return
            
        if value:
            assertion_text = f"{assertion_type}: {selector} = '{value}'"
        else:
            assertion_text = f"{assertion_type}: {selector}"
            
        item = QListWidgetItem(assertion_text)
        self.assertions_list.addItem(item)
        
        # Clear inputs
        self.assertion_selector_edit.clear()
        self.assertion_value_edit.clear()
        
    def remove_assertion(self):
        """Remove selected assertion"""
        current_row = self.assertions_list.currentRow()
        if current_row >= 0:
            self.assertions_list.takeItem(current_row)
            
    def load_data(self):
        """Load test case data for editing"""
        if not self.test_case:
            return
            
        # Basic info
        self.title_edit.setText(self.test_case.get('title', ''))
        self.description_edit.setPlainText(self.test_case.get('description', ''))
        
        type_text = self.test_case.get('type', 'Functional')
        type_index = self.type_combo.findText(type_text)
        if type_index >= 0:
            self.type_combo.setCurrentIndex(type_index)
            
        priority_text = self.test_case.get('priority', 'Medium')
        priority_index = self.priority_combo.findText(priority_text)
        if priority_index >= 0:
            self.priority_combo.setCurrentIndex(priority_index)
            
        status_text = self.test_case.get('status', 'Draft')
        status_index = self.status_combo.findText(status_text)
        if status_index >= 0:
            self.status_combo.setCurrentIndex(status_index)
            
        self.tags_edit.setText(self.test_case.get('tags', ''))
        self.duration_spin.setValue(self.test_case.get('estimated_duration', 5))
        self.automation_check.setChecked(self.test_case.get('automation_enabled', True))
        
        # Steps
        self.preconditions_edit.setPlainText(self.test_case.get('preconditions', ''))
        self.expected_result_edit.setPlainText(self.test_case.get('expected_result', ''))
        
        steps = self.test_case.get('steps', [])
        for i, step in enumerate(steps):
            item = QListWidgetItem(f"{i + 1}. {step}")
            self.steps_list.addItem(item)
            
        # Assertions
        assertions = self.test_case.get('assertions', [])
        for assertion in assertions:
            item = QListWidgetItem(assertion)
            self.assertions_list.addItem(item)
            
        # Metadata
        environment = self.test_case.get('environment', 'Development')
        env_index = self.environment_combo.findText(environment)
        if env_index >= 0:
            self.environment_combo.setCurrentIndex(env_index)
            
        browser = self.test_case.get('browser', 'Any')
        browser_index = self.browser_combo.findText(browser)
        if browser_index >= 0:
            self.browser_combo.setCurrentIndex(browser_index)
            
        device = self.test_case.get('device_type', 'Desktop')
        device_index = self.device_combo.findText(device)
        if device_index >= 0:
            self.device_combo.setCurrentIndex(device_index)
            
        self.test_data_edit.setPlainText(self.test_case.get('test_data', ''))
        self.dependencies_edit.setPlainText(self.test_case.get('dependencies', ''))
        self.author_edit.setText(self.test_case.get('author', ''))
        
    def get_test_case_data(self) -> Dict[str, Any]:
        """Get test case data from form"""
        # Get steps
        steps = []
        for i in range(self.steps_list.count()):
            step_text = self.steps_list.item(i).text()
            # Remove step number
            if '. ' in step_text:
                step_text = '. '.join(step_text.split('. ')[1:])
            steps.append(step_text)
            
        # Get assertions
        assertions = []
        for i in range(self.assertions_list.count()):
            assertions.append(self.assertions_list.item(i).text())
            
        return {
            'title': self.title_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip(),
            'type': self.type_combo.currentText(),
            'priority': self.priority_combo.currentText(),
            'status': self.status_combo.currentText(),
            'tags': self.tags_edit.text().strip(),
            'estimated_duration': self.duration_spin.value(),
            'automation_enabled': self.automation_check.isChecked(),
            'preconditions': self.preconditions_edit.toPlainText().strip(),
            'steps': steps,
            'expected_result': self.expected_result_edit.toPlainText().strip(),
            'assertions': assertions,
            'environment': self.environment_combo.currentText(),
            'browser': self.browser_combo.currentText(),
            'device_type': self.device_combo.currentText(),
            'test_data': self.test_data_edit.toPlainText().strip(),
            'dependencies': self.dependencies_edit.toPlainText().strip(),
            'author': self.author_edit.text().strip()
        }
