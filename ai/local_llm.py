"""
Local LLM client for offline test generation
"""

import logging
import json
import subprocess
import requests
import time
from typing import Dict, Any, Optional
from pathlib import Path

class LocalLLMClient:
    """Client for local LLM inference"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_name = config.get('local_model', 'llama2')
        self.server_url = config.get('local_server_url', 'http://localhost:11434')
        self.max_tokens = config.get('max_tokens', 2000)
        self.temperature = config.get('temperature', 0.3)
        
        # Try to initialize local LLM server
        self.server_available = self.check_server_availability()
        
        if not self.server_available:
            logging.warning("Local LLM server not available. Attempting to start Ollama...")
            self.server_available = self.start_ollama_server()
    
    def check_server_availability(self) -> bool:
        """Check if local LLM server is available"""
        try:
            response = requests.get(f"{self.server_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logging.debug(f"Local LLM server not available: {e}")
            return False
    
    def start_ollama_server(self) -> bool:
        """Attempt to start Ollama server"""
        try:
            # Check if Ollama is installed
            result = subprocess.run(['ollama', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logging.warning("Ollama not found. Please install Ollama for local LLM support.")
                return False
            
            # Start Ollama serve in background
            subprocess.Popen(['ollama', 'serve'], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            
            # Wait for server to start
            for i in range(30):  # Wait up to 30 seconds
                if self.check_server_availability():
                    logging.info("Ollama server started successfully")
                    return True
                time.sleep(1)
            
            logging.warning("Failed to start Ollama server within timeout")
            return False
            
        except Exception as e:
            logging.warning(f"Failed to start Ollama server: {e}")
            return False
    
    def ensure_model_available(self) -> bool:
        """Ensure the specified model is available"""
        try:
            # Check if model is already available
            response = requests.get(f"{self.server_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model['name'] for model in models]
                
                if self.model_name in model_names:
                    return True
            
            # Try to pull the model
            logging.info(f"Pulling model {self.model_name}...")
            pull_data = {"name": self.model_name}
            
            response = requests.post(f"{self.server_url}/api/pull", 
                                   json=pull_data, timeout=300)
            
            if response.status_code == 200:
                logging.info(f"Model {self.model_name} pulled successfully")
                return True
            else:
                logging.error(f"Failed to pull model: {response.status_code}")
                return False
                
        except Exception as e:
            logging.error(f"Error ensuring model availability: {e}")
            return False
    
    def generate_tests(self, prompt: str) -> str:
        """Generate test cases using local LLM"""
        if not self.server_available:
            raise Exception("Local LLM server not available")
        
        # Ensure model is available
        if not self.ensure_model_available():
            raise Exception(f"Model {self.model_name} not available")
        
        try:
            # Prepare the request
            system_message = """You are an expert software testing engineer. Generate comprehensive, practical test cases based on the provided information. Always respond with valid JSON format containing an array of test case objects. Each test case must include: title, description, priority, steps, expected_result, and assertions fields."""
            
            formatted_prompt = f"{system_message}\n\n{prompt}\n\nPlease provide your response as a JSON array of test cases."
            
            payload = {
                "model": self.model_name,
                "prompt": formatted_prompt,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                },
                "stream": False
            }
            
            # Make the request
            response = requests.post(f"{self.server_url}/api/generate", 
                                   json=payload, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '')
                
                if generated_text:
                    return self.clean_response(generated_text)
                else:
                    raise Exception("Empty response from local LLM")
            else:
                raise Exception(f"Local LLM request failed: {response.status_code}")
                
        except requests.exceptions.Timeout:
            logging.error("Local LLM request timed out")
            raise Exception("Local LLM request timed out")
        except Exception as e:
            logging.error(f"Local LLM generation failed: {e}")
            raise
    
    def clean_response(self, response: str) -> str:
        """Clean and format LLM response"""
        try:
            # Remove markdown code blocks if present
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end != -1:
                    response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                if end != -1:
                    response = response[start:end].strip()
            
            # Try to find JSON array or object
            response = response.strip()
            
            # Look for JSON array
            if '[' in response and ']' in response:
                start = response.find('[')
                end = response.rfind(']') + 1
                json_part = response[start:end]
                
                # Validate JSON
                try:
                    json.loads(json_part)
                    return json_part
                except json.JSONDecodeError:
                    pass
            
            # Look for individual JSON objects
            import re
            json_objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            
            if json_objects:
                # Try to create an array from individual objects
                valid_objects = []
                for obj_str in json_objects:
                    try:
                        obj = json.loads(obj_str)
                        valid_objects.append(obj)
                    except json.JSONDecodeError:
                        continue
                
                if valid_objects:
                    return json.dumps(valid_objects)
            
            # If no valid JSON found, return the cleaned response
            return response
            
        except Exception as e:
            logging.warning(f"Error cleaning response: {e}")
            return response
    
    def generate_test_enhancements(self, test_case: Dict[str, Any]) -> str:
        """Generate enhancements for existing test case"""
        if not self.server_available:
            raise Exception("Local LLM server not available")
        
        prompt = f"""
        Analyze the following test case and suggest improvements:
        
        Test Case: {json.dumps(test_case, indent=2)}
        
        Provide suggestions for:
        1. Additional test steps for better coverage
        2. More specific assertions
        3. Edge cases to consider
        4. Error handling scenarios
        5. Performance considerations
        
        Respond with an enhanced version of the test case in JSON format.
        """
        
        return self.generate_tests(prompt)
    
    def generate_test_data(self, test_case: Dict[str, Any]) -> str:
        """Generate test data for a test case"""
        if not self.server_available:
            raise Exception("Local LLM server not available")
        
        prompt = f"""
        Generate realistic test data for the following test case:
        
        Test Case: {json.dumps(test_case, indent=2)}
        
        Generate:
        1. Valid test data for positive scenarios
        2. Invalid test data for negative scenarios
        3. Edge case data (boundary values, special characters)
        4. Different data sets for comprehensive testing
        
        Respond with a JSON object containing different test data sets.
        """
        
        return self.generate_tests(prompt)
    
    def is_available(self) -> bool:
        """Check if local LLM is available"""
        return self.server_available and self.check_server_availability()
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        if not self.server_available:
            return {}
        
        try:
            response = requests.get(f"{self.server_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                for model in models:
                    if model['name'] == self.model_name:
                        return model
            return {}
        except Exception as e:
            logging.debug(f"Error getting model info: {e}")
            return {}
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check of local LLM service"""
        health_status = {
            'server_available': False,
            'model_available': False,
            'response_time': None,
            'error_message': None
        }
        
        try:
            start_time = time.time()
            
            # Check server
            health_status['server_available'] = self.check_server_availability()
            
            if health_status['server_available']:
                # Check model
                health_status['model_available'] = self.ensure_model_available()
                
                # Test response time with simple query
                test_prompt = "Generate a simple test case for a login button."
                try:
                    self.generate_tests(test_prompt)
                    health_status['response_time'] = time.time() - start_time
                except Exception as e:
                    health_status['error_message'] = str(e)
            else:
                health_status['error_message'] = "Server not available"
                
        except Exception as e:
            health_status['error_message'] = str(e)
        
        return health_status
