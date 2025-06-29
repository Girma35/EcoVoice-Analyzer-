from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import tempfile
import os
from dotenv import load_dotenv
import asyncio
from typing import Optional

from classification.classify import PollutionAnalyzerLLM
from location.extractor import LocationExtractor
from voice.voice_recognizer import VoiceRecognizer
from LangChainHelper.langchain_helper import LangChainHelper

# Load environment variables
load_dotenv()

app = FastAPI(title="AI Pollution Analyzer", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
voice_recognizer = VoiceRecognizer()
pollution_analyzer = PollutionAnalyzerLLM()
location_extractor = LocationExtractor()
langchain_helper = LangChainHelper()

class AnalysisResponse(BaseModel):
    transcription: str
    recognition_service: str
    location: dict
    pollution_type: str
    recommendation: str
    responsible_agency: str
    raw_cohere_response: dict

class QueryResponse(BaseModel):
    query: str
    sql_query: str
    result: list

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_audio(file: UploadFile = File(...)):
    """
    Analyze uploaded audio file for pollution reporting.
    
    Accepts .wav audio files and returns comprehensive analysis including:
    - Audio transcription
    - Location extraction
    - Pollution type classification
    - Cleanup recommendations
    - Responsible agency identification
    """
    
    # Validate file type
    if not file.filename.endswith('.wav'):
        raise HTTPException(status_code=400, detail="Only .wav files are supported")
    
    # Create temporary file for audio processing
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
        try:
            # Save uploaded file to temporary location
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            
            # Step 1: Transcribe audio to text
            transcription = await voice_recognizer.transcribe(temp_file.name)
            recognition_service = voice_recognizer.get_service_name()
            
            # Step 2: Extract location information from transcription
            location_info = await location_extractor.extract_location(transcription)
            
            # Step 3: Analyze pollution type and generate recommendations
            pollution_analysis = await pollution_analyzer.analyze(transcription)
            
            # Step 4: Assemble response data
            analysis_data = {
                "transcription": transcription,
                "recognition_service": recognition_service,
                "location": location_info,
                "pollution_type": pollution_analysis["pollution_type"],
                "recommendation": pollution_analysis["recommendation"],
                "responsible_agency": pollution_analysis["responsible_agency"],
                "raw_cohere_response": pollution_analysis["raw_response"]
            }
            
            # Step 5: Store data in database
            await langchain_helper.add_to_db(analysis_data)
            
            return AnalysisResponse(**analysis_data)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

@app.get("/ask", response_model=QueryResponse)
async def ask_question(q: str = Query(..., description="Natural language question to query the database")):
    """
    Ask natural language questions about stored pollution data.
    
    Converts natural language queries to SQL and returns results from the database.
    """
    
    try:
        # Convert natural language to SQL and execute query
        sql_query, result = await langchain_helper.query(q)
        
        return QueryResponse(
            query=q,
            sql_query=sql_query,
            result=result
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring service status."""
    return {
        "status": "healthy",
        "service": "AI Pollution Analyzer API",
        "version": "1.0.0"
    }

@app.on_event("startup")
async def startup_event():
    """Initialize database and other startup tasks."""
    await langchain_helper.initialize_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)