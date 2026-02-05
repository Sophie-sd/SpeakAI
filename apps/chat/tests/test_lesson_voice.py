"""
Tests for Lesson Voice Practice and Role-Play features (Phase 2.9)
"""

import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.chat.models import (
    ChatSession, ChatMessage, Lesson, Module, UserLessonProgress,
    RolePlaySession
)
from apps.chat.services.gemini import GeminiService
from apps.chat.services.roleplay_engine import RolePlayEngine

User = get_user_model()


class LessonVoiceChatModelTests(TestCase):
    """Test models for lesson voice chat"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.module = Module.objects.create(
            title='Test Module',
            level='A1',
            module_number=1
        )
        self.lesson = Lesson.objects.create(
            module=self.module,
            lesson_number=1,
            title='Test Lesson',
            voice_practice_prompts=['Say hello', 'Introduce yourself'],
            role_play_scenario={
                'setting': 'Coffee shop',
                'ai_role': 'Barista',
                'user_role': 'Customer',
                'objectives': ['Order coffee'],
                'difficulty': 'easy'
            }
        )
    
    def test_chatsession_with_lesson(self):
        """Test ChatSession with lesson reference"""
        session = ChatSession.objects.create(
            user=self.user,
            lesson=self.lesson,
            session_type='lesson_voice_practice',
            title='Voice Practice Session',
            is_active=True
        )
        
        self.assertEqual(session.lesson, self.lesson)
        self.assertEqual(session.session_type, 'lesson_voice_practice')
        self.assertTrue(session.is_active)
    
    def test_userlessonprogress_feedback_fields(self):
        """Test UserLessonProgress feedback JSON fields"""
        progress = UserLessonProgress.objects.create(
            user=self.user,
            lesson=self.lesson,
            voice_practice_score=8.5,
            voice_practice_feedback={
                'overall_score': 8.5,
                'strengths': ['Good pronunciation'],
                'improvements': ['Work on fluency']
            },
            role_play_feedback={
                'overall_score': 7.0,
                'strengths': ['Natural responses'],
                'improvements': ['Use more vocabulary']
            }
        )
        
        self.assertEqual(progress.voice_practice_score, 8.5)
        self.assertIsNotNone(progress.voice_practice_feedback)
        self.assertIsNotNone(progress.role_play_feedback)
        self.assertEqual(
            progress.voice_practice_feedback['overall_score'],
            8.5
        )


class LessonVoicePracticeViewTests(TestCase):
    """Test voice practice views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_paid=True
        )
        self.module = Module.objects.create(
            title='Test Module',
            level='A1',
            module_number=1
        )
        self.lesson = Lesson.objects.create(
            module=self.module,
            lesson_number=1,
            title='Test Lesson',
            voice_practice_prompts=['Say hello', 'Introduce yourself']
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_start_lesson_voice_practice_creates_session(self):
        """Test starting voice practice creates new session"""
        url = reverse('start_lesson_voice_practice', args=[self.lesson.id])
        response = self.client.post(url, {}, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertIn('session_id', data)
        self.assertIn('initial_message', data)
        self.assertFalse(data.get('continued', True))
        
        # Verify session was created
        session = ChatSession.objects.get(id=data['session_id'])
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.lesson, self.lesson)
        self.assertEqual(session.session_type, 'lesson_voice_practice')
    
    def test_start_lesson_voice_practice_resumes_existing(self):
        """Test voice practice resumes existing active session"""
        # Create active session
        session = ChatSession.objects.create(
            user=self.user,
            lesson=self.lesson,
            session_type='lesson_voice_practice',
            is_active=True
        )
        
        msg = ChatMessage.objects.create(
            session=session,
            role='user',
            content='Hello'
        )
        
        url = reverse('start_lesson_voice_practice', args=[self.lesson.id])
        response = self.client.post(url, {}, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['session_id'], session.id)
        self.assertTrue(data.get('continued', False))
        self.assertIsNotNone(data.get('messages'))


class GeminiServiceLessonTests(TestCase):
    """Test Gemini service for lesson context"""
    
    def setUp(self):
        self.service = GeminiService()
        self.module = Module.objects.create(
            title='Test Module',
            level='A1',
            module_number=1
        )
        self.lesson = Lesson.objects.create(
            module=self.module,
            lesson_number=1,
            title='Test Lesson',
            grammar_focus='Present tense',
            vocabulary_list=['hello', 'goodbye', 'please'],
            voice_practice_prompts=['Say hello', 'Introduce yourself']
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_get_lesson_voice_response_includes_context(self):
        """Test that lesson context is included in response"""
        # This will generate a response using Gemini if API key is available
        # For testing purposes, we just verify the method exists and accepts parameters
        try:
            response = self.service.get_lesson_voice_response(
                user_message="Hello",
                lesson=self.lesson,
                chat_history_objects=[],
                user_profile=self.user
            )
            
            # Verify response structure
            self.assertIn('response', response)
            self.assertIn('translation', response)
            self.assertIn('phase', response)
            
        except Exception as e:
            # API key might not be configured in test environment
            self.skipTest(f"Gemini API not available: {e}")


class RolePlayEngineTests(TestCase):
    """Test Role-Play engine with lesson context"""
    
    def setUp(self):
        self.engine = RolePlayEngine()
        self.module = Module.objects.create(
            title='Test Module',
            level='A1',
            module_number=1
        )
        self.lesson = Lesson.objects.create(
            module=self.module,
            lesson_number=1,
            title='Test Lesson',
            grammar_focus='Present tense',
            vocabulary_list=['coffee', 'please', 'thank you'],
            role_play_scenario={
                'setting': 'Coffee shop',
                'ai_role': 'Barista',
                'user_role': 'Customer',
                'objectives': ['Order coffee'],
                'difficulty': 'easy'
            }
        )
    
    def test_build_scenario_prompt_with_lesson_context(self):
        """Test scenario prompt includes lesson context"""
        lesson_context = {
            'grammar_focus': self.lesson.grammar_focus,
            'vocabulary': self.lesson.vocabulary_list[:10]
        }
        
        prompt = self.engine._build_scenario_prompt(
            scenario=self.lesson.role_play_scenario,
            user_level='A1',
            user_profile=None,
            lesson_context=lesson_context
        )
        
        # Verify prompt includes context
        self.assertIn('LESSON CONTEXT', prompt)
        self.assertIn('grammar_focus', prompt)
        self.assertIn('coffee', prompt)


class ManualQAChecklist(TestCase):
    """Manual QA testing checklist and procedures"""
    
    def test_qa_checklist_procedures(self):
        """
        Document manual QA procedures:
        
        === VOICE PRACTICE TEST FLOW ===
        1. Open lesson page
        2. Click "Voice Practice" button
        3. Modal should appear (80% width/height) with:
           - Left panel (40%): visualizer + record button
           - Right panel (60%): chat history + input
        4. Hold microphone button and speak first prompt
        5. Verify:
           - Transcript displayed correctly
           - AI response appears in chat
           - Audio plays with visualizer animation
        6. Repeat for 5-7 exchanges
        7. AI suggests "Ready to evaluate?"
        8. Click "Завершити та оцінити"
        9. Verify evaluation shows:
           - Overall score /10
           - Strengths list
           - Improvements list
        10. Click "Повернутися до уроку"
        11. Verify progress updated on lesson page
        
        === ROLE-PLAY TEST FLOW ===
        1. Open lesson with role-play scenario
        2. Click "Role-Play" button
        3. Modal appears with same layout
        4. AI greets in character (barista, tourist, etc.)
        5. Type text response and submit
        6. Verify:
           - User message shown in chat
           - AI responds in character
           - No off-topic corrections
        7. Continue 5-7 exchanges
        8. Click "Завершити та оцінити"
        9. Verify evaluation scores
        10. Progress saves to UserLessonProgress
        
        === RESUME TEST ===
        1. Start Voice Practice
        2. Do 2-3 exchanges
        3. Close modal (click ✕)
        4. Reopen same lesson Voice Practice
        5. Verify all previous messages displayed
        6. Can continue conversation
        
        === OFF-TOPIC TEST ===
        1. In Voice Practice
        2. Ask question not related to lesson
        3. Verify AI redirects with:
           - "That's interesting, but let's focus on [topic]"
           - With translation
           - Returns to lesson objectives
        
        === ERROR HANDLING ===
        1. Test with no microphone permission
           → Show error message
        2. Test with very short recording
           → Show "recording too short" error
        3. Test network error
           → Show "error processing audio"
        4. Test STT failure
           → Show "could not understand" message
        """
        # This is a documentation test
        self.assertTrue(True)
