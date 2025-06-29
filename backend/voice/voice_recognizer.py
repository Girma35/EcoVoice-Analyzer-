import whisper
import torch
import tempfile
import os
from typing import Optional
import asyncio

class VoiceRecognizer:
    """
    Audio transcription service using OpenAI Whisper.
    
    Converts WAV audio files to text transcriptions with high accuracy
    and multilingual support.
    """
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize Whisper model.
        
        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
        """
        self.model_size = model_size
        self.model = None
        self.service_name = f"OpenAI Whisper ({model_size})"
        
        # Supported audio formats
        self.supported_formats = ['.wav', '.mp3', '.m4a', '.flac']
        
        # Load model on first use for better startup performance
        self._model_loaded = False
    
    async def transcribe(self, audio_file_path: str) -> str:
        """
        Transcribe audio file to text.
        
        Args:
            audio_file_path: Path to audio file (.wav format)
            
        Returns:
            Transcribed text
            
        Raises:
            FileNotFoundError: If audio file doesn't exist
            ValueError: If audio format is not supported
            RuntimeError: If transcription fails
        """
        
        # Validate file existence
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
        # Validate file format
        file_ext = os.path.splitext(audio_file_path)[1].lower()
        if file_ext not in self.supported_formats:
            raise ValueError(f"Unsupported audio format: {file_ext}. Supported: {self.supported_formats}")
        
        try:
            # Load model if not already loaded
            if not self._model_loaded:
                await self._load_model()
            
            # Perform transcription in thread pool to avoid blocking
            result = await asyncio.to_thread(self._transcribe_sync, audio_file_path)
            
            # Extract text from result
            if isinstance(result, dict) and 'text' in result:
                transcription = result['text'].strip()
            else:
                transcription = str(result).strip()
            
            if not transcription:
                raise RuntimeError("Transcription resulted in empty text")
            
            return transcription
            
        except Exception as e:
            raise RuntimeError(f"Transcription failed: {str(e)}")
    
    async def _load_model(self):
        """Load Whisper model asynchronously."""
        
        try:
            # Check if CUDA is available for GPU acceleration
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            # Load model in thread pool to avoid blocking
            self.model = await asyncio.to_thread(
                whisper.load_model, 
                self.model_size, 
                device=device
            )
            
            self._model_loaded = True
            print(f"Whisper model '{self.model_size}' loaded on {device}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load Whisper model: {str(e)}")
    
    def _transcribe_sync(self, audio_file_path: str) -> dict:
        """
        Synchronous transcription method to be run in thread pool.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Whisper transcription result
        """
        
        try:
            # Configure transcription options
            options = {
                "language": None,  # Auto-detect language
                "task": "transcribe",  # Transcribe (not translate)
                "fp16": torch.cuda.is_available(),  # Use FP16 if GPU available
                "verbose": False
            }
            
            # Perform transcription
            result = self.model.transcribe(audio_file_path, **options)
            
            return result
            
        except Exception as e:
            raise RuntimeError(f"Whisper transcription error: {str(e)}")
    
    def get_service_name(self) -> str:
        """Get the name of the recognition service."""
        return self.service_name
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "service": self.service_name,
            "model_size": self.model_size,
            "model_loaded": self._model_loaded,
            "device": "cuda" if torch.cuda.is_available() else "cpu",
            "supported_formats": self.supported_formats
        }
    
    async def transcribe_with_metadata(self, audio_file_path: str) -> dict:
        """
        Transcribe audio with additional metadata.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Dictionary with transcription, language, and confidence data
        """
        
        try:
            # Load model if not already loaded
            if not self._model_loaded:
                await self._load_model()
            
            # Perform detailed transcription
            result = await asyncio.to_thread(self._transcribe_with_details, audio_file_path)
            
            return {
                "text": result.get("text", "").strip(),
                "language": result.get("language", "unknown"),
                "segments": result.get("segments", []),
                "duration": self._get_audio_duration(audio_file_path),
                "service": self.service_name
            }
            
        except Exception as e:
            raise RuntimeError(f"Detailed transcription failed: {str(e)}")
    
    def _transcribe_with_details(self, audio_file_path: str) -> dict:
        """Synchronous detailed transcription."""
        
        options = {
            "language": None,
            "task": "transcribe",
            "fp16": torch.cuda.is_available(),
            "verbose": True,
            "word_timestamps": True
        }
        
        result = self.model.transcribe(audio_file_path, **options)
        return result
    
    def _get_audio_duration(self, audio_file_path: str) -> Optional[float]:
        """Get audio file duration in seconds."""
        
        try:
            import librosa
            duration = librosa.get_duration(filename=audio_file_path)
            return round(duration, 2)
        except Exception:
            # Fallback - duration not critical for core functionality
            return None
    
    async def health_check(self) -> dict:
        """Check if the voice recognition service is functioning."""
        
        try:
            # Try to load model if not loaded
            if not self._model_loaded:
                await self._load_model()
            
            return {
                "status": "healthy",
                "service": self.service_name,
                "model_loaded": self._model_loaded,
                "gpu_available": torch.cuda.is_available()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "service": self.service_name
            }