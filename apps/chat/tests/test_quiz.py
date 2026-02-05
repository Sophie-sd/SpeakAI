"""
Tests for Quiz system
"""
from unittest.mock import patch, Mock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.chat.models import Module, Lesson, Quiz, Question, QuizAttempt, QuestionResponse
from apps.chat.services.quiz_engine import QuizEngine

User = get_user_model()


class QuizModelTestCase(TestCase):
    """Test Quiz models"""
    
    def setUp(self):
        """Set up test data"""
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
            grammar_focus="Present Simple"
        )
        
        self.quiz = Quiz.objects.create(
            lesson=self.lesson,
            title="Test Quiz",
            passing_score=6.0,
            time_limit_minutes=10
        )
        
        self.question = Question.objects.create(
            quiz=self.quiz,
            question_type='multiple_choice',
            question_text="What is 2+2?",
            options={
                'choices': [
                    {'id': 'a', 'text': '3'},
                    {'id': 'b', 'text': '4'},
                    {'id': 'c', 'text': '5'}
                ]
            },
            correct_answer={'answer': 'b'},
            points=1.0,
            explanation="2+2=4",
            order=1
        )
    
    def test_quiz_creation(self):
        """Test quiz is created correctly"""
        self.assertEqual(self.quiz.title, "Test Quiz")
        self.assertEqual(self.quiz.lesson, self.lesson)
        self.assertEqual(self.quiz.passing_score, 6.0)
    
    def test_question_creation(self):
        """Test question is created correctly"""
        self.assertEqual(self.question.quiz, self.quiz)
        self.assertEqual(self.question.question_type, 'multiple_choice')
        self.assertEqual(self.question.points, 1.0)
    
    def test_question_check_answer_correct(self):
        """Test checking correct answer"""
        user_answer = {'answer': 'b'}
        is_correct, points = self.question.check_answer(user_answer)
        self.assertTrue(is_correct)
        self.assertEqual(points, 1.0)
    
    def test_question_check_answer_incorrect(self):
        """Test checking incorrect answer"""
        user_answer = {'answer': 'a'}
        is_correct, points = self.question.check_answer(user_answer)
        self.assertFalse(is_correct)
        self.assertEqual(points, 0.0)
    
    def test_quiz_total_points(self):
        """Test quiz total points calculation"""
        # Add another question
        Question.objects.create(
            quiz=self.quiz,
            question_type='true_false',
            question_text="True or False?",
            options={},
            correct_answer={'answer': True},
            points=2.0,
            order=2
        )
        
        # Should be 3.0 (1.0 + 2.0)
        self.assertEqual(self.quiz.total_points, 3.0)


class QuizEngineTestCase(TestCase):
    """Test QuizEngine"""
    
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
            total_lessons=1
        )
        
        self.lesson = Lesson.objects.create(
            module=self.module,
            lesson_number=1,
            title="Test Lesson"
        )
        
        self.quiz = Quiz.objects.create(
            lesson=self.lesson,
            title="Test Quiz",
            passing_score=6.0
        )
        
        self.question1 = Question.objects.create(
            quiz=self.quiz,
            question_type='multiple_choice',
            question_text="Question 1",
            options={'choices': [{'id': 'a', 'text': 'Answer A'}, {'id': 'b', 'text': 'Answer B'}]},
            correct_answer={'answer': 'b'},
            points=5.0,
            order=1
        )
        
        self.question2 = Question.objects.create(
            quiz=self.quiz,
            question_type='true_false',
            question_text="Question 2",
            options={},
            correct_answer={'answer': True},
            points=5.0,
            order=2
        )
    
    def test_start_quiz(self):
        """Test starting a quiz"""
        attempt = QuizEngine.start_quiz(self.quiz, self.user)
        
        self.assertIsNotNone(attempt)
        self.assertEqual(attempt.user, self.user)
        self.assertEqual(attempt.quiz, self.quiz)
        self.assertIsNone(attempt.completed_at)
    
    def test_submit_answer(self):
        """Test submitting an answer"""
        attempt = QuizEngine.start_quiz(self.quiz, self.user)
        user_answer = {'answer': 'b'}
        
        response = QuizEngine.submit_answer(attempt, self.question1, user_answer)
        
        self.assertTrue(response.is_correct)
        self.assertEqual(response.points_earned, 5.0)
    
    def test_complete_quiz_passed(self):
        """Test completing quiz with passing score"""
        attempt = QuizEngine.start_quiz(self.quiz, self.user)
        
        # Answer both questions correctly
        QuizEngine.submit_answer(attempt, self.question1, {'answer': 'b'})
        QuizEngine.submit_answer(attempt, self.question2, {'answer': True})
        
        result = QuizEngine.complete_quiz(attempt)
        
        self.assertEqual(result['score'], 10.0)  # Perfect score
        self.assertTrue(result['passed'])
        self.assertEqual(result['correct_answers'], 2)
    
    def test_complete_quiz_failed(self):
        """Test completing quiz with failing score"""
        attempt = QuizEngine.start_quiz(self.quiz, self.user)
        
        # Answer both questions incorrectly
        QuizEngine.submit_answer(attempt, self.question1, {'answer': 'a'})
        QuizEngine.submit_answer(attempt, self.question2, {'answer': False})
        
        result = QuizEngine.complete_quiz(attempt)
        
        self.assertEqual(result['score'], 0.0)
        self.assertFalse(result['passed'])
        self.assertEqual(result['correct_answers'], 0)
    
    def test_cannot_submit_after_completion(self):
        """Test cannot submit answer after quiz completion"""
        attempt = QuizEngine.start_quiz(self.quiz, self.user)
        QuizEngine.submit_answer(attempt, self.question1, {'answer': 'b'})
        QuizEngine.complete_quiz(attempt)
        
        # Try to submit another answer
        with self.assertRaises(ValueError):
            QuizEngine.submit_answer(attempt, self.question2, {'answer': True})


class QuizViewsTestCase(TestCase):
    """Test quiz views"""
    
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
        
        self.quiz = Quiz.objects.create(
            lesson=self.lesson,
            title="Test Quiz",
            passing_score=6.0
        )
        
        self.question = Question.objects.create(
            quiz=self.quiz,
            question_type='multiple_choice',
            question_text="Test Question",
            options={'choices': [{'id': 'a', 'text': 'A'}, {'id': 'b', 'text': 'B'}]},
            correct_answer={'answer': 'b'},
            points=10.0,
            order=1
        )
        
        self.client.login(username='testuser', password='password123')
    
    def test_get_lesson_quiz(self):
        """Test getting quiz for lesson"""
        response = self.client.get(
            reverse('get_lesson_quiz', args=[self.lesson.id])
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('quiz', data)
        self.assertEqual(data['quiz']['id'], self.quiz.id)
        self.assertEqual(len(data['quiz']['questions']), 1)
    
    def test_start_quiz(self):
        """Test starting a quiz"""
        response = self.client.post(
            reverse('start_quiz', args=[self.quiz.id])
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('attempt_id', data)
    
    def test_submit_answer(self):
        """Test submitting an answer"""
        # Start quiz first
        start_response = self.client.post(
            reverse('start_quiz', args=[self.quiz.id])
        )
        attempt_id = start_response.json()['attempt_id']
        
        # Submit answer
        response = self.client.post(
            reverse('submit_quiz_answer', args=[attempt_id]),
            data={'question_id': self.question.id, 'answer': {'answer': 'b'}},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['is_correct'])
    
    def test_complete_quiz(self):
        """Test completing a quiz"""
        # Start quiz
        start_response = self.client.post(
            reverse('start_quiz', args=[self.quiz.id])
        )
        attempt_id = start_response.json()['attempt_id']
        
        # Submit answer
        self.client.post(
            reverse('submit_quiz_answer', args=[attempt_id]),
            data={'question_id': self.question.id, 'answer': {'answer': 'b'}},
            content_type='application/json'
        )
        
        # Complete quiz
        response = self.client.post(
            reverse('complete_quiz', args=[attempt_id])
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['passed'])
        self.assertEqual(data['score'], 10.0)
