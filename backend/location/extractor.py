import re
import geocoder
from geopy.geocoders import Nominatim
from typing import Dict, Optional, Tuple
import asyncio

class LocationExtractor:
    """
    Extract and geocode location information from text descriptions.
    
    Uses pattern matching and geocoding services to identify locations
    and convert them to coordinates and standardized addresses.
    """
    
    def __init__(self):
        """Initialize geocoding services."""
        self.geolocator = Nominatim(user_agent="pollution_analyzer_v1.0")
        
        # Common location patterns
        self.location_patterns = [
            # Street addresses
            r'\b\d+\s+[A-Za-z\s]+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln)\b',
            # Intersections
            r'\b[A-Za-z\s]+\s+(?:and|&|\+)\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd)\b',
            # Near landmarks
            r'\bnear\s+[A-Za-z\s]+(?:Park|School|Hospital|Mall|Center|Plaza)\b',
            # City, State patterns
            r'\b[A-Za-z\s]+,\s*[A-Z]{2}\b',
            # Coordinates (lat, lon)
            r'\b-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\b',
            # Zip codes in addresses
            r'\b[A-Za-z\s]+\s+\d{5}(?:-\d{4})?\b'
        ]
        
        # Location keywords that might indicate a place
        self.location_keywords = [
            'located', 'at', 'near', 'on', 'by', 'beside', 'next to',
            'intersection', 'corner', 'between', 'behind', 'front of',
            'park', 'river', 'lake', 'beach', 'highway', 'freeway'
        ]
    
    async def extract_location(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract location information from text and geocode it.
        
        Args:
            text: Text containing location references
            
        Returns:
            Dictionary with latitude, longitude, address, and confidence
        """
        
        try:
            # Step 1: Extract potential location strings from text
            location_candidates = self._extract_location_strings(text)
            
            if not location_candidates:
                return self._empty_location_result()
            
            # Step 2: Try to geocode each candidate
            for candidate in location_candidates:
                location_data = await self._geocode_location(candidate)
                if location_data["latitude"] and location_data["longitude"]:
                    location_data["extracted_text"] = candidate
                    return location_data
            
            # Step 3: Fallback - try geocoding entire text if specific extraction fails
            fallback_result = await self._geocode_location(text)
            if fallback_result["latitude"] and fallback_result["longitude"]:
                fallback_result["extracted_text"] = "full_text_geocoded"
                return fallback_result
            
            return self._empty_location_result()
            
        except Exception as e:
            return {
                "latitude": None,
                "longitude": None,
                "address": None,
                "confidence": "error",
                "error": str(e)
            }
    
    def _extract_location_strings(self, text: str) -> list:
        """Extract potential location strings using pattern matching."""
        
        candidates = []
        text_clean = text.strip()
        
        # Extract using regex patterns
        for pattern in self.location_patterns:
            matches = re.findall(pattern, text_clean, re.IGNORECASE)
            candidates.extend(matches)
        
        # Extract sentences containing location keywords
        sentences = re.split(r'[.!?]+', text_clean)
        for sentence in sentences:
            sentence = sentence.strip()
            if any(keyword in sentence.lower() for keyword in self.location_keywords):
                # Extract the part after location keywords
                for keyword in self.location_keywords:
                    if keyword in sentence.lower():
                        parts = sentence.lower().split(keyword)
                        if len(parts) > 1:
                            potential_location = parts[1].strip()
                            # Clean up the extracted location
                            potential_location = re.sub(r'^(the|a|an)\s+', '', potential_location, flags=re.IGNORECASE)
                            if len(potential_location) > 3:  # Avoid very short extractions
                                candidates.append(potential_location)
        
        # Remove duplicates and sort by length (longer strings first)
        candidates = list(set(candidates))
        candidates.sort(key=len, reverse=True)
        
        return candidates[:5]  # Limit to top 5 candidates to avoid excessive API calls
    
    async def _geocode_location(self, location_string: str) -> Dict[str, Optional[str]]:
        """
        Geocode a location string to coordinates and address.
        
        Args:
            location_string: String describing a location
            
        Returns:
            Dictionary with geocoding results
        """
        
        try:
            # First try with Nominatim (OpenStreetMap)
            location = await asyncio.to_thread(
                self.geolocator.geocode, 
                location_string, 
                timeout=10
            )
            
            if location:
                return {
                    "latitude": str(location.latitude),
                    "longitude": str(location.longitude),
                    "address": location.address,
                    "confidence": "high"
                }
            
            # Fallback to geocoder library with multiple providers
            return await self._fallback_geocoding(location_string)
            
        except Exception as e:
            print(f"Geocoding error for '{location_string}': {str(e)}")
            return {
                "latitude": None,
                "longitude": None,
                "address": None,
                "confidence": "failed",
                "error": str(e)
            }
    
    async def _fallback_geocoding(self, location_string: str) -> Dict[str, Optional[str]]:
        """Fallback geocoding using geocoder library with multiple providers."""
        
        providers = ['osm', 'arcgis']  # OpenStreetMap and ArcGIS
        
        for provider in providers:
            try:
                result = await asyncio.to_thread(
                    geocoder.geocode, 
                    location_string, 
                    provider=provider
                )
                
                if result and result.latlng:
                    return {
                        "latitude": str(result.latlng[0]),
                        "longitude": str(result.latlng[1]),
                        "address": result.address or location_string,
                        "confidence": "medium"
                    }
                    
            except Exception as e:
                print(f"Fallback geocoding error with {provider}: {str(e)}")
                continue
        
        return self._empty_location_result()
    
    def _empty_location_result(self) -> Dict[str, Optional[str]]:
        """Return empty location result structure."""
        return {
            "latitude": None,
            "longitude": None,
            "address": None,
            "confidence": "none"
        }
    
    def _parse_coordinates(self, text: str) -> Optional[Tuple[float, float]]:
        """Extract coordinates if directly provided in text."""
        
        # Look for coordinate patterns like "37.7749, -122.4194"
        coord_pattern = r'(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)'
        matches = re.findall(coord_pattern, text)
        
        for match in matches:
            try:
                lat, lon = float(match[0]), float(match[1])
                # Basic validation for reasonable coordinate ranges
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (lat, lon)
            except ValueError:
                continue
        
        return None