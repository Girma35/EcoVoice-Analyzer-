#!/usr/bin/env python3
"""
Quick test script to verify backend components work locally
"""

import os
import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

async def test_components():
    """Test each backend component individually"""
    
    print("🧪 Testing Backend Components...")
    print("=" * 50)
    
    # Test 1: Environment Variables
    print("\n1. Testing Environment Variables...")
    try:
        from dotenv import load_dotenv
        load_dotenv(backend_path / ".env")
        
        cohere_key = os.getenv("COHERE_API_KEY")
        db_url = os.getenv("DATABASE_URL")
        
        if cohere_key:
            print(f"   ✅ COHERE_API_KEY: {cohere_key[:10]}...")
        else:
            print("   ❌ COHERE_API_KEY missing")
            
        if db_url:
            print(f"   ✅ DATABASE_URL: {db_url[:30]}...")
        else:
            print("   ❌ DATABASE_URL missing")
            
    except Exception as e:
        print(f"   ❌ Environment setup failed: {e}")
    
    # Test 2: Import all modules
    print("\n2. Testing Module Imports...")
    try:
        from classification.classify import PollutionAnalyzerLLM
        print("   ✅ PollutionAnalyzerLLM imported")
    except Exception as e:
        print(f"   ❌ PollutionAnalyzerLLM failed: {e}")
    
    try:
        from location.extractor import LocationExtractor
        print("   ✅ LocationExtractor imported")
    except Exception as e:
        print(f"   ❌ LocationExtractor failed: {e}")
    
    try:
        from voice.voice_recognizer import VoiceRecognizer
        print("   ✅ VoiceRecognizer imported")
    except Exception as e:
        print(f"   ❌ VoiceRecognizer failed: {e}")
    
    try:
        from LangChainHelper.langchain_helper import LangChainHelper
        print("   ✅ LangChainHelper imported")
    except Exception as e:
        print(f"   ❌ LangChainHelper failed: {e}")
    
    # Test 3: FastAPI app
    print("\n3. Testing FastAPI App...")
    try:
        from main import app
        print("   ✅ FastAPI app created successfully")
        
        # Check endpoints
        routes = [route.path for route in app.routes]
        expected_routes = ["/analyze", "/ask", "/health"]
        
        for route in expected_routes:
            if route in routes:
                print(f"   ✅ Route {route} exists")
            else:
                print(f"   ❌ Route {route} missing")
                
    except Exception as e:
        print(f"   ❌ FastAPI app failed: {e}")
    
    # Test 4: Database Connection
    print("\n4. Testing Database Connection...")
    try:
        helper = LangChainHelper()
        await helper.initialize_db()
        print("   ✅ Database initialized successfully")
        
        # Test basic query
        stats = await helper.get_statistics()
        print(f"   ✅ Database stats: {stats.get('total_records', 0)} records")
        
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
    
    # Test 5: AI Components (without heavy models)
    print("\n5. Testing AI Components...")
    try:
        analyzer = PollutionAnalyzerLLM()
        print("   ✅ Cohere client initialized")
    except Exception as e:
        print(f"   ❌ Cohere initialization failed: {e}")
    
    try:
        extractor = LocationExtractor()
        print("   ✅ Location extractor initialized")
    except Exception as e:
        print(f"   ❌ Location extractor failed: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Test Complete!")
    print("\nIf all components show ✅, your backend is ready for deployment.")
    print("If you see ❌, those issues need to be fixed first.")

if __name__ == "__main__":
    asyncio.run(test_components())