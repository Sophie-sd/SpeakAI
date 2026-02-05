"""
Tests for chat services (GeminiService, RolePlayEngine, LessonContentEnhancer)
"""
import json
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.chat.models import Module, Lesson, KnowledgeBase
from apps.chat.services.gemini import GeminiService, _parse_gemini_json
from apps.chat.services.roleplay_engine import RolePlayEngine
from apps.chat.services.lesson_enhancer import LessonContentEnhancer

User = get_user_model()


class ParseGeminiJsonTestCase(TestCase):
    """Test JSON parsing utility"""
    
    def test_parse_valid_json(self):
        """Test parsing valid JSON"""
        json_str = '{"response": "Hello", "translation": "Привіт"}'
        result = _parse_gemini_json(json_str)
        self.assertIsNotNone(result)
        self.assertEqual(result['response'], 'Hello')
    
    def test_parse_json_in_markdown(self):
        """Test parsing JSON wrapped in markdown"""
        json_str = '```json\n{"response": "Test"}\n```'
        result = _parse_gemini_json(json_str)
        self.assertIsNotNone(result)
        self.assertEqual(result['response'], 'Test')
    
    def test_parse_empty_string(self):
        """Test parsing empty string"""
        result = _parse_gemini_json('')
        self.assertIsNone(result)
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON"""
        result = _parse_gemini_json('not valid json')
        self.assertIsNone(result)


class GeminiServiceTestCase(TestCase):
    """Test GeminiService"""
    
    def setUp(self):
        """Set up test data"""
        self.service = GeminiService()
        
        # Create test lesson
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
            vocabulary_list=['hello', 'world'],
            homework_description="Write a short text",
            homework_instructions={
                'criteria': {
                    'grammar': {'weight': 50, 'description': 'Граматика'},
                    'vocabulary': {'weight': 50, 'description': 'Словник'}
                },
                'min_passing_score': 6.0,
                'feedback_language': 'ukrainian',
                'focus_areas': ['accuracy']
            },
            voice_practice_prompts=["Say hello", "Introduce yourself"]
        )
        
        self.user = User.objects.create_user(
            username='testuser',
            password='password123',
            email='test@test.com',
            level='A1'
        )
    
    def test_get_embedding_without_client(self):
        """Test get_embedding when client is not initialized"""
        service = GeminiService()
        service.client = None
        result = service.get_embedding("test text")
        self.assertEqual(result, [])
    
    def test_rag_search_without_client(self):
        """Test RAG search without client falls back to keyword search"""
        # Create knowledge base item
        KnowledgeBase.objects.create(
            topic="Test",
            content="This is a test content"
        )
        
        service = GeminiService()
        service.client = None
        results = service.rag_search("test")
        self.assertIsInstance(results, list)
    
    def test_evaluate_homework_without_instructions(self):
        """Test homework evaluation without instructions"""
        lesson_no_hw = Lesson.objects.create(
            module=self.module,
            lesson_number=2,
            title="No HW Lesson",
            homework_instructions={}
        )
        
        result = self.service.evaluate_homework(
            homework_text="Test homework",
            lesson=lesson_no_hw,
            user=self.user
        )
        
        self.assertIn('score', result)
        self.assertEqual(result['score'], 5.0)
    
    def test_evaluate_voice_practice_without_prompts(self):
        """Test voice practice evaluation without prompts"""
        lesson_no_vp = Lesson.objects.create(
            module=self.module,
            lesson_number=3,
            title="No VP Lesson",
            voice_practice_prompts=[]
        )
        
        result = self.service.evaluate_voice_practice(
            user_responses=["response 1"],
            lesson=lesson_no_vp,
            user=self.user
        )
        
        self.assertIn('score', result)
        self.assertEqual(result['score'], 5.0)
    
    def test_get_chat_response_without_client(self):
        """Test chat response without client"""
        service = GeminiService()
        service.client = None
        
        result = service.get_chat_response("Hello")
        
        self.assertIn('response', result)
        self.assertIn('translation', result)


class RolePlayEngineTestCase(TestCase):
    """Test RolePlayEngine"""
    
    def setUp(self):
        """Set up test data"""
        self.engine = RolePlayEngine()
        
        self.scenario = {
            'setting': 'Coffee Shop',
            'ai_role': 'Barista',
            'user_role': 'Customer',
            'objectives': ['Order coffee'],
            'difficulty': 'easy'
        }
    
    def test_build_scenario_prompt(self):
        """Test scenario prompt building"""
        prompt = self.engine._build_scenario_prompt(
            self.scenario,
            'A1',
            None
        )
        
        self.assertIn('Coffee Shop', prompt)
        self.assertIn('Barista', prompt)
        self.assertIn('A1', prompt)
    
    def test_start_scenario_without_client(self):
        """Test starting scenario without client"""
        engine = RolePlayEngine()
        engine.client = None
        
        result = engine.start_scenario(
            self.scenario,
            'A1',
            None
        )
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_continue_dialogue_without_session(self):
        """Test continuing dialogue without session"""
        result = self.engine.continue_dialogue(None, "Hello")
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)


class LessonContentEnhancerTestCase(TestCase):
    """Test LessonContentEnhancer"""
    
    def setUp(self):
        """Set up test data"""
        self.enhancer = LessonContentEnhancer()
        
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
            vocabulary_list=['hello', 'world'],
            voice_practice_type="Drill",
            voice_practice_instructions="Repeat after me",
            homework_description="Write a text"
        )
    
    def test_generate_voice_prompts_without_client(self):
        """Test generating voice prompts without client"""
        enhancer = LessonContentEnhancer()
        enhancer.client = None
        
        result = enhancer.generate_voice_prompts(self.lesson)
        
        self.assertEqual(result, [])
    
    def test_generate_homework_criteria_without_client(self):
        """Test generating homework criteria without client falls back to defaults"""
        enhancer = LessonContentEnhancer()
        enhancer.client = None
        
        result = enhancer.generate_homework_criteria(self.lesson)
        
        self.assertIn('criteria', result)
        self.assertIn('min_passing_score', result)
        self.assertIsInstance(result['criteria'], dict)
    
    def test_get_default_homework_criteria(self):
        """Test default homework criteria generation"""
        result = self.enhancer._get_default_homework_criteria('A1')
        
        self.assertIn('criteria', result)
        self.assertIn('min_passing_score', result)
        
        # Check weights sum to 100
        total_weight = sum(
            c.get('weight', 0) 
            for c in result['criteria'].values()
        )
        self.assertAlmostEqual(total_weight, 100, places=1)
