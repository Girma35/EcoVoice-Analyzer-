import re
import geocoder
from geopy.geocoders import Nominatim
from typing import Dict, Optional, Tuple, Any
import asyncio
import time

class LocationExtractor:
    """
    Extract and geocode location information from text descriptions.
    
    Uses pattern matching and geocoding services to identify locations
    and convert them to coordinates and standardized addresses.
    """
    
    def __init__(self):
        """Initialize geocoding services."""
        self.geolocator = Nominatim(user_agent="pollution_analyzer_v1.0", timeout=10)
        
        # Enhanced location patterns with more comprehensive matching
        self.location_patterns = [
            # Street addresses with numbers
            r'\b\d+\s+[A-Za-z\s]+(Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|Drive|Dr\.?|Lane|Ln\.?|Way|Place|Pl\.?)\b',
            # Intersections
            r'\b[A-Za-z\s]+\s+(?:and|&|\+|at)\s+[A-Za-z\s]+(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?)\b',
            # Near landmarks
            r'\bnear\s+[A-Za-z\s]+(?:Park|School|Hospital|Mall|Center|Centre|Plaza|Station|Airport|Bridge|Library|University|College)\b',
            # City, State patterns
            r'\b[A-Za-z\s]+,\s*[A-Z]{2}\b',
            # City names (common cities worldwide)
            r'\b(?:New York|Los Angeles|Chicago|Houston|Phoenix|Philadelphia|San Antonio|San Diego|Dallas|San Jose|Austin|Jacksonville|Fort Worth|Columbus|Charlotte|San Francisco|Indianapolis|Seattle|Denver|Washington|Boston|El Paso|Nashville|Detroit|Oklahoma City|Portland|Las Vegas|Memphis|Louisville|Baltimore|Milwaukee|Albuquerque|Tucson|Fresno|Sacramento|Mesa|Kansas City|Atlanta|Long Beach|Colorado Springs|Raleigh|Miami|Virginia Beach|Omaha|Oakland|Minneapolis|Tulsa|Arlington|Tampa|New Orleans|Wichita|Cleveland|Bakersfield|Aurora|Anaheim|Honolulu|Santa Ana|Riverside|Corpus Christi|Lexington|Stockton|Henderson|Saint Paul|St\. Paul|Cincinnati|Pittsburgh|Greensboro|Anchorage|Plano|Lincoln|Orlando|Irvine|Newark|Durham|Chula Vista|Toledo|Fort Wayne|St\. Petersburg|Laredo|Jersey City|Chandler|Madison|Lubbock|Scottsdale|Reno|Buffalo|Gilbert|Glendale|North Las Vegas|Winston-Salem|Chesapeake|Norfolk|Fremont|Garland|Irving|Hialeah|Richmond|Boise|Spokane|Baton Rouge|London|Paris|Berlin|Tokyo|Sydney|Toronto|Vancouver|Montreal|Rhine River|Thames|Seine|Danube|Nile|Amazon|Mississippi|Colorado River|Lahore|Karachi|Mumbai|Delhi|Beijing|Shanghai|Moscow|Istanbul|Cairo|Lagos|Nairobi|Cape Town|Rio de Janeiro|Buenos Aires|Mexico City|Lima|Bogota|Santiago|Brasilia)\b',
            # Rivers and water bodies
            r'\b(?:Rhine|Thames|Seine|Danube|Nile|Amazon|Mississippi|Colorado|Yangtze|Ganges|Indus|Mekong|Volga|Euphrates|Tigris)\s+River\b',
            # Coordinates (lat, lon)
            r'\b-?\d+\.?\d*\s*,\s*-?\d+\.?\d*\b',
            # Zip codes in addresses
            r'\b[A-Za-z\s]+\s+\d{5}(?:-\d{4})?\b',
            # Highway/Interstate references
            r'\b(?:Highway|Hwy|Interstate|I-)\s*\d+\b',
            # General location indicators
            r'\b(?:downtown|uptown|midtown|suburb|neighborhood|district)\s+[A-Za-z\s]+\b'
        ]
        
        # Enhanced location keywords
        self.location_keywords = [
            'located', 'at', 'near', 'on', 'by', 'beside', 'next to', 'close to',
            'intersection', 'corner', 'between', 'behind', 'in front of', 'across from',
            'park', 'river', 'lake', 'beach', 'highway', 'freeway', 'street', 'avenue',
            'downtown', 'uptown', 'city', 'town', 'area', 'neighborhood', 'district',
            'building', 'plaza', 'mall', 'center', 'station', 'airport', 'bridge'
        ]
        
        # Common location prepositions
        self.location_prepositions = ['at', 'on', 'in', 'near', 'by', 'around', 'along']
    
    async def extract_location(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract location information from text and geocode it.
        
        Args:
            text: Text containing location references
            
        Returns:
            Dictionary with latitude, longitude, address, and confidence
        """
        
        try:
            print(f"🔍 Extracting location from: {text[:100]}...")
            
            # Step 1: Extract potential location strings from text
            location_candidates = self._extract_location_strings(text)
            print(f"📍 Found {len(location_candidates)} location candidates: {location_candidates}")
            
            if not location_candidates:
                # Try extracting from the entire text as a fallback
                location_candidates = [text.strip()]
            
            # Step 2: Try to geocode each candidate
            for i, candidate in enumerate(location_candidates):
                print(f"🌐 Geocoding candidate {i+1}: '{candidate}'")
                location_data = await self._geocode_location(candidate)
                
                if location_data["latitude"] and location_data["longitude"]:
                    location_data["extracted_text"] = candidate
                    print(f"✅ Successfully geocoded: {location_data}")
                    return location_data
                else:
                    print(f"❌ Failed to geocode: '{candidate}'")
            
            # Step 3: Try extracting city/state patterns specifically
            city_state_candidates = self._extract_city_state_patterns(text)
            for candidate in city_state_candidates:
                print(f"🏙️ Trying city/state pattern: '{candidate}'")
                location_data = await self._geocode_location(candidate)
                if location_data["latitude"] and location_data["longitude"]:
                    location_data["extracted_text"] = candidate
                    print(f"✅ City/state geocoded: {location_data}")
                    return location_data
            
            # Step 4: Try common location extraction patterns
            common_locations = self._extract_common_locations(text)
            for candidate in common_locations:
                print(f"🏢 Trying common location: '{candidate}'")
                location_data = await self._geocode_location(candidate)
                if location_data["latitude"] and location_data["longitude"]:
                    location_data["extracted_text"] = candidate
                    print(f"✅ Common location geocoded: {location_data}")
                    return location_data
            
            print("❌ No location could be extracted and geocoded")
            return self._empty_location_result()
            
        except Exception as e:
            print(f"❌ Location extraction error: {str(e)}")
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
            if matches:
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
                            potential_location = re.sub(r'\s+', ' ', potential_location)  # Normalize whitespace
                            if len(potential_location) > 3:  # Avoid very short extractions
                                candidates.append(potential_location)
        
        # Extract location phrases after prepositions
        for prep in self.location_prepositions:
            pattern = rf'\b{prep}\s+([A-Za-z\s,]+?)(?:\.|,|$|\s+(?:and|but|or|so|because))'
            matches = re.findall(pattern, text_clean, re.IGNORECASE)
            for match in matches:
                clean_match = match.strip().rstrip(',.')
                if len(clean_match) > 3:
                    candidates.append(clean_match)
        
        # Remove duplicates and sort by length (longer strings first)
        candidates = list(set(candidates))
        candidates = [c for c in candidates if len(c.strip()) > 2]  # Filter out very short candidates
        candidates.sort(key=len, reverse=True)
        
        return candidates[:8]  # Limit to top 8 candidates
    
    def _extract_city_state_patterns(self, text: str) -> list:
        """Extract city, state patterns specifically."""
        
        candidates = []
        
        # Look for City, State patterns
        city_state_pattern = r'\b([A-Za-z\s]+),\s*([A-Z]{2})\b'
        matches = re.findall(city_state_pattern, text)
        for city, state in matches:
            candidates.append(f"{city.strip()}, {state}")
        
        # Look for just state abbreviations and try to extract nearby city names
        state_pattern = r'\b[A-Z]{2}\b'
        states = re.findall(state_pattern, text)
        for state in states:
            # Look for words before the state that might be city names
            state_context_pattern = rf'\b([A-Za-z\s]+)\s+{state}\b'
            city_matches = re.findall(state_context_pattern, text)
            for city in city_matches:
                city = city.strip()
                if len(city) > 2 and not city.lower() in ['in', 'at', 'near', 'from', 'to']:
                    candidates.append(f"{city}, {state}")
        
        return candidates
    
    def _extract_common_locations(self, text: str) -> list:
        """Extract common location types and landmarks."""
        
        candidates = []
        
        # Look for specific landmark types
        landmark_patterns = [
            r'\b([A-Za-z\s]+(?:Park|School|Hospital|Mall|Center|Plaza|Station|Airport|Bridge|Library|University|College))\b',
            r'\b([A-Za-z\s]+(?:Street|Avenue|Road|Boulevard|Drive|Lane))\b',
            r'\b(downtown|uptown|midtown)\s+([A-Za-z\s]+)\b'
        ]
        
        for pattern in landmark_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if isinstance(matches[0] if matches else None, tuple):
                # Handle tuple matches (from grouped patterns)
                for match_tuple in matches:
                    for match in match_tuple:
                        if match and len(match.strip()) > 3:
                            candidates.append(match.strip())
            else:
                # Handle simple string matches
                candidates.extend([m.strip() for m in matches if len(m.strip()) > 3])
        
        return candidates
    
    async def _geocode_location(self, location_string: str) -> Dict[str, Optional[str]]:
        """
        Geocode a location string to coordinates and address.
        
        Args:
            location_string: String describing a location
            
        Returns:
            Dictionary with geocoding results
        """
        
        if not location_string or len(location_string.strip()) < 2:
            return self._empty_location_result()
        
        location_string = location_string.strip()
        
        try:
            # First try with Nominatim (OpenStreetMap) - most reliable
            print(f"   🌍 Trying Nominatim for: '{location_string}'")
            location = await asyncio.to_thread(
                self.geolocator.geocode, 
                location_string, 
                timeout=10,
                exactly_one=True
            )
            
            if location:
                result = {
                    "latitude": str(location.latitude),
                    "longitude": str(location.longitude),
                    "address": location.address,
                    "confidence": "high"
                }
                print(f"   ✅ Nominatim success: {result}")
                return result
            
            # Add small delay to respect rate limits
            await asyncio.sleep(0.5)
            
            # Fallback to geocoder library with multiple providers
            print(f"   🔄 Trying fallback geocoding for: '{location_string}'")
            return await self._fallback_geocoding(location_string)
            
        except Exception as e:
            print(f"   ❌ Geocoding error for '{location_string}': {str(e)}")
            # Try fallback even if Nominatim fails
            try:
                return await self._fallback_geocoding(location_string)
            except:
                return {
                    "latitude": None,
                    "longitude": None,
                    "address": None,
                    "confidence": "failed",
                    "error": str(e)
                }
    
    async def _fallback_geocoding(self, location_string: str) -> Dict[str, Optional[str]]:
        """Fallback geocoding using geocoder library with correct API."""
        
        providers = [
            ('osm', 'OpenStreetMap'),
            ('arcgis', 'ArcGIS'),
            ('bing', 'Bing Maps'),
            ('google', 'Google Maps')
        ]
        
        for provider_key, provider_name in providers:
            try:
                print(f"   🔄 Trying {provider_name}...")
                
                # Use the correct geocoder API - each provider has its own method
                if provider_key == 'osm':
                    result = await asyncio.to_thread(geocoder.osm, location_string)
                elif provider_key == 'arcgis':
                    result = await asyncio.to_thread(geocoder.arcgis, location_string)
                elif provider_key == 'bing':
                    result = await asyncio.to_thread(geocoder.bing, location_string)
                elif provider_key == 'google':
                    result = await asyncio.to_thread(geocoder.google, location_string)
                else:
                    continue
                
                if result and result.latlng and len(result.latlng) >= 2:
                    geocoded_result = {
                        "latitude": str(result.latlng[0]),
                        "longitude": str(result.latlng[1]),
                        "address": result.address or location_string,
                        "confidence": "medium"
                    }
                    print(f"   ✅ {provider_name} success: {geocoded_result}")
                    return geocoded_result
                else:
                    print(f"   ❌ {provider_name} returned no results")
                    
                # Small delay between providers
                await asyncio.sleep(0.3)
                    
            except Exception as e:
                print(f"   ❌ {provider_name} error: {str(e)}")
                continue
        
        print("   ❌ All fallback providers failed")
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
        coord_patterns = [
            r'(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)',
            r'lat[itude]*\s*[:\s]\s*(-?\d+\.?\d*)\s*,?\s*lon[gitude]*\s*[:\s]\s*(-?\d+\.?\d*)',
            r'(-?\d+\.?\d*)\s*[NS]\s*,?\s*(-?\d+\.?\d*)\s*[EW]'
        ]
        
        for pattern in coord_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    lat, lon = float(match[0]), float(match[1])
                    # Basic validation for reasonable coordinate ranges
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        return (lat, lon)
                except (ValueError, IndexError):
                    continue
        
        return None