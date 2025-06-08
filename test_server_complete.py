#!/usr/bin/env python3
"""
Complete FastAPI Server Test
Tests the complete FastAPI application setup including all routes and dependencies.
"""

import sys
import os
import traceback
from contextlib import contextmanager

def test_imports():
    """Test all critical imports"""
    print("🔍 Testing imports...")
    
    try:
        # Core FastAPI imports
        import fastapi
        import uvicorn
        print(f"✅ FastAPI {fastapi.__version__}")
        print(f"✅ Uvicorn {uvicorn.__version__}")
        
        # Google AI imports
        import google.generativeai as genai
        print("✅ Google Generative AI")
        
        # PDF processing imports
        import fitz  # PyMuPDF
        print("✅ PyMuPDF (fitz)")
        
        # Other critical imports
        import pandas as pd
        import numpy as np
        print(f"✅ Pandas {pd.__version__}")
        print(f"✅ NumPy {np.__version__}")
        
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_app_creation():
    """Test FastAPI app creation and routing"""
    print("\n🏗️ Testing FastAPI app creation...")
    
    try:
        from main import app
        print("✅ FastAPI app imported from main.py")
        
        # Check app type
        from fastapi import FastAPI
        if isinstance(app, FastAPI):
            print("✅ App is valid FastAPI instance")
        else:
            print(f"❌ App is not FastAPI instance: {type(app)}")
            return False
            
        # Check routes
        routes = [route.path for route in app.routes]
        print(f"✅ Available routes: {routes}")
        
        return True
    except Exception as e:
        print(f"❌ App creation error: {e}")
        traceback.print_exc()
        return False

def test_services():
    """Test service modules"""
    print("\n🔧 Testing service modules...")
    
    try:
        # Test pipeline service
        from services.pipeline import DocumentTranslationPipeline
        pipeline = DocumentTranslationPipeline()
        print("✅ DocumentTranslationPipeline imported")
        
        # Test anonymization service
        from services.anonymization import AnonymizationService
        anon_service = AnonymizationService()
        print("✅ AnonymizationService imported")
        
        # Test translation service
        from services.translation import TranslationService
        translation_service = TranslationService()
        print("✅ TranslationService imported")
        
        return True
    except Exception as e:
        print(f"❌ Service error: {e}")
        traceback.print_exc()
        return False

def test_environment():
    """Test environment configuration"""
    print("\n🌍 Testing environment configuration...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        import os
        gemini_key = os.getenv('GEMINI_API_KEY')
        if gemini_key:
            print("✅ GEMINI_API_KEY found in environment")
            print(f"✅ Key starts with: {gemini_key[:10]}...")
        else:
            print("⚠️ GEMINI_API_KEY not found in environment")
        
        return True
    except Exception as e:
        print(f"❌ Environment error: {e}")
        return False

def test_uvicorn_startup():
    """Test if uvicorn can start the server (dry run)"""
    print("\n🚀 Testing uvicorn server startup (dry run)...")
    
    try:
        # Import uvicorn and test configuration
        import uvicorn
        from main import app
        
        # Create uvicorn config (but don't run)
        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=8000,
            log_level="info"
        )
        
        print("✅ Uvicorn configuration created successfully")
        print(f"✅ Host: {config.host}")
        print(f"✅ Port: {config.port}")
        print("✅ Server ready for startup")
        
        return True
    except Exception as e:
        print(f"❌ Uvicorn startup error: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🧪 FastAPI Server Complete Test Suite")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("App Creation Test", test_app_creation),
        ("Services Test", test_services),
        ("Environment Test", test_environment),
        ("Uvicorn Startup Test", test_uvicorn_startup),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
        
        print("-" * 30)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Server is ready to run.")
        print("\n🚀 To start the server, run:")
        print("   python main.py")
        print("   or")
        print("   uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
