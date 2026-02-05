"""
Tests for chat views
"""
from unittest.mock import patch, Mock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.chat.models import Module, Lesson, UserLessonProgress, RolePlaySession

User = get_user_model()


class HomeworkCheckViewTestCase(TestCase):
    """Test check_homework view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create user
        self.user = User.objects.create_user(
            username='testuser',
            password='password123',
            email='test@test.com',
            level='A1',
            is_paid=True,
            onboarding_completed=True
        )
        
        # Create lesson
        self.module = Module.objects.create(
            title="Test Module",
            level="A1",
            module_number=1,
            total_lessons=1
        )
        
        self.lesson = Lesson.objects.create(
            module=self.module,
            lesson_number=1,
            title="Test Lesson",
            grammar_focus="Present Simple",
            homework_description="Write a text",
            homework_instructions={
                'criteria': {
                    'grammar': {'weight': 50, 'description': 'Граматика'},
                    'vocabulary': {'weight': 50, 'description': 'Словник'}
                },
                'min_passing_score': 6.0,
                'feedback_language': 'ukrainian',
                'focus_areas': ['accuracy']
            }
        )
        
        self.client.login(username='testuser', password='password123')
    
    @patch('apps.chat.views.GeminiService')
    def test_check_homework_success(self, mock_service):
        """Test successful homework check"""
        # Mock the service
        mock_instance = Mock()
        mock_instance.evaluate_homework.return_value = {
            'score': 8.0,
            'feedback': 'Good job',
            'errors': [],
            'strengths': ['Clear writing']
        }
        mock_service.return_value = mock_instance
        
        response = self.client.post(
            reverse('check_homework', args=[self.lesson.id]),
            data={'homework': 'My homework text'},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('score', data)
    
    def test_check_homework_no_text(self):
        """Test homework check without text"""
        response = self.client.post(
            reverse('check_homework', args=[self.lesson.id]),
            data={},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_check_homework_unauthorized(self):
        """Test homework check without authentication"""
        self.client.logout()
        
        response = self.client.post(
            reverse('check_homework', args=[self.lesson.id]),
            data={'homework': 'Test'},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 302)  # Redirect to login


class CompleteLessonComponentViewTestCase(TestCase):
    """Test complete_lesson_component view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='testuser',
            password='password123',
            email='test@test.com',
            level='A1',
            is_paid=True,
            onboarding_completed=True
        )
        
        self.module = Module.objects.create(
            title="Test Module",
            level="A1",
            module_number=1,
            total_lessons=1
        )
        
        self.lesson = Lesson.objects.create(
            module=self.module,
            lesson_number=1,
            title="Test Lesson"
        )
        
        self.progress = UserLessonProgress.objects.create(
            user=self.user,
            lesson=self.lesson
        )
        
        self.client.login(username='testuser', password='password123')
    
    def test_complete_theory_component(self):
        """Test completing theory component"""
        response = self.client.post(
            reverse('complete_lesson_component', args=[self.lesson.id]),
            data={'component': 'theory'}
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Refresh progress
        self.progress.refresh_from_db()
        self.assertTrue(self.progress.theory_completed)
    
    def test_complete_voice_practice_with_score(self):
        """Test completing voice practice with score"""
        response = self.client.post(
            reverse('complete_lesson_component', args=[self.lesson.id]),
            data={
                'component': 'voice_practice',
                'score': '8.5'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Refresh progress
        self.progress.refresh_from_db()
        self.assertTrue(self.progress.voice_practice_completed)
        self.assertEqual(self.progress.voice_practice_score, 8.5)
    
    def test_complete_invalid_component(self):
        """Test completing with invalid component name"""
        response = self.client.post(
            reverse('complete_lesson_component', args=[self.lesson.id]),
            data={'component': 'invalid'}
        )
        
        # Should still return 200 but not update anything
        self.assertEqual(response.status_code, 200)


class RolePlayViewsTestCase(TestCase):
    """Test role-play views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='testuser',
            password='password123',
            email='test@test.com',
            level='A1',
            is_paid=True,
            onboarding_completed=True
        )
        
        self.module = Module.objects.create(
            title="Test Module",
            level="A1",
            module_number=1,
            total_lessons=1
        )
        
        self.lesson = Lesson.objects.create(
            module=self.module,
            lesson_number=1,
            title="Test Lesson",
            role_play_scenario_name="Coffee Shop",
            role_play_scenario={
                'setting': 'Coffee Shop',
                'ai_role': 'Barista',
                'user_role': 'Customer',
                'objectives': ['Order coffee'],
                'difficulty': 'easy',
                'system_prompt': 'You are a barista'
            }
        )
        
        self.client.login(username='testuser', password='password123')
    
    @patch('apps.chat.views.RolePlayEngine')
    def test_start_role_play_success(self, mock_engine):
        """Test starting role-play successfully"""
        # Mock the engine
        mock_instance = Mock()
        mock_instance.start_scenario.return_value = {
            'ai_message': 'Hello! What can I get you?',
            'success': True,
            'scenario_name': 'Coffee Shop'
        }
        mock_engine.return_value = mock_instance
        
        response = self.client.post(
            reverse('start_role_play', args=[self.lesson.id])
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('ai_message', data)
        # Check session_id is present
        self.assertIn('session_id', data)
    
    def test_start_role_play_unauthorized(self):
        """Test starting role-play without authentication"""
        self.client.logout()
        
        response = self.client.post(
            reverse('start_role_play', args=[self.lesson.id])
        )
        
        self.assertEqual(response.status_code, 302)  # Redirect to login
