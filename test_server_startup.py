#!/usr/bin/env python3
"""
FastAPI Server Startup Test
Tests if the FastAPI server can start without import or syntax errors
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

def test_imports():
    """Test if all modules can be imported without errors"""
    print("=== Testing Imports ===")
    
    try:
        # Test main imports
        print("Testing main.py imports...")
        import main
        print("✓ main.py imported successfully")
        
        # Test service imports
        print("Testing services imports...")
        from services import translation, anonymization, pipeline, websocket_manager
        print("✓ All services imported successfully")
        
        # Test routes imports
        print("Testing routes imports...")
        from routes import pdf_processing
        print("✓ Routes imported successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

def test_fastapi_creation():
    """Test if FastAPI app can be created"""
    print("\n=== Testing FastAPI App Creation ===")
    
    try:
        from main import app
        print("✓ FastAPI app created successfully")
        print(f"App title: {app.title}")
        return True
        
    except Exception as e:
        print(f"✗ FastAPI app creation failed: {e}")
        return False

def test_dependencies():
    """Test if all required dependencies are available"""
    print("\n=== Testing Dependencies ===")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'python-multipart',
        'websockets',
        'google.generativeai',
        'python-dotenv',
        'spacy',
        'transformers',
        'torch',
        'opencv-python',
        'pillow',
        'PyPDF2',
        'pdf2image',
        'pytesseract',
        'ultralytics'
    ]
    
    failed_imports = []
    
    for package in required_packages:
        try:
            if package == 'google.generativeai':
                import google.generativeai
            elif package == 'python-multipart':
                import multipart
            elif package == 'python-dotenv':
                import dotenv
            elif package == 'opencv-python':
                import cv2
            elif package == 'PyPDF2':
                import PyPDF2
            else:
                __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package}")
            failed_imports.append(package)
    
    if failed_imports:
        print(f"\n⚠ Missing packages: {', '.join(failed_imports)}")
        print("You may need to install these packages or they may have import issues")
        return False
    else:
        print("\n✓ All required packages are available")
        return True

def test_server_startup():
    """Test if the server can start"""
    print("\n=== Testing Server Startup ===")
    
    try:
        # Try to start the server in a subprocess for a few seconds
        venv_python = os.path.join(project_root, "env-api-flask", "Scripts", "python.exe")
        if not os.path.exists(venv_python):
            venv_python = "python"  # Fallback to system python
        
        print(f"Starting server with: {venv_python}")
        process = subprocess.Popen(
            [venv_python, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(project_root)
        )
        
        # Wait a few seconds for startup
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is None:
            print("✓ Server started successfully")
            
            # Try to make a simple request
            try:
                response = requests.get("http://localhost:8001/", timeout=5)
                if response.status_code == 200:
                    print("✓ Server is responding to HTTP requests")
                else:
                    print(f"⚠ Server responding but with status code: {response.status_code}")
            except requests.RequestException as e:
                print(f"⚠ Server started but not responding to requests: {e}")
            
            # Terminate the process
            process.terminate()
            process.wait()
            return True
        else:
            # Process died, get error output
            stdout, stderr = process.communicate()
            print(f"✗ Server failed to start")
            if stderr:
                print(f"Error: {stderr.decode()}")
            if stdout:
                print(f"Output: {stdout.decode()}")
            return False
            
    except Exception as e:
        print(f"✗ Server startup test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("FastAPI Server Startup Test")
    print("="*40)
    
    results = {}
    
    # Test imports
    results['Imports'] = test_imports()
    
    # Test FastAPI creation
    results['FastAPI Creation'] = test_fastapi_creation()
    
    # Test dependencies
    results['Dependencies'] = test_dependencies()
    
    # Test server startup (only if other tests pass)
    if all(results.values()):
        results['Server Startup'] = test_server_startup()
    else:
        print("\n⚠ Skipping server startup test due to previous failures")
        results['Server Startup'] = False
    
    # Generate report
    print("\n" + "="*40)
    print("         TEST REPORT")
    print("="*40)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    print("\nDetailed Results:")
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {test_name}: {status}")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Your FastAPI server is ready.")
    else:
        print(f"\n⚠ {total_tests - passed_tests} test(s) failed. Please address the issues above.")

if __name__ == "__main__":
    main()
