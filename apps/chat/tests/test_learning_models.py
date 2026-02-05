import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.chat.models import Module, Lesson, UserLessonProgress, UserModuleProgress

User = get_user_model()


class LearningProgramTestCase(TestCase):
    """Test cases for learning program models and functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='password123',
            email='test@test.com',
            level='A1',
            is_paid=True
        )
        
        self.module = Module.objects.create(
            title="Test Module",
            level="A1",
            module_number=1,
            total_lessons=3,
            estimated_duration_weeks=2
        )
        
        self.lesson = Lesson.objects.create(
            module=self.module,
            lesson_number=1,
            title="Test Lesson",
            grammar_focus="Present Simple"
        )
    
    def test_module_creation(self):
        """Test module is created correctly"""
        self.assertEqual(self.module.title, "Test Module")
        self.assertEqual(self.module.level, "A1")
        self.assertEqual(self.module.module_number, 1)
    
    def test_lesson_creation(self):
        """Test lesson is created correctly"""
        self.assertEqual(self.lesson.title, "Test Lesson")
        self.assertEqual(self.lesson.module, self.module)
        self.assertEqual(self.lesson.lesson_number, 1)
    
    def test_lesson_progress_creation(self):
        """Test lesson progress is created correctly"""
        progress = UserLessonProgress.objects.create(
            user=self.user,
            lesson=self.lesson
        )
        self.assertEqual(progress.status, 'not_started')
        self.assertFalse(progress.theory_completed)
        self.assertFalse(progress.voice_practice_completed)
        self.assertFalse(progress.role_play_completed)
        self.assertFalse(progress.homework_completed)
    
    def test_lesson_progress_mark_complete(self):
        """Test marking lesson components as completed"""
        progress = UserLessonProgress.objects.create(
            user=self.user,
            lesson=self.lesson
        )
        
        # Mark all components as completed
        progress.theory_completed = True
        progress.voice_practice_completed = True
        progress.role_play_completed = True
        progress.homework_completed = True
        progress.status = 'completed'
        progress.save()
        
        # Refresh from database
        progress.refresh_from_db()
        self.assertEqual(progress.status, 'completed')
        self.assertTrue(progress.theory_completed)
    
    def test_lesson_overall_score_calculation(self):
        """Test overall score calculation"""
        progress = UserLessonProgress.objects.create(
            user=self.user,
            lesson=self.lesson
        )
        
        # Set component scores
        progress.voice_practice_score = 8.5
        progress.role_play_score = 7.0
        progress.homework_score = 9.0
        progress.calculate_overall_score()
        
        # Check overall score is average
        expected_score = (8.5 + 7.0 + 9.0) / 3
        self.assertAlmostEqual(progress.overall_score, expected_score, places=2)
    
    def test_module_progress_creation(self):
        """Test module progress is created correctly"""
        progress = UserModuleProgress.objects.create(
            user=self.user,
            module=self.module
        )
        self.assertEqual(progress.status, 'locked')
        self.assertEqual(progress.progress_percentage, 0.0)
    
    def test_module_progress_update(self):
        """Test updating module progress"""
        mod_progress = UserModuleProgress.objects.create(
            user=self.user,
            module=self.module,
            lessons_total=3
        )
        
        # Create and complete a lesson
        lesson_progress = UserLessonProgress.objects.create(
            user=self.user,
            lesson=self.lesson,
            status='completed'
        )
        
        # Update module progress
        mod_progress.update_progress()
        
        self.assertEqual(mod_progress.lessons_completed, 1)
        self.assertAlmostEqual(mod_progress.progress_percentage, 33.33, places=1)
    
    def test_get_next_lesson(self):
        """Test getting next lesson"""
        lesson2 = Lesson.objects.create(
            module=self.module,
            lesson_number=2,
            title="Test Lesson 2"
        )
        
        next_lesson = self.lesson.get_next_lesson()
        self.assertEqual(next_lesson, lesson2)
    
    def test_get_previous_lesson(self):
        """Test getting previous lesson"""
        lesson2 = Lesson.objects.create(
            module=self.module,
            lesson_number=2,
            title="Test Lesson 2"
        )
        
        prev_lesson = lesson2.get_previous_lesson()
        self.assertEqual(prev_lesson, self.lesson)


class ModuleOrderingTestCase(TestCase):
    """Test module and lesson ordering"""
    
    def test_modules_ordered_by_level_and_number(self):
        """Test modules are ordered correctly"""
        # Create modules out of order
        m2 = Module.objects.create(title="M2", level="A2", module_number=1)
        m1 = Module.objects.create(title="M1", level="A1", module_number=1)
        m3 = Module.objects.create(title="M3", level="A1", module_number=2)
        
        modules = Module.objects.all()
        self.assertEqual(modules[0], m1)  # A1, 1
        self.assertEqual(modules[1], m3)  # A1, 2
        self.assertEqual(modules[2], m2)  # A2, 1
