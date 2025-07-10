"""
AI-powered test case generator using LLM models
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ai.local_llm import LocalLLMClient
from ai.cloud_llm import CloudLLMClient
from storage.database import DatabaseManager
from storage.vector_store import VectorStore

class TestGenerator:
    """AI-powered test case generator"""
    
    def __init__(self, ai_config: Dict[str, Any], db_manager: DatabaseManager):
        self.config = ai_config
        self.db_manager = db_manager
        self.vector_store = VectorStore(db_manager)
        
        # Initialize LLM clients
        self.use_local_llm = ai_config.get('use_local_llm', True)
        
        if self.use_local_llm:
            self.llm_client = LocalLLMClient(ai_config)
        else:
            self.llm_client = CloudLLMClient(ai_config)
        
        # Test generation templates
        self.test_templates = self.load_test_templates()
        
    def load_test_templates(self) -> Dict[str, str]:
        """Load test generation templates"""
        return {
            'functional_test': """
            Generate functional test cases for the following page elements.
            Focus on testing the core functionality and user interactions.
            
            Page Information:
            - URL: {url}
            - Title: {title}
            - Elements: {elements}
            
            Requirements: {requirements}
            
            Generate test cases that cover:
            1. Happy path scenarios
            2. Input validation
            3. Error handling
            4. User workflow completion
            
            Format each test case as JSON with these fields:
            - title: Clear, descriptive test case name
            - description: What the test validates
            - priority: High/Medium/Low
            - steps: Array of test steps
            - expected_result: Expected outcome
            - test_data: Required test data
            - assertions: Array of assertions to verify
            """,
            
            'ui_test': """
            Generate UI test cases for the following page elements.
            Focus on user interface interactions and visual validations.
            
            Page Information:
            - URL: {url}
            - Title: {title}
            - Interactive Elements: {interactive_elements}
            - UI Structure: {ui_structure}
            
            Generate UI test cases that cover:
            1. Element visibility and layout
            2. Button clicks and navigation
            3. Form interactions
            4. Responsive behavior
            5. Accessibility compliance
            
            Format each test case as JSON with these fields:
            - title: Clear, descriptive test case name
            - description: What the test validates
            - priority: High/Medium/Low
            - steps: Array of test steps with specific selectors
            - expected_result: Expected UI state
            - assertions: Array of UI assertions
            """,
            
            'integration_test': """
            Generate integration test cases for the following page and its interactions.
            Focus on testing data flow and system integrations.
            
            Page Information:
            - URL: {url}
            - Title: {title}
            - Forms: {forms}
            - API Endpoints: {api_endpoints}
            
            Generate integration test cases that cover:
            1. Form submissions and data persistence
            2. API integrations
            3. Cross-page navigation
            4. Data validation across components
            5. Error handling and recovery
            
            Format each test case as JSON with these fields:
            - title: Clear, descriptive test case name
            - description: What the test validates
            - priority: High/Medium/Low
            - steps: Array of test steps
            - expected_result: Expected system behavior
            - test_data: Required test data
            - assertions: Array of integration assertions
            """
        }
    
    def generate_tests_for_page(self, page_data: Dict[str, Any], 
                               requirements: str = "") -> List[Dict[str, Any]]:
        """Generate test cases for a single page"""
        try:
            generated_tests = []
            
            # Extract relevant page information
            page_info = self.extract_page_info(page_data)
            
            # Generate different types of tests
            test_types = ['functional_test', 'ui_test']
            
            # Add integration tests if forms are present
            if page_info.get('forms'):
                test_types.append('integration_test')
            
            for test_type in test_types:
                try:
                    tests = self.generate_tests_by_type(page_info, test_type, requirements)
                    generated_tests.extend(tests)
                except Exception as e:
                    logging.warning(f"Failed to generate {test_type} for {page_info['url']}: {e}")
            
            # Store generated tests in vector store for future reference
            self.store_generated_tests(page_info, generated_tests)
            
            return generated_tests
            
        except Exception as e:
            logging.error(f"Failed to generate tests for page: {e}")
            return []
    
    def extract_page_info(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant information from page data"""
        return {
            'url': page_data.get('url', ''),
            'title': page_data.get('title', ''),
            'elements': self.summarize_elements(page_data.get('elements', [])),
            'interactive_elements': self.filter_interactive_elements(page_data.get('elements', [])),
            'forms': page_data.get('forms', []),
            'navigation': page_data.get('navigation', {}),
            'structure': page_data.get('structure', {}),
            'ui_structure': self.summarize_ui_structure(page_data.get('structure', {})),
            'accessibility_tree': page_data.get('accessibility_tree', {}),
            'api_endpoints': self.extract_api_endpoints(page_data)
        }
    
    def summarize_elements(self, elements: List[Dict[str, Any]]) -> str:
        """Create a summary of page elements for LLM consumption"""
        if not elements:
            return "No interactive elements found"
        
        element_summary = []
        element_types = {}
        
        for element in elements:
            elem_type = element.get('type', 'unknown')
            element_types[elem_type] = element_types.get(elem_type, 0) + 1
        
        # Create summary by type
        for elem_type, count in element_types.items():
            element_summary.append(f"{count} {elem_type}(s)")
        
        # Add details for key elements
        key_elements = []
        for element in elements[:10]:  # Limit to first 10 elements
            if element.get('text') or element.get('aria_label'):
                key_elements.append({
                    'type': element.get('type'),
                    'text': element.get('text', '')[:50],
                    'selector': element.get('css_selector', ''),
                    'id': element.get('id', ''),
                    'aria_label': element.get('aria_label', '')
                })
        
        summary = f"Element types: {', '.join(element_summary)}\n"
        if key_elements:
            summary += "Key elements:\n"
            for elem in key_elements:
                summary += f"- {elem['type']}: {elem['text'] or elem['aria_label'] or elem['id']}\n"
        
        return summary
    
    def filter_interactive_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter and format interactive elements for test generation"""
        interactive_types = {'button', 'input', 'link', 'select', 'checkbox', 'radio', 'form'}
        
        interactive_elements = []
        for element in elements:
            if element.get('type') in interactive_types:
                # Simplify element data for LLM
                simplified = {
                    'type': element.get('type'),
                    'text': element.get('text', '')[:100],
                    'css_selector': element.get('css_selector', ''),
                    'id': element.get('id', ''),
                    'class': element.get('class', ''),
                    'aria_label': element.get('aria_label', ''),
                    'visible': element.get('visible', True),
                    'enabled': element.get('enabled', True)
                }
                
                # Add type-specific information
                if element.get('type') == 'input':
                    simplified['input_type'] = element.get('attributes', {}).get('type', 'text')
                    simplified['placeholder'] = element.get('attributes', {}).get('placeholder', '')
                    simplified['required'] = element.get('attributes', {}).get('required', False)
                elif element.get('type') == 'link':
                    simplified['href'] = element.get('href', '')
                
                interactive_elements.append(simplified)
        
        return interactive_elements
    
    def summarize_ui_structure(self, structure: Dict[str, Any]) -> str:
        """Summarize UI structure for LLM"""
        if not structure:
            return "No structure information available"
        
        summary_parts = []
        
        # Semantic structure
        semantic = structure.get('semantic_structure', {})
        if semantic:
            semantic_parts = []
            for key, value in semantic.items():
                if value and key.startswith('has_'):
                    semantic_parts.append(key.replace('has_', '').replace('_', ' '))
            
            if semantic_parts:
                summary_parts.append(f"Semantic elements: {', '.join(semantic_parts)}")
        
        # Headings
        headings = structure.get('heading_structure', [])
        if headings:
            heading_levels = [f"H{h['level']}: {h['text'][:50]}" for h in headings[:5]]
            summary_parts.append(f"Headings: {'; '.join(heading_levels)}")
        
        # Sections
        sections = structure.get('sections', [])
        if sections:
            section_types = [s.get('tag', 'unknown') for s in sections[:5]]
            summary_parts.append(f"Sections: {', '.join(section_types)}")
        
        return '\n'.join(summary_parts) if summary_parts else "Basic page structure"
    
    def extract_api_endpoints(self, page_data: Dict[str, Any]) -> List[str]:
        """Extract potential API endpoints from page data"""
        endpoints = []
        
        # Look for form actions
        forms = page_data.get('forms', [])
        for form in forms:
            action = form.get('action', '')
            if action and action.startswith('/') and action not in endpoints:
                endpoints.append(action)
        
        # Look for AJAX URLs in scripts (basic extraction)
        # This could be enhanced with more sophisticated analysis
        
        return endpoints
    
    def generate_tests_by_type(self, page_info: Dict[str, Any], 
                              test_type: str, requirements: str) -> List[Dict[str, Any]]:
        """Generate tests for a specific type"""
        try:
            # Get template
            template = self.test_templates.get(test_type, '')
            if not template:
                raise ValueError(f"No template found for test type: {test_type}")
            
            # Format template with page information
            prompt = template.format(
                url=page_info['url'],
                title=page_info['title'],
                elements=page_info['elements'],
                interactive_elements=json.dumps(page_info['interactive_elements'], indent=2),
                forms=json.dumps(page_info['forms'], indent=2),
                ui_structure=page_info['ui_structure'],
                api_endpoints=json.dumps(page_info['api_endpoints']),
                requirements=requirements or "Standard quality assurance testing"
            )
            
            # Add examples for better LLM performance
            prompt += self.get_test_examples(test_type)
            
            # Generate tests using LLM
            response = self.llm_client.generate_tests(prompt)
            
            # Parse and validate response
            tests = self.parse_test_response(response, test_type)
            
            # Enhance tests with additional metadata
            for test in tests:
                test['generated_by'] = 'AI'
                test['generation_type'] = test_type
                test['source_url'] = page_info['url']
                test['created_at'] = datetime.now().isoformat()
                test['automation_enabled'] = True
            
            return tests
            
        except Exception as e:
            logging.error(f"Failed to generate {test_type} tests: {e}")
            return []
    
    def get_test_examples(self, test_type: str) -> str:
        """Get example test cases to improve LLM performance"""
        examples = {
            'functional_test': '''
            
            Example test case format:
            {
                "title": "Verify user can submit contact form with valid data",
                "description": "Test that the contact form accepts valid input and submits successfully",
                "priority": "High",
                "steps": [
                    "Navigate to the contact page",
                    "Fill in the 'Name' field with 'John Doe'",
                    "Fill in the 'Email' field with 'john@example.com'",
                    "Fill in the 'Message' field with 'Test message'",
                    "Click the 'Submit' button"
                ],
                "expected_result": "Form submits successfully and confirmation message is displayed",
                "test_data": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "message": "Test message"
                },
                "assertions": [
                    "Success message is visible",
                    "Form fields are cleared",
                    "Page remains on contact page or redirects to thank you page"
                ]
            }
            ''',
            
            'ui_test': '''
            
            Example test case format:
            {
                "title": "Verify navigation menu is responsive on mobile",
                "description": "Test that the navigation menu adapts correctly to mobile viewport",
                "priority": "Medium",
                "steps": [
                    "Open page in mobile viewport (375px width)",
                    "Verify hamburger menu icon is visible",
                    "Click the hamburger menu icon",
                    "Verify menu items are displayed in mobile format"
                ],
                "expected_result": "Navigation menu displays correctly in mobile format",
                "assertions": [
                    "Hamburger icon is visible at mobile viewport",
                    "Menu items are hidden by default",
                    "Clicking hamburger reveals menu items",
                    "Menu items are stacked vertically"
                ]
            }
            ''',
            
            'integration_test': '''
            
            Example test case format:
            {
                "title": "Verify form data is saved to database",
                "description": "Test that form submission persists data correctly in the backend",
                "priority": "High",
                "steps": [
                    "Submit form with test data",
                    "Verify form submission success",
                    "Check database for saved record",
                    "Verify data integrity"
                ],
                "expected_result": "Form data is correctly saved and retrievable",
                "test_data": {
                    "test_record": "Sample data for integration test"
                },
                "assertions": [
                    "Database record is created",
                    "All form fields are saved correctly",
                    "Record can be retrieved via API",
                    "Data types match expected schema"
                ]
            }
            '''
        }
        
        return examples.get(test_type, '')
    
    def parse_test_response(self, response: str, test_type: str) -> List[Dict[str, Any]]:
        """Parse LLM response and extract test cases"""
        try:
            # Try to parse as JSON first
            if response.strip().startswith('['):
                tests = json.loads(response)
                if isinstance(tests, list):
                    return self.validate_tests(tests)
            
            # Try to extract JSON objects from response
            tests = self.extract_json_objects(response)
            return self.validate_tests(tests)
            
        except Exception as e:
            logging.error(f"Failed to parse test response: {e}")
            return []
    
    def extract_json_objects(self, text: str) -> List[Dict[str, Any]]:
        """Extract JSON objects from text response"""
        import re
        
        tests = []
        
        # Find JSON objects in the text
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                test_data = json.loads(match)
                if self.is_valid_test_structure(test_data):
                    tests.append(test_data)
            except json.JSONDecodeError:
                continue
        
        return tests
    
    def is_valid_test_structure(self, test_data: Dict[str, Any]) -> bool:
        """Validate test case structure"""
        required_fields = ['title', 'steps', 'expected_result']
        return all(field in test_data for field in required_fields)
    
    def validate_tests(self, tests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean test cases"""
        validated_tests = []
        
        for test in tests:
            if not isinstance(test, dict):
                continue
            
            # Ensure required fields
            if not self.is_valid_test_structure(test):
                continue
            
            # Clean and validate fields
            validated_test = {
                'title': str(test.get('title', 'Untitled Test')).strip(),
                'description': str(test.get('description', '')).strip(),
                'priority': self.validate_priority(test.get('priority', 'Medium')),
                'steps': self.validate_steps(test.get('steps', [])),
                'expected_result': str(test.get('expected_result', '')).strip(),
                'test_data': test.get('test_data', {}),
                'assertions': self.validate_assertions(test.get('assertions', [])),
                'type': 'AI-Generated',
                'environment': 'Testing',
                'browser': 'Any',
                'device_type': 'Desktop'
            }
            
            validated_tests.append(validated_test)
        
        return validated_tests
    
    def validate_priority(self, priority: str) -> str:
        """Validate and normalize priority"""
        valid_priorities = ['Low', 'Medium', 'High', 'Critical']
        priority_str = str(priority).strip().title()
        return priority_str if priority_str in valid_priorities else 'Medium'
    
    def validate_steps(self, steps: Any) -> List[str]:
        """Validate and clean test steps"""
        if not isinstance(steps, list):
            return []
        
        validated_steps = []
        for step in steps:
            step_str = str(step).strip()
            if step_str:
                validated_steps.append(step_str)
        
        return validated_steps
    
    def validate_assertions(self, assertions: Any) -> List[str]:
        """Validate and clean assertions"""
        if not isinstance(assertions, list):
            return []
        
        validated_assertions = []
        for assertion in assertions:
            assertion_str = str(assertion).strip()
            if assertion_str:
                validated_assertions.append(assertion_str)
        
        return validated_assertions
    
    def store_generated_tests(self, page_info: Dict[str, Any], tests: List[Dict[str, Any]]):
        """Store generated tests in vector store for future reference"""
        try:
            for test in tests:
                # Create embedding text
                embedding_text = f"""
                Page: {page_info['title']} ({page_info['url']})
                Test: {test['title']}
                Description: {test.get('description', '')}
                Steps: {' -> '.join(test.get('steps', []))}
                Expected: {test.get('expected_result', '')}
                """
                
                # Store in vector store
                self.vector_store.store_test_case(
                    test_id=hash(test['title'] + page_info['url']),
                    embedding_text=embedding_text.strip(),
                    metadata={
                        'page_url': page_info['url'],
                        'page_title': page_info['title'],
                        'test_title': test['title'],
                        'test_type': test.get('generation_type', 'unknown'),
                        'generated_at': datetime.now().isoformat()
                    }
                )
                
        except Exception as e:
            logging.warning(f"Failed to store generated tests in vector store: {e}")
    
    def generate_tests_from_requirements(self, requirements: str, 
                                       context_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate tests from natural language requirements"""
        try:
            # Find similar existing tests
            similar_tests = self.vector_store.find_similar_tests(requirements)
            
            # Create prompt for requirements-based generation
            prompt = f"""
            Generate test cases based on the following requirements:
            
            Requirements: {requirements}
            
            """
            
            if context_data:
                prompt += f"Context Information:\n{json.dumps(context_data, indent=2)}\n\n"
            
            if similar_tests:
                prompt += "Similar existing tests for reference:\n"
                for test in similar_tests[:3]:
                    prompt += f"- {test['metadata']['test_title']}\n"
                prompt += "\n"
            
            prompt += """
            Generate comprehensive test cases that cover the requirements.
            Format each test case as JSON with the required fields.
            """
            
            # Generate tests
            response = self.llm_client.generate_tests(prompt)
            tests = self.parse_test_response(response, 'requirements_based')
            
            return tests
            
        except Exception as e:
            logging.error(f"Failed to generate tests from requirements: {e}")
            return []
    
    def enhance_existing_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance an existing test case with AI suggestions"""
        try:
            prompt = f"""
            Enhance the following test case with additional steps, assertions, and edge cases:
            
            Current Test Case:
            {json.dumps(test_case, indent=2)}
            
            Provide suggestions for:
            1. Additional test steps
            2. More comprehensive assertions
            3. Edge cases to consider
            4. Error scenarios
            5. Performance considerations
            
            Return the enhanced test case in the same JSON format.
            """
            
            response = self.llm_client.generate_tests(prompt)
            enhanced_tests = self.parse_test_response(response, 'enhancement')
            
            return enhanced_tests[0] if enhanced_tests else test_case
            
        except Exception as e:
            logging.error(f"Failed to enhance test case: {e}")
            return test_case
