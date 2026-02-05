"""
Role-Play Engine для адаптивних сценаріїв з AI
"""
from typing import Dict, List, Any
from google import genai
from google.genai import types
from django.conf import settings
import logging
import json

logger = logging.getLogger(__name__)


class RolePlayEngine:
    """Движок для рольових ігор з AI"""
    
    def __init__(self):
        self.model_name = 'gemini-2.0-flash'
        if settings.GEMINI_API_KEY:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self.client = None
    
    def start_scenario(
        self, 
        scenario: Dict[str, Any], 
        user_level: str,
        user_profile: Any = None,
        lesson_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Почати новий сценарій рольової гри
        
        Args:
            scenario: JSON об'єкт сценарію з Lesson
            user_level: Рівень користувача (A1, B2 і т.д.)
            user_profile: Профіль користувача
            lesson_context: Контекст уроку (grammar_focus, vocabulary, theory)
        
        Returns:
            Dict з greeting повідомленням від AI + translation, correction, explanation
        """
        system_prompt = self._build_scenario_prompt(scenario, user_level, user_profile, lesson_context)
        
        if not self.client:
            logger.error("RolePlayEngine: Gemini client not initialized")
            return {
                'ai_message': "Hello! Let's practice English together.",
                'translation': "Привіт! Давайте практикуватимемо англійську мову разом.",
                'corrected_text': None,
                'explanation': None,
                'error': 'No API client available',
                'success': False
            }
        
        try:
            # Створити чат з початковою історією
            chat = self.client.chats.create(
                model=self.model_name,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json"
                )
            )
            
            # Початкове привітання від AI
            response = chat.send_message(message="Start the scenario with a greeting.")
            
            if not response or not response.text:
                logger.warning("Empty response from Gemini for role-play start")
                return {
                    'ai_message': "Hello! Let's practice English together.",
                    'translation': "Привіт! Давайте практикуватимемо англійську мову разом.",
                    'corrected_text': None,
                    'explanation': None,
                    'error': 'Empty response',
                    'success': False
                }
            
            # Parse JSON response
            try:
                result_data = json.loads(response.text)
                return {
                    'ai_message': result_data.get('response', response.text),
                    'translation': result_data.get('translation', ''),
                    'corrected_text': result_data.get('corrected_text'),
                    'explanation': result_data.get('explanation'),
                    'chat_session': chat,
                    'scenario_name': scenario.get('setting', 'Role-play'),
                    'success': True
                }
            except json.JSONDecodeError:
                # Fallback: if AI returns plain text instead of JSON
                logger.warning("Role-play response was not valid JSON, treating as plain text")
                return {
                    'ai_message': response.text,
                    'translation': '',
                    'corrected_text': None,
                    'explanation': None,
                    'chat_session': chat,
                    'scenario_name': scenario.get('setting', 'Role-play'),
                    'success': True
                }
        
        except AttributeError as e:
            logger.error(f"Error accessing role-play response structure: {e}", exc_info=True)
            return {
                'ai_message': "Hello! Let's practice English together.",
                'translation': "Привіт! Давайте практикуватимемо англійську мову разом.",
                'corrected_text': None,
                'explanation': None,
                'error': str(e),
                'success': False
            }
        except Exception as e:
            logger.error(f"Unexpected error starting role-play: {e}", exc_info=True)
            return {
                'ai_message': "Hello! Let's practice English together.",
                'translation': "Привіт! Давайте практикуватимемо англійську мову разом.",
                'corrected_text': None,
                'explanation': None,
                'error': str(e),
                'success': False
            }
    
    def _build_scenario_prompt(
        self, 
        scenario: Dict[str, Any], 
        user_level: str,
        user_profile: Any,
        lesson_context: Dict[str, Any] = None
    ) -> str:
        """Побудувати системний промпт для сценарію"""
        
        difficulty_instructions = {
            'easy': 'Use simple present tense, basic vocabulary. Speak slowly and clearly.',
            'medium': 'Use varied tenses, common phrases. Speak at normal pace.',
            'hard': 'Use complex structures, idioms. Speak naturally with some slang.'
        }
        
        difficulty = scenario.get('difficulty', 'easy')
        
        prompt = f"""You are a role-play partner for an English learner at level {user_level}.

SCENARIO SETUP:
Setting: {scenario.get('setting', 'A general conversation')}
Your Role: {scenario.get('ai_role', 'A helpful conversation partner')}
User's Role: {scenario.get('user_role', 'An English learner')}

OBJECTIVES:
The user needs to accomplish these goals in this conversation:
{chr(10).join(['- ' + obj for obj in scenario.get('objectives', ['Practice speaking'])])}

DIFFICULTY LEVEL ({difficulty}):
{difficulty_instructions.get(difficulty, difficulty_instructions['easy'])}

INSTRUCTIONS:
1. Stay in character throughout the conversation
2. React naturally to what the user says
3. If user makes grammar mistakes, respond naturally and NOTE them for correction
4. Keep responses short (2-3 sentences max)
5. Ask follow-up questions to keep conversation going
6. Adapt to user's English level
7. If user seems stuck, provide hints or rephrase
8. After 5-7 exchanges, wrap up the scenario naturally

EVALUATION (internal):
Track: grammar accuracy, vocabulary usage, fluency, task completion

LANGUAGE HANDLING (CRITICAL):
1. USER CAN WRITE IN UKRAINIAN - this is NORMAL and ALLOWED
2. Ukrainian is the student's native language and communication tool
3. ALWAYS understand and accept Ukrainian input - never refuse it
4. ALWAYS respond in English (stay in character)
5. ALWAYS provide Ukrainian translation in "translation" field
6. If user writes ONLY Ukrainian, respond naturally in character (in English)
7. If user mixes Ukrainian and English, note the English parts in "corrected_text" if there are errors
8. DO NOT say "I don't speak Ukrainian" - you DO understand it
9. DO NOT ask user to speak English - they can use Ukrainian freely
10. Example:
    - User: "Привіт! Я хочу coffee please"
    - You (in character): "Hello! Of course, what size would you like?"
    - Translation: "Привіт! Звичайно, який розмір ви хочете?"

OUTPUT FORMAT - ALWAYS respond in JSON (even if user writes Ukrainian):
{{
    "response": "Your in-character response in English",
    "translation": "Ukrainian translation of your response",
    "corrected_text": "Corrected version of user's English (if there are errors), or null",
    "explanation": "Brief Ukrainian explanation of grammar mistakes (if any), or null"
}}

Begin the scenario with a greeting appropriate to your role."""
        
        # Додати контекст про користувача якщо є
        if user_profile:
            prompt += f"\n\nUSER CONTEXT:\n- Native language: {user_profile.native_language}"
            if hasattr(user_profile, 'interests') and user_profile.interests:
                prompt += f"\n- Interests: {', '.join(user_profile.interests[:3])}"
        
        # Додати lesson context якщо є
        if lesson_context:
            prompt += f"""

LESSON CONTEXT (stay within this scope):
Grammar focus: {lesson_context.get('grammar_focus', 'General')}
Key vocabulary: {', '.join(lesson_context.get('vocabulary', [])[:20]) if lesson_context.get('vocabulary') else 'N/A'}

Important: If user goes off-topic or tries to discuss something unrelated to lesson context, gently redirect them back to the scenario while staying in character."""
        
        return prompt
    
    def continue_dialogue(
        self,
        chat_session: Any,
        user_message: str
    ) -> Dict[str, Any]:
        """
        Продовжити діалог в рольовій грі
        
        Args:
            chat_session: Gemini chat session
            user_message: Повідомлення користувача
        
        Returns:
            Dict з відповіддю AI + translation, correction, explanation
        """
        if not chat_session:
            logger.error("Continue dialogue called with no chat session")
            return {
                'ai_message': "I'm sorry, the conversation session was lost. Could you start again?",
                'translation': "Мені дуже жаль, сесія розмови була втрачена. Можна почати заново?",
                'corrected_text': None,
                'explanation': None,
                'error': 'No chat session',
                'success': False
            }
        
        try:
            response = chat_session.send_message(message=user_message)
            
            if not response or not response.text:
                logger.warning("Empty response from Gemini for role-play continuation")
                return {
                    'ai_message': "I'm sorry, I didn't catch that. Could you repeat?",
                    'translation': "Мені дуже жаль, я не чув. Можете повторити?",
                    'corrected_text': None,
                    'explanation': None,
                    'error': 'Empty response',
                    'success': False
                }
            
            # Parse JSON response
            try:
                result_data = json.loads(response.text)
                return {
                    'ai_message': result_data.get('response', response.text),
                    'translation': result_data.get('translation', ''),
                    'corrected_text': result_data.get('corrected_text'),
                    'explanation': result_data.get('explanation'),
                    'success': True
                }
            except json.JSONDecodeError:
                # Fallback: if AI returns plain text instead of JSON
                logger.warning("Role-play continuation was not valid JSON, treating as plain text")
                return {
                    'ai_message': response.text,
                    'translation': '',
                    'corrected_text': None,
                    'explanation': None,
                    'success': True
                }
        
        except AttributeError as e:
            logger.error(f"Error accessing role-play dialogue response: {e}", exc_info=True)
            return {
                'ai_message': "I'm sorry, I didn't catch that. Could you repeat?",
                'translation': "Мені дуже жаль, я не чув. Можете повторити?",
                'corrected_text': None,
                'explanation': None,
                'error': str(e),
                'success': False
            }
        except Exception as e:
            logger.error(f"Unexpected error in role-play dialogue: {e}", exc_info=True)
            return {
                'ai_message': "I'm sorry, I didn't catch that. Could you repeat?",
                'translation': "Мені дуже жаль, я не чув. Можете повторити?",
                'corrected_text': None,
                'explanation': None,
                'error': str(e),
                'success': False
            }
    
    def serialize_history(self, chat_session: Any) -> List[Dict[str, str]]:
        """
        Серіалізувати chat history з Gemini session в JSON
        
        Args:
            chat_session: Gemini chat session object
            
        Returns:
            List of message dicts [{'role': 'user'/'model', 'content': 'text'}]
        """
        if not chat_session or not hasattr(chat_session, 'history'):
            return []
        
        messages_history = []
        try:
            for content in chat_session.history:
                role = content.role  # 'user' or 'model'
                # Extract text from parts
                text = ''
                if hasattr(content, 'parts') and content.parts:
                    for part in content.parts:
                        if hasattr(part, 'text'):
                            text += part.text
                
                messages_history.append({
                    'role': role,
                    'content': text
                })
        except Exception as e:
            logger.error(f"Error serializing chat history: {e}", exc_info=True)
        
        return messages_history
    
    def restore_session(
        self, 
        system_prompt: str, 
        messages_history: List[Dict[str, str]]
    ) -> Any:
        """
        Відновити chat session з збереженої history
        
        Args:
            system_prompt: System instruction для чату
            messages_history: List of messages [{'role': 'user'/'model', 'content': 'text'}]
            
        Returns:
            Gemini chat session object або None
        """
        if not self.client:
            logger.error("RolePlayEngine: Cannot restore session - no client")
            return None
        
        try:
            # Конвертувати messages_history в Gemini Content format
            history = []
            for msg in messages_history:
                history.append(
                    types.Content(
                        role=msg['role'], 
                        parts=[types.Part(text=msg['content'])]
                    )
                )
            
            # Створити chat з історією
            chat = self.client.chats.create(
                model=self.model_name,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json"
                ),
                history=history
            )
            
            logger.info(f"Restored role-play session with {len(history)} messages")
            return chat
            
        except Exception as e:
            logger.error(f"Error restoring chat session: {e}", exc_info=True)
            return None
    
    def evaluate_performance(
        self,
        dialogue: List[Dict[str, str]],
        scenario_objectives: List[str],
        user_level: str
    ) -> Dict[str, Any]:
        """
        Оцінити виступ користувача в рольовій грі
        
        Args:
            dialogue: Список повідомлень діалогу
            scenario_objectives: Цілі сценарію
            user_level: Рівень користувача
        
        Returns:
            Dict з оцінками та фідбеком
        """
        # Побудувати контекст діалогу
        dialogue_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}" 
            for msg in dialogue
        ])
        
        evaluation_prompt = f"""Evaluate this English conversation for a {user_level} level learner.

DIALOGUE:
{dialogue_text}

SCENARIO OBJECTIVES:
{chr(10).join(['- ' + obj for obj in scenario_objectives])}

Provide evaluation as JSON:
{{
    "grammar_score": <0-10>,
    "vocabulary_score": <0-10>,
    "fluency_score": <0-10>,
    "task_completion_score": <0-10>,
    "overall_score": <0-10>,
    "strengths": ["strength 1", "strength 2"],
    "improvements": ["area 1", "area 2"],
    "feedback": "Detailed feedback in 2-3 sentences",
    "grammar_mistakes": [
        {{"original": "I goed", "correction": "I went", "explanation": "Past tense of 'go' is irregular"}}
    ]
}}
"""
        
        if not self.client:
            logger.error("RolePlayEngine: No client for evaluation")
            return {
                'grammar_score': 5.0,
                'vocabulary_score': 5.0,
                'fluency_score': 5.0,
                'task_completion_score': 5.0,
                'overall_score': 5.0,
                'strengths': ['Participated in the conversation'],
                'improvements': ['Continue practicing'],
                'feedback': 'Evaluation unavailable - no API client',
                'grammar_mistakes': []
            }
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=evaluation_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            if not response or not response.text:
                logger.warning("Empty response from Gemini for role-play evaluation")
                return {
                    'grammar_score': 5.0,
                    'vocabulary_score': 5.0,
                    'fluency_score': 5.0,
                    'task_completion_score': 5.0,
                    'overall_score': 5.0,
                    'strengths': ['Participated in the conversation'],
                    'improvements': ['Continue practicing'],
                    'feedback': 'Empty evaluation response',
                    'grammar_mistakes': []
                }
            
            evaluation = json.loads(response.text)
            return evaluation
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error evaluating role-play: {e}", exc_info=True)
            return {
                'grammar_score': 5.0,
                'vocabulary_score': 5.0,
                'fluency_score': 5.0,
                'task_completion_score': 5.0,
                'overall_score': 5.0,
                'strengths': ['Participated in the conversation'],
                'improvements': ['Continue practicing'],
                'feedback': 'JSON parsing error',
                'grammar_mistakes': []
            }
        except AttributeError as e:
            logger.error(f"Attribute error evaluating role-play: {e}", exc_info=True)
            return {
                'grammar_score': 5.0,
                'vocabulary_score': 5.0,
                'fluency_score': 5.0,
                'task_completion_score': 5.0,
                'overall_score': 5.0,
                'strengths': ['Participated in the conversation'],
                'improvements': ['Continue practicing'],
                'feedback': 'Response structure error',
                'grammar_mistakes': []
            }
        except Exception as e:
            logger.error(f"Unexpected error evaluating role-play: {e}", exc_info=True)
            return {
                'grammar_score': 5.0,
                'vocabulary_score': 5.0,
                'fluency_score': 5.0,
                'task_completion_score': 5.0,
                'overall_score': 5.0,
                'strengths': ['Participated in the conversation'],
                'improvements': ['Continue practicing'],
                'feedback': 'Good effort! Keep practicing.',
                'error': str(e)
            }
