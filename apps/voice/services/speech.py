"""
Speech-to-Text and Text-to-Speech service using Google Cloud APIs
"""
import os
import io
import logging
from django.conf import settings
from google.cloud import speech_v1
from google.cloud import texttospeech
from google.api_core.client_options import ClientOptions

logger = logging.getLogger(__name__)


class SpeechService:
    """Service for STT and TTS operations"""
    
    def __init__(self):
        self.speech_client = None
        self.tts_client = None
        self._init_clients()
    
    def _init_clients(self):
        """Initialize Google Cloud clients"""
        try:
            client_options = None
            api_key = getattr(settings, 'GOOGLE_CLOUD_API_KEY', None)
            
            if api_key:
                logger.info("Initializing Google Cloud clients with API Key")
                client_options = ClientOptions(api_key=api_key)
                
                # If using API key, we should explicitly pass credentials=None 
                # to prevent the client from trying to load default credentials 
                # from GOOGLE_APPLICATION_CREDENTIALS environment variable.
                self.speech_client = speech_v1.SpeechClient(
                    client_options=client_options, 
                    credentials=None
                )
                self.tts_client = texttospeech.TextToSpeechClient(
                    client_options=client_options, 
                    credentials=None
                )
            else:
                # Fallback to default credentials (JSON file)
                self.speech_client = speech_v1.SpeechClient()
                self.tts_client = texttospeech.TextToSpeechClient()
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud clients: {e}")
            self.speech_client = None
            self.tts_client = None
    
    def transcribe_audio(self, audio_blob, language_code='en-US') -> str:
        """
        Convert audio blob to text using Google Cloud Speech-to-Text
        Supports both English and Ukrainian simultaneously.
        """
        if not self.speech_client:
            logger.error("Speech client not initialized")
            return "Error: Speech service not available"
        
        try:
            if hasattr(audio_blob, 'read'):
                audio_data = audio_blob.read()
            else:
                audio_data = audio_blob
            
            audio = speech_v1.RecognitionAudio(content=audio_data)
            
            # Use multi-language recognition
            config = speech_v1.RecognitionConfig(
                encoding=speech_v1.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                language_code=language_code,
                alternative_language_codes=['uk-UA'], # Add Ukrainian support for simultaneous recognition
                model="latest_long", # Use better model if available
                enable_automatic_punctuation=True,
            )
            
            # Call API
            response = self.speech_client.recognize(config=config, audio=audio)
            
            # Extract transcript
            transcript = ""
            for result in response.results:
                if result.alternatives:
                    # The first alternative is usually the most accurate
                    transcript += result.alternatives[0].transcript
            
            return transcript.strip() or "No speech detected"
        
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return f"Error: {str(e)}"
    
    def synthesize_speech(self, text, language_code='en-US', voice_name=None, force_english=True) -> bytes:
        """
        Convert text to speech using Google Cloud Text-to-Speech
        
        Args:
            text: Text to synthesize
            language_code: Language code (default: 'en-US')
            voice_name: Specific voice name to use
            force_english: If True (default), always use English voice for AI responses.
                          This ensures consistent, high-quality audio and proper pronunciation.
                          Cyrillic detection is disabled for AI responses to maintain clean English output.
        """
        if not self.tts_client:
            logger.error("TTS client not initialized")
            return b""
        
        try:
            # For AI responses, always use English voice (force_english=True)
            # This ensures:
            # 1. Consistent English pronunciation
            # 2. Clean audio output without mixing languages
            # 3. Better student learning experience
            if force_english:
                target_language = 'en-US'
                target_voice = voice_name or 'en-US-Neural2-F'
            else:
                # Optional: Detect language only when force_english=False
                # This is for potential future use cases (e.g., Ukrainian explanations)
                has_cyrillic = any('\u0400' <= char <= '\u04FF' for char in text)
                
                if has_cyrillic:
                    target_language = 'uk-UA'
                    target_voice = voice_name or 'uk-UA-Wavenet-A'
                else:
                    target_language = language_code
                    target_voice = voice_name or 'en-US-Neural2-F'
            
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            voice = texttospeech.VoiceSelectionParams(
                language_code=target_language,
                name=target_voice,
            )
            
            # Select audio encoding
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,
                pitch=0.0,
            )
            
            # Call API
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )
            
            return response.audio_content
        
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return b""
    
    def save_audio_file(self, audio_bytes, filename='output.mp3', folder='audio') -> str:
        """
        Save audio bytes to temporary file or cloud storage
        
        Args:
            audio_bytes: Audio content bytes
            filename: Output filename
            folder: Storage folder
        
        Returns:
            File path or URL
        """
        try:
            # For now, save to temporary media folder
            media_path = os.path.join(settings.MEDIA_ROOT, folder)
            os.makedirs(media_path, exist_ok=True)
            
            file_path = os.path.join(media_path, filename)
            with open(file_path, 'wb') as f:
                f.write(audio_bytes)
            
            # Return URL path
            return f"{settings.MEDIA_URL}{folder}/{filename}"
        
        except Exception as e:
            logger.error(f"Error saving audio file: {e}")
            return ""
