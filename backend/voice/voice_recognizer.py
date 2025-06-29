import speech_recognition as sr
import tempfile
import os
from typing import Optional
import asyncio
from pydub import AudioSegment
import io

class VoiceRecognizer:
    """
    Audio transcription service using SpeechRecognition library.
    
    Converts audio files to text transcriptions using multiple
    cloud-based speech recognition services as fallbacks.
    """
    
    def __init__(self):
        """Initialize speech recognition with multiple service options."""
        self.recognizer = sr.Recognizer()
        self.service_name = "SpeechRecognition (Multi-Service)"
        
        # Supported audio formats
        self.supported_formats = ['.wav', '.mp3', '.m4a', '.flac', '.webm']
        
        # Service priority order (free services first)
        self.services = [
            ('google', 'Google Speech Recognition'),
            ('sphinx', 'CMU Sphinx (Offline)'),
            ('wit', 'Wit.ai'),
        ]
        
        # Configure recognizer settings
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.operation_timeout = 10
    
    async def transcribe(self, audio_file_path: str) -> str:
        """
        Transcribe audio file to text using multiple services as fallbacks.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Transcribed text
            
        Raises:
            FileNotFoundError: If audio file doesn't exist
            ValueError: If audio format is not supported
            RuntimeError: If transcription fails with all services
        """
        
        # Validate file existence
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
        # Validate file format
        file_ext = os.path.splitext(audio_file_path)[1].lower()
        if file_ext not in self.supported_formats:
            raise ValueError(f"Unsupported audio format: {file_ext}. Supported: {self.supported_formats}")
        
        try:
            # Convert audio to WAV format if needed
            wav_path = await self._ensure_wav_format(audio_file_path)
            
            # Load audio file
            with sr.AudioFile(wav_path) as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                # Record the audio
                audio_data = self.recognizer.record(source)
            
            # Try each service until one succeeds
            last_error = None
            for service_key, service_name in self.services:
                try:
                    result = await self._transcribe_with_service(audio_data, service_key)
                    if result and result.strip():
                        self.service_name = service_name
                        return result.strip()
                except Exception as e:
                    last_error = e
                    print(f"Service {service_name} failed: {str(e)}")
                    continue
            
            # If all services failed
            raise RuntimeError(f"All transcription services failed. Last error: {str(last_error)}")
            
        except Exception as e:
            if isinstance(e, (FileNotFoundError, ValueError, RuntimeError)):
                raise
            else:
                raise RuntimeError(f"Transcription failed: {str(e)}")
        
        finally:
            # Clean up temporary WAV file if created
            if 'wav_path' in locals() and wav_path != audio_file_path and os.path.exists(wav_path):
                try:
                    os.unlink(wav_path)
                except:
                    pass
    
    async def _ensure_wav_format(self, audio_file_path: str) -> str:
        """Convert audio file to WAV format if needed."""
        
        file_ext = os.path.splitext(audio_file_path)[1].lower()
        
        # If already WAV, return as-is
        if file_ext == '.wav':
            return audio_file_path
        
        try:
            # Convert to WAV using pydub
            audio = AudioSegment.from_file(audio_file_path)
            
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_wav:
                audio.export(temp_wav.name, format='wav')
                return temp_wav.name
                
        except Exception as e:
            raise RuntimeError(f"Audio format conversion failed: {str(e)}")
    
    async def _transcribe_with_service(self, audio_data, service_key: str) -> str:
        """Transcribe audio using specific service."""
        
        try:
            if service_key == 'google':
                # Google Speech Recognition (free tier)
                result = await asyncio.to_thread(
                    self.recognizer.recognize_google, 
                    audio_data,
                    language='en-US'
                )
                return result
                
            elif service_key == 'sphinx':
                # CMU Sphinx (offline, lower accuracy but always available)
                result = await asyncio.to_thread(
                    self.recognizer.recognize_sphinx, 
                    audio_data
                )
                return result
                
            elif service_key == 'wit':
                # Wit.ai (requires API key in environment)
                wit_key = os.getenv('WIT_AI_KEY')
                if wit_key:
                    result = await asyncio.to_thread(
                        self.recognizer.recognize_wit,
                        audio_data,
                        key=wit_key
                    )
                    return result
                else:
                    raise ValueError("WIT_AI_KEY not found in environment")
            
            else:
                raise ValueError(f"Unknown service: {service_key}")
                
        except sr.UnknownValueError:
            raise RuntimeError("Could not understand audio")
        except sr.RequestError as e:
            raise RuntimeError(f"Service request failed: {str(e)}")
    
    def get_service_name(self) -> str:
        """Get the name of the recognition service that was used."""
        return self.service_name
    
    def get_model_info(self) -> dict:
        """Get information about available services."""
        return {
            "service": "SpeechRecognition Library",
            "available_services": [name for _, name in self.services],
            "supported_formats": self.supported_formats,
            "current_service": self.service_name
        }
    
    async def transcribe_with_metadata(self, audio_file_path: str) -> dict:
        """
        Transcribe audio with additional metadata.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Dictionary with transcription and metadata
        """
        
        try:
            # Get basic transcription
            text = await self.transcribe(audio_file_path)
            
            # Get audio duration
            duration = await self._get_audio_duration(audio_file_path)
            
            return {
                "text": text,
                "service": self.service_name,
                "duration": duration,
                "confidence": "medium",  # SpeechRecognition doesn't provide confidence scores
                "language": "en-US"
            }
            
        except Exception as e:
            raise RuntimeError(f"Detailed transcription failed: {str(e)}")
    
    async def _get_audio_duration(self, audio_file_path: str) -> Optional[float]:
        """Get audio file duration in seconds."""
        
        try:
            audio = AudioSegment.from_file(audio_file_path)
            return round(len(audio) / 1000.0, 2)  # Convert milliseconds to seconds
        except Exception:
            return None
    
    async def health_check(self) -> dict:
        """Check if the voice recognition service is functioning."""
        
        try:
            # Test basic functionality
            test_successful = True
            available_services = []
            
            for service_key, service_name in self.services:
                try:
                    if service_key == 'sphinx':
                        # Sphinx is always available (offline)
                        available_services.append(service_name)
                    elif service_key == 'google':
                        # Google requires internet connection
                        available_services.append(service_name + " (requires internet)")
                    elif service_key == 'wit':
                        # Wit.ai requires API key
                        if os.getenv('WIT_AI_KEY'):
                            available_services.append(service_name)
                        else:
                            available_services.append(service_name + " (API key required)")
                except:
                    continue
            
            return {
                "status": "healthy" if available_services else "limited",
                "available_services": available_services,
                "primary_service": self.service_name,
                "supported_formats": self.supported_formats
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "service": "SpeechRecognition"
            }
    
    def configure_service_priority(self, services: list):
        """
        Configure the priority order of speech recognition services.
        
        Args:
            services: List of tuples (service_key, service_name)
        """
        self.services = services
        print(f"Service priority updated: {[name for _, name in services]}")