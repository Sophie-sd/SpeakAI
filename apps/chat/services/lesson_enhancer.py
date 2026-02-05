"""
LessonContentEnhancer - Генерує унікальні AI промпти та адаптивні критерії оцінювання для уроків
"""

import json
import logging
from typing import Dict, List, Any, Optional
from django.conf import settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class LessonContentEnhancer:
    """Генератор контенту для уроків через Gemini AI"""
    
    def __init__(self):
        self.model_name = 'gemini-2.0-flash'
        if settings.GEMINI_API_KEY:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self.client = None
    
    def generate_voice_prompts(self, lesson: Any) -> List[str]:
        """
        Генерує 3-5 унікальних голосових промптів для уроку
        
        Args:
            lesson: Об'єкт Lesson з контекстом
            
        Returns:
            Список промптів (або пустий список якщо помилка)
        """
        if not self.client:
            logger.warning(f"No Gemini client for lesson {lesson.id}")
            return []
        
        prompt = f"""You are a Harvard-level ESL instructor creating voice practice prompts.

LESSON CONTEXT:
- Title: {lesson.title}
- Level: {lesson.module.level}
- Grammar: {lesson.grammar_focus}
- Vocabulary: {', '.join(lesson.vocabulary_list)}
- Voice Practice Type: {lesson.voice_practice_type}
- Instructions: {lesson.voice_practice_instructions}

TASK:
Generate 3-5 engaging, context-relevant voice practice prompts that:
1. Match the {lesson.module.level} proficiency level exactly
2. Practice the grammar focus: {lesson.grammar_focus}
3. Use vocabulary from the lesson
4. Are appropriate for {lesson.voice_practice_type} practice
5. Progress from easier to more challenging
6. Are specific, actionable, and natural

For {lesson.voice_practice_type} practice, adapt:
- Drill: Simple repetition phrases
- Q&A: Questions about the topic
- Dialogue: Back-and-forth exchanges
- Discussion: Open-ended discussion starters
- Debate: Argument/opinion prompts
- Native Conversation: Natural, idiomatic exchanges
- Expert Dialogue: Advanced technical/professional exchanges

Return as JSON array of strings ONLY - no explanations.
Example: ["Say slowly: Hello, my name is...", "Repeat: How are you?", "Practice: Nice to meet you!"]
"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            if not response or not response.text:
                logger.warning(f"Empty response from Gemini for voice prompts generation")
                return []
            
            # Parse JSON response
            try:
                result = json.loads(response.text)
                if isinstance(result, list):
                    # Ensure all items are strings
                    prompts = [str(p) for p in result[:5]]  # Max 5 prompts
                    logger.info(f"Generated {len(prompts)} voice prompts for lesson {lesson.id}")
                    return prompts
                else:
                    logger.warning(f"Unexpected response type for lesson {lesson.id}: {type(result)}")
                    return []
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse voice prompts JSON for lesson {lesson.id}: {e}", exc_info=True)
                return []
        
        except AttributeError as e:
            logger.error(f"Attribute error generating voice prompts for lesson {lesson.id}: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error generating voice prompts for lesson {lesson.id}: {e}", exc_info=True)
            return []
    
    def generate_homework_criteria(self, lesson: Any) -> Dict[str, Any]:
        """
        Генерує адаптивні критерії оцінювання для домашнього завдання
        залежно від рівня CEFR
        
        Args:
            lesson: Об'єкт Lesson
            
        Returns:
            Dict з criteria, weights, min_passing_score, тощо
        """
        if not self.client:
            logger.warning(f"No Gemini client for lesson {lesson.id}")
            return self._get_default_homework_criteria(lesson.module.level)
        
        level = lesson.module.level
        
        # Структурні шаблони для кожного рівня
        criteria_templates = {
            'A0': {
                'criteria_count': 3,
                'focus': 'completeness, basic_grammar, vocabulary',
                'min_score': 6.0,
                'weights': [40, 30, 30]
            },
            'A1': {
                'criteria_count': 3,
                'focus': 'completeness, basic_grammar, vocabulary',
                'min_score': 6.0,
                'weights': [35, 35, 30]
            },
            'A2': {
                'criteria_count': 4,
                'focus': 'grammar, vocabulary, structure, completeness',
                'min_score': 6.5,
                'weights': [25, 25, 25, 25]
            },
            'B1': {
                'criteria_count': 5,
                'focus': 'grammar, vocabulary, structure, task_completion, coherence',
                'min_score': 6.5,
                'weights': [20, 20, 20, 20, 20]
            },
            'B2': {
                'criteria_count': 6,
                'focus': 'grammar_mastery, lexical_resource, coherence, task_response, critical_thinking, style',
                'min_score': 7.0,
                'weights': [18, 17, 17, 17, 17, 14]
            },
            'C1': {
                'criteria_count': 6,
                'focus': 'grammar_mastery, lexical_resource, coherence, task_response, critical_thinking, sophistication',
                'min_score': 7.5,
                'weights': [16, 17, 17, 17, 17, 16]
            },
            'C2': {
                'criteria_count': 6,
                'focus': 'native_fluency, idiomatic_language, sophistication, accuracy, creativity, cultural_awareness',
                'min_score': 8.0,
                'weights': [16, 17, 17, 17, 17, 16]
            }
        }
        
        template = criteria_templates.get(level, criteria_templates['A1'])
        
        prompt = f"""You are a Cambridge/Harvard language assessment expert creating evaluation criteria.

LESSON CONTEXT:
- Level: {level}
- Title: {lesson.title}
- Grammar: {lesson.grammar_focus}
- Vocabulary: {', '.join(lesson.vocabulary_list)}
- Homework: {lesson.homework_description}

TASK:
Create evaluation criteria JSON for {level} level with:
- {template['criteria_count']} evaluation dimensions
- Focus areas: {template['focus']}
- Weights sum to 100
- Minimum passing score: {template['min_score']}
- Appropriate difficulty for {level}

Return ONLY valid JSON (no markdown, no explanations):
{{
    "criteria": {{
        "criterion_1": {{"weight": NUM, "description": "Description in Ukrainian"}},
        "criterion_2": {{"weight": NUM, "description": "Description in Ukrainian"}},
        ...
    }},
    "min_passing_score": {template['min_score']},
    "feedback_language": "ukrainian",
    "focus_areas": ["area1", "area2"],
    "example_feedback": "Example feedback for a good response in Ukrainian"
}}

Requirements:
1. Weights MUST sum to exactly 100
2. All descriptions in Ukrainian (clear, specific)
3. Criteria names in snake_case
4. Ensure weights match: {template['weights']}
"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            if not response or not response.text:
                logger.warning(f"Empty response from Gemini for homework criteria generation")
                return self._get_default_homework_criteria(level)
            
            try:
                result = json.loads(response.text)
                
                # Validation
                if 'criteria' in result and isinstance(result['criteria'], dict):
                    total_weight = sum(
                        c.get('weight', 0) 
                        for c in result['criteria'].values()
                    )
                    
                    if abs(total_weight - 100) > 0.1:
                        logger.warning(f"Weights sum to {total_weight} for lesson {lesson.id}, normalizing...")
                        # Normalize weights
                        factor = 100 / total_weight if total_weight > 0 else 1
                        for criterion in result['criteria'].values():
                            criterion['weight'] = round(criterion.get('weight', 0) * factor, 1)
                    
                    logger.info(f"Generated homework criteria for lesson {lesson.id} (level {level})")
                    return result
                else:
                    logger.warning(f"Invalid criteria structure for lesson {lesson.id}")
                    return self._get_default_homework_criteria(level)
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse homework criteria JSON for lesson {lesson.id}: {e}", exc_info=True)
                return self._get_default_homework_criteria(level)
        
        except AttributeError as e:
            logger.error(f"Attribute error generating homework criteria for lesson {lesson.id}: {e}", exc_info=True)
            return self._get_default_homework_criteria(level)
        except Exception as e:
            logger.error(f"Unexpected error generating homework criteria for lesson {lesson.id}: {e}", exc_info=True)
            return self._get_default_homework_criteria(level)
    
    def _get_default_homework_criteria(self, level: str) -> Dict[str, Any]:
        """Повертає стандартні критерії для рівня якщо генерація не вдалась"""
        
        defaults = {
            'A0': {
                'criteria': {
                    'completeness': {'weight': 40, 'description': 'Завдання виконано повністю'},
                    'basic_grammar': {'weight': 30, 'description': 'Базова граматика правильна'},
                    'vocabulary': {'weight': 30, 'description': 'Використано слова з уроку'}
                },
                'min_passing_score': 6.0,
                'feedback_language': 'ukrainian',
                'focus_areas': ['простота', 'чіткість', 'правильність']
            },
            'A1': {
                'criteria': {
                    'completeness': {'weight': 35, 'description': 'Завдання виконано повністю'},
                    'basic_grammar': {'weight': 35, 'description': 'Граматика здебільшого правильна'},
                    'vocabulary': {'weight': 30, 'description': 'Використано необхідний словник'}
                },
                'min_passing_score': 6.0,
                'feedback_language': 'ukrainian',
                'focus_areas': ['точність', 'повнота', 'ясність']
            },
            'A2': {
                'criteria': {
                    'grammar': {'weight': 25, 'description': 'Граматична точність'},
                    'vocabulary': {'weight': 25, 'description': 'Різноманітність словника'},
                    'structure': {'weight': 25, 'description': 'Структура висловлювання'},
                    'completeness': {'weight': 25, 'description': 'Повнота виконання'}
                },
                'min_passing_score': 6.5,
                'feedback_language': 'ukrainian',
                'focus_areas': ['зв\'язність', 'різноманітність', 'точність']
            }
        }
        
        # Fallback для B1 і вище
        for level_code in ['B1', 'B2', 'C1', 'C2']:
            if level_code not in defaults:
                defaults[level_code] = {
                    'criteria': {
                        'grammar_mastery': {'weight': 20, 'description': 'Володіння граматикою'},
                        'lexical_resource': {'weight': 20, 'description': 'Лексичне багатство'},
                        'coherence': {'weight': 20, 'description': 'Зв\'язність'},
                        'task_response': {'weight': 20, 'description': 'Відповідність завданню'},
                        'critical_thinking': {'weight': 20, 'description': 'Критичне мислення'}
                    },
                    'min_passing_score': 7.0 if level_code in ['B1', 'B2'] else 7.5,
                    'feedback_language': 'ukrainian',
                    'focus_areas': ['аргументація', 'стиль', 'нюанси']
                }
        
        return defaults.get(level, defaults['A1'])
