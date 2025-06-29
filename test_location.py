#!/usr/bin/env python3
"""
Test script for location extraction functionality
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from location.extractor import LocationExtractor

async def test_location_extraction():
    """Test location extraction with various inputs."""
    
    print("🧪 Testing Location Extraction...")
    print("=" * 50)
    
    extractor = LocationExtractor()
    
    # Test cases with different types of location references
    test_cases = [
        "There's pollution at 123 Main Street, New York, NY",
        "I see oil spill near Central Park in Manhattan",
        "Chemical waste dumped at the intersection of 5th Avenue and Broadway",
        "Air pollution downtown Los Angeles",
        "Water contamination in Chicago near the lake",
        "Sewage overflow at Golden Gate Bridge, San Francisco",
        "Noise pollution from construction site on Highway 101",
        "Plastic waste at Santa Monica Beach, California",
        "Industrial emissions in Houston, Texas area",
        "Soil contamination near Phoenix Airport"
    ]
    
    print(f"\nTesting {len(test_cases)} different location scenarios...\n")
    
    success_count = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case}")
        print("-" * 60)
        
        try:
            result = await extractor.extract_location(test_case)
            
            if result["latitude"] and result["longitude"]:
                print(f"✅ SUCCESS")
                print(f"   📍 Coordinates: {result['latitude']}, {result['longitude']}")
                print(f"   🏠 Address: {result['address']}")
                print(f"   🎯 Confidence: {result['confidence']}")
                success_count += 1
            else:
                print(f"❌ FAILED")
                print(f"   Error: {result.get('error', 'No location found')}")
                
        except Exception as e:
            print(f"❌ EXCEPTION: {str(e)}")
        
        print()
    
    print("=" * 50)
    print(f"🏁 Test Results: {success_count}/{len(test_cases)} successful")
    print(f"Success Rate: {(success_count/len(test_cases)*100):.1f}%")
    
    if success_count > 0:
        print("✅ Location extraction is working!")
    else:
        print("❌ Location extraction needs debugging")

if __name__ == "__main__":
    asyncio.run(test_location_extraction())