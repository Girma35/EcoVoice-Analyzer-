import cohere
import os
import json
from typing import Dict, Any

class PollutionAnalyzerLLM:
    """
    AI-powered pollution analyzer using Cohere LLM.
    
    Classifies pollution types, generates cleanup recommendations,
    and identifies responsible agencies based on text descriptions.
    """
    
    def __init__(self):
        """Initialize Cohere client with API key from environment."""
        self.api_key = os.getenv("COHERE_API_KEY")
        if not self.api_key:
            raise ValueError("COHERE_API_KEY environment variable is required")
        
        self.client = cohere.Client(self.api_key)
        
        # Pollution type categories
        self.pollution_types = [
            "air pollution", "water pollution", "soil pollution", 
            "noise pollution", "oil spill", "chemical spill",
            "waste dumping", "sewage overflow", "industrial emission",
            "plastic pollution", "radioactive contamination"
        ]
        
        # Government agencies by pollution type
        self.agencies_map = {
            "air pollution": "Environmental Protection Agency (EPA)",
            "water pollution": "EPA Water Quality Division",
            "oil spill": "Coast Guard and EPA",
            "chemical spill": "EPA Emergency Response Team",
            "waste dumping": "Local Environmental Health Department",
            "sewage overflow": "Municipal Water Authority",
            "industrial emission": "EPA Air Quality Management",
            "noise pollution": "Local Environmental Control Board",
            "soil pollution": "EPA Superfund Division",
            "plastic pollution": "EPA Waste Management Division",
            "radioactive contamination": "Nuclear Regulatory Commission (NRC)"
        }
    
    async def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze pollution description and generate comprehensive response.
        
        Args:
            text: Transcribed text describing pollution incident
            
        Returns:
            Dictionary containing pollution type, recommendation, responsible agency, and raw response
        """
        
        # Construct analysis prompt
        prompt = self._build_analysis_prompt(text)
        
        try:
            # Generate response using Cohere
            response = self.client.generate(
                model='command',
                prompt=prompt,
                max_tokens=800,
                temperature=0.3,
                k=0,
                stop_sequences=[],
                return_likelihoods='NONE'
            )
            
            # Parse the structured response
            parsed_response = self._parse_response(response.generations[0].text)
            
            # Add raw response for debugging/audit purposes
            parsed_response["raw_response"] = {
                "text": response.generations[0].text,
                "meta": {
                    "api_version": response.meta.api_version if hasattr(response, 'meta') else None,
                    "model": "command"
                }
            }
            
            return parsed_response
            
        except Exception as e:
            # Fallback response in case of API failure
            return self._generate_fallback_response(text, str(e))
    
    def _build_analysis_prompt(self, text: str) -> str:
        """Build structured prompt for pollution analysis."""
        
        return f"""
You are an expert environmental analyst. Analyze the following pollution report and provide a structured response.

POLLUTION REPORT:
{text}

Please analyze this report and respond in the following JSON format:

{{
    "pollution_type": "specific pollution category from: {', '.join(self.pollution_types)}",
    "recommendation": "detailed cleanup and mitigation steps (2-3 sentences)",
    "responsible_agency": "appropriate government agency or department",
    "severity_level": "low/medium/high/critical",
    "immediate_actions": "urgent steps to take (1-2 sentences)",
    "long_term_solution": "preventive measures and long-term remediation"
}}

Focus on:
1. Accurate pollution type classification
2. Practical, actionable recommendations
3. Correct agency identification
4. Public safety considerations

Response:
"""
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate Cohere response."""
        
        try:
            # Try to extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                parsed = json.loads(json_str)
                
                # Validate required fields
                pollution_type = parsed.get("pollution_type", "unknown pollution")
                recommendation = parsed.get("recommendation", "Contact local environmental authorities for assessment.")
                
                # Determine responsible agency
                responsible_agency = self._get_responsible_agency(pollution_type)
                
                return {
                    "pollution_type": pollution_type,
                    "recommendation": recommendation,
                    "responsible_agency": responsible_agency,
                    "severity_level": parsed.get("severity_level", "medium"),
                    "immediate_actions": parsed.get("immediate_actions", "Secure the area and report to authorities."),
                    "long_term_solution": parsed.get("long_term_solution", "Regular monitoring and compliance checks.")
                }
            
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback parsing if JSON extraction fails
            return self._extract_from_text(response_text)
        
        # Last resort fallback
        return self._generate_default_response()
    
    def _get_responsible_agency(self, pollution_type: str) -> str:
        """Determine responsible agency based on pollution type."""
        
        # Direct match
        if pollution_type in self.agencies_map:
            return self.agencies_map[pollution_type]
        
        # Partial match for compound pollution types
        for key, agency in self.agencies_map.items():
            if key in pollution_type.lower():
                return agency
        
        # Default agency
        return "Environmental Protection Agency (EPA)"
    
    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """Extract information from unstructured response text."""
        
        pollution_type = "environmental contamination"
        
        # Simple keyword matching for pollution type
        text_lower = text.lower()
        for p_type in self.pollution_types:
            if p_type in text_lower:
                pollution_type = p_type
                break
        
        return {
            "pollution_type": pollution_type,
            "recommendation": "Contact environmental authorities for proper assessment and cleanup procedures.",
            "responsible_agency": self._get_responsible_agency(pollution_type),
            "severity_level": "medium",
            "immediate_actions": "Secure the area and report to local authorities.",
            "long_term_solution": "Conduct environmental impact assessment and implement remediation plan."
        }
    
    def _generate_fallback_response(self, text: str, error: str) -> Dict[str, Any]:
        """Generate fallback response when API fails."""
        
        return {
            "pollution_type": "environmental incident",
            "recommendation": "Unable to analyze pollution type due to service error. Contact local environmental authorities immediately.",
            "responsible_agency": "Environmental Protection Agency (EPA)",
            "severity_level": "unknown",
            "immediate_actions": "Report to authorities and secure the area.",
            "long_term_solution": "Follow up with environmental assessment once service is restored.",
            "raw_response": {"error": error, "fallback": True}
        }
    
    def _generate_default_response(self) -> Dict[str, Any]:
        """Generate default response structure."""
        
        return {
            "pollution_type": "unspecified pollution",
            "recommendation": "Contact environmental authorities for assessment and appropriate action.",
            "responsible_agency": "Environmental Protection Agency (EPA)",
            "severity_level": "medium",
            "immediate_actions": "Report incident and secure affected area.",
            "long_term_solution": "Conduct environmental impact assessment."
        }