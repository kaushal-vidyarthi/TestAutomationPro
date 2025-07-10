"""
Cloud LLM client using OpenAI API for test generation
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
import os
from openai import OpenAI

class CloudLLMClient:
    """Client for cloud-based LLM services (OpenAI)"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.model = config.get('openai_model', 'gpt-4o')
        self.max_tokens = config.get('max_tokens', 2000)
        self.temperature = config.get('temperature', 0.3)
        self.top_p = config.get('top_p', 0.9)
        
        # Initialize OpenAI client
        api_key = config.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key is required for cloud LLM")
        
        self.client = OpenAI(api_key=api_key)
        
        # Test API connection
        self.api_available = self.test_api_connection()
    
    def test_api_connection(self) -> bool:
        """Test OpenAI API connection"""
        try:
            # Simple test request
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            logging.error(f"OpenAI API connection failed: {e}")
            return False
    
    def generate_tests(self, prompt: str) -> str:
        """Generate test cases using OpenAI"""
        if not self.api_available:
            raise Exception("OpenAI API not available")
        
        try:
            # Prepare system message for test generation
            system_message = """You are an expert software testing engineer specializing in automated test case generation for web applications. Your task is to create comprehensive, practical, and executable test cases.

Guidelines:
1. Generate test cases that are specific, actionable, and cover both positive and negative scenarios
2. Include clear step-by-step instructions with specific selectors when possible
3. Create realistic assertions that verify expected behavior
4. Consider edge cases, error handling, and accessibility
5. Ensure test cases are maintainable and follow testing best practices

Always respond with valid JSON format containing an array of test case objects. Each test case must include:
- title: Clear, descriptive test case name
- description: What the test validates  
- priority: High/Medium/Low
- steps: Array of specific test steps
- expected_result: Expected outcome
- test_data: Required test data (if any)
- assertions: Array of specific assertions to verify"""

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"{prompt}\n\nGenerate test cases in JSON format."}
            ]
            
            # Make API request
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                response_format={"type": "json_object"}
            )
            
            if response.choices and response.choices[0].message:
                generated_text = response.choices[0].message.content
                return self.process_response(generated_text)
            else:
                raise Exception("Empty response from OpenAI")
                
        except Exception as e:
            logging.error(f"OpenAI test generation failed: {e}")
            raise
    
    def process_response(self, response: str) -> str:
        """Process and validate OpenAI response"""
        try:
            # Parse JSON to validate structure
            parsed = json.loads(response)
            
            # If response contains 'test_cases' key, extract it
            if isinstance(parsed, dict) and 'test_cases' in parsed:
                return json.dumps(parsed['test_cases'])
            
            # If response is already an array, return as-is
            if isinstance(parsed, list):
                return response
            
            # If response is a single object, wrap in array
            if isinstance(parsed, dict):
                return json.dumps([parsed])
            
            return response
            
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON response from OpenAI: {e}")
            # Try to extract JSON from response
            return self.extract_json_from_text(response)
    
    def extract_json_from_text(self, text: str) -> str:
        """Extract JSON from text response"""
        import re
        
        # Try to find JSON array or object in the text
        json_pattern = r'(\[.*?\]|\{.*?\})'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                json.loads(match)
                return match
            except json.JSONDecodeError:
                continue
        
        # If no valid JSON found, return original text
        return text
    
    def generate_test_scenarios(self, requirements: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate test scenarios from requirements"""
        try:
            prompt = f"""
            Based on the following requirements, generate comprehensive test scenarios:
            
            Requirements: {requirements}
            """
            
            if context:
                prompt += f"\nAdditional Context: {json.dumps(context, indent=2)}"
            
            prompt += """
            
            Generate test scenarios that cover:
            1. Happy path workflows
            2. Edge cases and boundary conditions
            3. Error handling and validation
            4. User experience considerations
            5. Performance and accessibility aspects
            
            Format the response as a JSON object with a 'test_scenarios' array.
            """
            
            messages = [
                {"role": "system", "content": "You are a senior QA engineer creating test scenarios for web applications."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Failed to generate test scenarios: {e}")
            raise
    
    def enhance_test_case(self, test_case: Dict[str, Any]) -> str:
        """Enhance existing test case with AI suggestions"""
        try:
            prompt = f"""
            Analyze and enhance the following test case:
            
            Current Test Case:
            {json.dumps(test_case, indent=2)}
            
            Provide enhancements for:
            1. More detailed test steps with specific actions
            2. Additional assertions for comprehensive validation
            3. Edge cases and error scenarios
            4. Test data variations
            5. Performance and accessibility considerations
            
            Return the enhanced test case in JSON format.
            """
            
            messages = [
                {"role": "system", "content": "You are an expert test engineer improving test case quality and coverage."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Failed to enhance test case: {e}")
            raise
    
    def generate_test_data(self, test_case: Dict[str, Any], data_type: str = "comprehensive") -> str:
        """Generate test data for test cases"""
        try:
            prompt = f"""
            Generate realistic test data for the following test case:
            
            Test Case: {json.dumps(test_case, indent=2)}
            
            Data Type: {data_type}
            
            Generate test data sets for:
            1. Valid/positive scenarios
            2. Invalid/negative scenarios  
            3. Boundary value testing
            4. Special characters and internationalization
            5. Performance testing (large datasets)
            
            Format as JSON with different data sets categorized by scenario type.
            """
            
            messages = [
                {"role": "system", "content": "You are a test data specialist creating realistic test data sets."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.5,  # Slightly higher for varied data
                response_format={"type": "json_object"}
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Failed to generate test data: {e}")
            raise
    
    def analyze_page_for_testing(self, page_data: Dict[str, Any]) -> str:
        """Analyze page structure and suggest testing strategies"""
        try:
            prompt = f"""
            Analyze the following page structure and suggest comprehensive testing strategies:
            
            Page Data:
            {json.dumps(page_data, indent=2)}
            
            Provide analysis for:
            1. Critical user journeys and workflows
            2. UI components that need testing
            3. Potential risk areas and failure points
            4. Accessibility and usability considerations
            5. Performance testing opportunities
            6. Security testing considerations
            
            Format response as JSON with structured testing recommendations.
            """
            
            messages = [
                {"role": "system", "content": "You are a senior QA architect analyzing web applications for comprehensive testing strategies."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Failed to analyze page for testing: {e}")
            raise
    
    def generate_accessibility_tests(self, page_elements: List[Dict[str, Any]]) -> str:
        """Generate accessibility-specific test cases"""
        try:
            prompt = f"""
            Generate accessibility test cases for the following page elements:
            
            Elements: {json.dumps(page_elements, indent=2)}
            
            Focus on WCAG 2.1 compliance and generate tests for:
            1. Keyboard navigation and focus management
            2. Screen reader compatibility
            3. Color contrast and visual design
            4. Alternative text and labels
            5. Form accessibility
            6. Interactive element accessibility
            
            Format as JSON array of accessibility test cases.
            """
            
            messages = [
                {"role": "system", "content": "You are an accessibility testing expert creating WCAG-compliant test cases."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Failed to generate accessibility tests: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if cloud LLM is available"""
        return self.api_available
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics (if available)"""
        # Note: OpenAI doesn't provide usage stats through the API
        # This is a placeholder for potential future functionality
        return {
            'model': self.model,
            'requests_made': 'N/A',
            'tokens_used': 'N/A',
            'cost_estimate': 'N/A'
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check of cloud LLM service"""
        health_status = {
            'api_available': False,
            'model_accessible': False,
            'response_time': None,
            'error_message': None
        }
        
        try:
            start_time = time.time()
            
            # Test basic API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Test connection"}],
                max_tokens=10
            )
            
            health_status['api_available'] = True
            health_status['model_accessible'] = True
            health_status['response_time'] = time.time() - start_time
            
        except Exception as e:
            health_status['error_message'] = str(e)
            if "model" in str(e).lower():
                health_status['api_available'] = True
                health_status['model_accessible'] = False
            
        return health_status
