"""
Pronunciation Scoring Service
Використовує Google Cloud Speech-to-Text для оцінки вимови
"""
from google.cloud import speech_v1
from google.api_core.client_options import ClientOptions
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class PronunciationScorer:
    """Сервіс для оцінки вимови"""
    
    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Ініціалізувати Google Speech клієнт"""
        try:
            api_key = getattr(settings, 'GOOGLE_CLOUD_API_KEY', None)
            if api_key:
                client_options = ClientOptions(api_key=api_key)
                self.client = speech_v1.SpeechClient(
                    client_options=client_options,
                    credentials=None
                )
            else:
                self.client = speech_v1.SpeechClient()
        except Exception as e:
            logger.error(f"Failed to initialize pronunciation scorer: {e}")
    
    def score_pronunciation(
        self,
        audio_data: bytes,
        target_text: str,
        language_code: str = 'en-US'
    ) -> dict:
        """
        Оцінити вимову користувача
        
        Args:
            audio_data: Аудіо дані
            target_text: Цільовий текст що має бути вимовлений
            language_code: Код мови
        
        Returns:
            Dict з оцінками вимови
        """
        if not self.client:
            logger.error("Pronunciation scorer not initialized")
            return self._default_score()
        
        try:
            # Конфігурація з фокусом на вимову
            config = speech_v1.RecognitionConfig(
                encoding=speech_v1.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                language_code=language_code,
                model="latest_long",
                enable_automatic_punctuation=True,
                # Додаткові фічі для аналізу вимови
                use_enhanced=True,
            )
            
            audio = speech_v1.RecognitionAudio(content=audio_data)
            
            # Розпізнавання
            response = self.client.recognize(config=config, audio=audio)
            
            if not response.results:
                return {
                    'pronunciation_score': 0.0,
                    'transcribed_text': '',
                    'accuracy_score': 0.0,
                    'fluency_score': 0.0,
                    'feedback': 'No speech detected. Please try again.'
                }
            
            # Отримати transcript
            result = response.results[0]
            transcribed_text = result.alternatives[0].transcript
            confidence = result.alternatives[0].confidence
            
            # Порівняти з цільовим текстом
            accuracy = self._calculate_accuracy(target_text, transcribed_text)
            
            # Оцінити плавність (на основі confidence)
            fluency = confidence * 100
            
            # Загальна оцінка вимови
            pronunciation_score = (accuracy + fluency) / 2
            
            # Детальний аналіз помилок
            word_analysis = self._analyze_words(target_text, transcribed_text)
            
            return {
                'pronunciation_score': round(pronunciation_score, 1),
                'transcribed_text': transcribed_text,
                'accuracy_score': round(accuracy, 1),
                'fluency_score': round(fluency, 1),
                'confidence': round(confidence * 100, 1),
                'word_analysis': word_analysis,
                'feedback': self._generate_feedback(
                    pronunciation_score, 
                    accuracy, 
                    fluency
                )
            }
        
        except Exception as e:
            logger.error(f"Error scoring pronunciation: {e}")
            return self._default_score()
    
    def _calculate_accuracy(self, target: str, transcribed: str) -> float:
        """
        Розрахувати точність вимови (порівняння слів)
        """
        target_words = target.lower().split()
        transcribed_words = transcribed.lower().split()
        
        if not target_words:
            return 0.0
        
        # Проста метрика: скільки слів збігається
        matches = sum(1 for tw in target_words if tw in transcribed_words)
        accuracy = (matches / len(target_words)) * 100
        
        return accuracy
    
    def _analyze_words(self, target: str, transcribed: str) -> list:
        """Аналіз помилок по словах"""
        target_words = target.lower().split()
        transcribed_words = transcribed.lower().split()
        
        analysis = []
        for i, target_word in enumerate(target_words):
            if i < len(transcribed_words):
                transcribed_word = transcribed_words[i]
                is_correct = target_word == transcribed_word
                analysis.append({
                    'target': target_word,
                    'pronounced': transcribed_word,
                    'correct': is_correct
                })
            else:
                analysis.append({
                    'target': target_word,
                    'pronounced': None,
                    'correct': False
                })
        
        return analysis
    
    def _generate_feedback(
        self, 
        pronunciation_score: float, 
        accuracy: float, 
        fluency: float
    ) -> str:
        """Генерувати текстовий фідбек"""
        if pronunciation_score >= 90:
            return "Excellent pronunciation! Native-like quality."
        elif pronunciation_score >= 75:
            return "Very good! Minor improvements needed."
        elif pronunciation_score >= 60:
            return "Good effort. Work on clarity and accuracy."
        elif pronunciation_score >= 40:
            return "Keep practicing! Focus on individual sounds."
        else:
            return "Need more practice. Speak slowly and clearly."
    
    def _default_score(self) -> dict:
        """Дефолтна оцінка при помилці"""
        return {
            'pronunciation_score': 50.0,
            'transcribed_text': '',
            'accuracy_score': 50.0,
            'fluency_score': 50.0,
            'confidence': 50.0,
            'word_analysis': [],
            'feedback': 'Unable to score pronunciation. Please try again.'
        }
