#!/usr/bin/env python3
"""
Comprehensive Gemini API Test Script
Tests the Gemini API key functionality for document translation
"""

import os
import sys
import asyncio
import json
from typing import Dict, Any, Optional
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Test imports
try:
    import google.generativeai as genai
    print("✓ Google Generative AI imported successfully")
except ImportError as e:
    print(f"✗ Failed to import Google Generative AI: {e}")
    sys.exit(1)

try:
    import requests
    print("✓ Requests imported successfully")
except ImportError as e:
    print(f"✗ Failed to import requests: {e}")
    sys.exit(1)


class GeminiAPITester:
    """Test the Gemini API functionality"""
    
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.model = None
        
    def check_api_key(self) -> bool:
        """Check if API key is configured"""
        print("\n=== API Key Configuration ===")
        
        if not self.api_key:
            print("✗ GEMINI_API_KEY not found in environment variables")
            return False
            
        print(f"✓ API Key found: {self.api_key[:10]}...{self.api_key[-4:]}")
        
        # Check API key format
        if not self.api_key.startswith('AIza'):
            print("⚠ Warning: API key doesn't follow expected Google format (should start with 'AIza')")
            
        return True
    
    def configure_client(self) -> bool:
        """Configure the Gemini client"""
        print("\n=== Client Configuration ===")
        
        try:
            genai.configure(api_key=self.api_key)
            print("✓ Gemini client configured successfully")
            return True
        except Exception as e:
            print(f"✗ Failed to configure Gemini client: {e}")
            return False
    
    def list_models(self) -> bool:
        """List available models"""
        print("\n=== Available Models ===")
        
        try:
            models = genai.list_models()
            available_models = []
            
            for model in models:
                if 'generateContent' in model.supported_generation_methods:
                    available_models.append(model.name)
                    print(f"✓ {model.name}")
            
            if not available_models:
                print("✗ No models available for content generation")
                return False
                
            print(f"\nTotal available models: {len(available_models)}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to list models: {e}")
            return False
    
    def test_basic_generation(self) -> bool:
        """Test basic text generation"""
        print("\n=== Basic Text Generation Test ===")
        
        try:
            # Use the recommended model
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Simple test prompt
            test_prompt = "Hello! Please respond with 'API test successful' to confirm the connection is working."
            
            print(f"Sending test prompt: {test_prompt}")
            response = model.generate_content(test_prompt)
            
            if response and response.text:
                print(f"✓ Response received: {response.text.strip()}")
                return True
            else:
                print("✗ Empty response received")
                return False
                
        except Exception as e:
            print(f"✗ Basic generation test failed: {e}")
            return False
    
    def test_translation(self) -> bool:
        """Test translation functionality"""
        print("\n=== Translation Test ===")
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Test text to translate
            test_text = "Hello, this is a test document for translation. Please translate this to French."
            
            translation_prompt = f"""
            Please translate the following English text to French. 
            Only return the translated text without any additional comments or explanations.
            
            Text to translate: {test_text}
            """
            
            print(f"Testing translation of: {test_text}")
            response = model.generate_content(translation_prompt)
            
            if response and response.text:
                translated_text = response.text.strip()
                print(f"✓ Translation successful: {translated_text}")
                
                # Basic validation - check if it's actually in French
                if any(word in translated_text.lower() for word in ['bonjour', 'salut', 'ceci', 'est', 'pour', 'de']):
                    print("✓ Translation appears to be in French")
                    return True
                else:
                    print("⚠ Translation may not be accurate or in the target language")
                    return False
            else:
                print("✗ Empty translation response")
                return False
                
        except Exception as e:
            print(f"✗ Translation test failed: {e}")
            return False
    
    def test_document_processing_prompt(self) -> bool:
        """Test document processing with a structured prompt"""
        print("\n=== Document Processing Test ===")
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Simulate a document processing scenario
            document_content = """
            Invoice #12345
            Date: January 15, 2024
            
            Customer Information:
            Name: John Doe
            Address: 123 Main Street, City, State 12345
            
            Items:
            - Product A: $50.00
            - Product B: $75.00
            
            Total: $125.00
            """
            
            processing_prompt = f"""
            You are a document translation AI. Please translate the following document from English to Spanish.
            Maintain the document structure and format. Translate all text content while preserving:
            - Numbers and dates
            - Formatting structure
            - Currency symbols
            
            Document to translate:
            {document_content}
            
            Return only the translated document without additional commentary.
            """
            
            print("Testing document processing and translation...")
            response = model.generate_content(processing_prompt)
            
            if response and response.text:
                translated_doc = response.text.strip()
                print("✓ Document processing successful")
                print(f"Translated document preview:\n{translated_doc[:200]}...")
                
                # Check if Spanish words are present
                spanish_indicators = ['factura', 'fecha', 'cliente', 'nombre', 'dirección', 'total', 'producto']
                if any(word in translated_doc.lower() for word in spanish_indicators):
                    print("✓ Document appears to be translated to Spanish")
                    return True
                else:
                    print("⚠ Translation may not be accurate")
                    return False
            else:
                print("✗ Empty document processing response")
                return False
                
        except Exception as e:
            print(f"✗ Document processing test failed: {e}")
            return False
    
    def test_api_quota_and_limits(self) -> bool:
        """Test API quota and rate limits"""
        print("\n=== API Quota and Limits Test ===")
        
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Test multiple quick requests to check rate limiting
            success_count = 0
            total_requests = 3
            
            for i in range(total_requests):
                try:
                    response = model.generate_content(f"Quick test {i+1}: Say 'OK'")
                    if response and response.text:
                        success_count += 1
                        print(f"✓ Request {i+1}: Success")
                    else:
                        print(f"✗ Request {i+1}: Empty response")
                except Exception as e:
                    print(f"✗ Request {i+1}: Failed - {e}")
            
            if success_count == total_requests:
                print(f"✓ All {total_requests} requests successful - No immediate rate limiting issues")
                return True
            elif success_count > 0:
                print(f"⚠ {success_count}/{total_requests} requests successful - Some issues detected")
                return True
            else:
                print(f"✗ All requests failed - Possible quota or authentication issues")
                return False
                
        except Exception as e:
            print(f"✗ Quota test failed: {e}")
            return False
    
    async def test_async_functionality(self) -> bool:
        """Test async functionality (if needed for the application)"""
        print("\n=== Async Functionality Test ===")
        
        try:
            # Note: google.generativeai doesn't have native async support
            # But we can test it in an async context
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Run in thread pool for async compatibility
            import concurrent.futures
            
            def generate_content():
                return model.generate_content("Async test: respond with 'Async OK'")
            
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = loop.run_in_executor(executor, generate_content)
                response = await future
            
            if response and response.text:
                print(f"✓ Async test successful: {response.text.strip()}")
                return True
            else:
                print("✗ Async test failed: Empty response")
                return False
                
        except Exception as e:
            print(f"✗ Async test failed: {e}")
            return False
    
    def generate_test_report(self, results: Dict[str, bool]) -> None:
        """Generate a comprehensive test report"""
        print("\n" + "="*50)
        print("           GEMINI API TEST REPORT")
        print("="*50)
        
        total_tests = len(results)
        passed_tests = sum(results.values())
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests / total_tests) * 100:.1f}%")
        
        print("\nDetailed Results:")
        for test_name, result in results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"  {test_name}: {status}")
        
        if passed_tests == total_tests:
            print("\n🎉 All tests passed! Gemini API is working correctly.")
            print("Your translation API should work properly with this configuration.")
        elif passed_tests >= total_tests * 0.7:
            print("\n⚠ Most tests passed. Some minor issues detected but API should work.")
        else:
            print("\n❌ Multiple test failures. Please check your API key and configuration.")
        
        print("\nNext Steps:")
        if passed_tests == total_tests:
            print("1. Your Gemini API is ready for production use")
            print("2. You can now test the full FastAPI server")
            print("3. Try uploading and translating documents")
        else:
            print("1. Verify your API key is correct and active")
            print("2. Check your Google Cloud project billing and quotas")
            print("3. Ensure you have the Gemini API enabled in your project")


async def main():
    """Main test function"""
    print("Starting Gemini API Comprehensive Test")
    print("="*50)
    
    tester = GeminiAPITester()
    results = {}
    
    # Run all tests
    results['API Key Check'] = tester.check_api_key()
    if not results['API Key Check']:
        print("\n❌ Cannot proceed without valid API key")
        return
    
    results['Client Configuration'] = tester.configure_client()
    if not results['Client Configuration']:
        print("\n❌ Cannot proceed without client configuration")
        return
    
    results['Model Listing'] = tester.list_models()
    results['Basic Generation'] = tester.test_basic_generation()
    results['Translation Test'] = tester.test_translation()
    results['Document Processing'] = tester.test_document_processing_prompt()
    results['Quota and Limits'] = tester.test_api_quota_and_limits()
    results['Async Functionality'] = await tester.test_async_functionality()
    
    # Generate report
    tester.generate_test_report(results)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
