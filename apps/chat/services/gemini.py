import json
import re
from typing import Optional, Dict, Any, List

from google import genai
from google.genai import types
from django.conf import settings
from apps.chat.models import KnowledgeBase, Memory
from apps.chat.monitoring import monitor_api_call, log_event
import logging

logger = logging.getLogger(__name__)

# Fallback response when Gemini fails
GEMINI_ERROR_FALLBACK = {
    "response": "Sorry, I'm having trouble thinking right now.",
    "translation": "Вибачте, у мене зараз виникли труднощі з обробкою запиту.",
    "explanation": None,
    "corrected_text": None,
    "full_english_version": None,
    "phase": "initial",
    "has_errors": False,
}


def _parse_gemini_json(raw_text: str) -> Optional[dict]:
    """
    Parse Gemini JSON response with fallbacks for malformed output.
    Handles invalid escape sequences, markdown-wrapped JSON, and control characters.
    """
    if not raw_text or not raw_text.strip():
        return None

    text = raw_text.strip()

    # Try direct parse with strict=False (allows control chars in strings)
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        pass

    # Extract JSON from markdown code blocks (```json ... ``` or ``` ... ```)
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1).strip(), strict=False)
        except json.JSONDecodeError:
            pass

    # Try to fix common invalid escape sequences: replace \ followed by
    # non-valid-escape char with escaped backslash + char
    def fix_escapes(match: re.Match) -> str:
        char = match.group(1)
        if char in '"\\/bfnrtu':
            return match.group(0)
        return "\\\\" + char

    fixed = re.sub(r"\\([^\"\\/bfnrtu])", fix_escapes, text)
    try:
        return json.loads(fixed, strict=False)
    except json.JSONDecodeError:
        pass

    return None


class GeminiService:
    def __init__(self):
        self.model_name = 'gemini-2.0-flash'
        self.embedding_model = 'gemini-embedding-001'
        if settings.GEMINI_API_KEY:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self.client = None

    def get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for text with proper error handling
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding values or empty list on error
        """
        if not self.client:
            logger.warning("Gemini client not initialized - no API key")
            return []
        
        try:
            result = self.client.models.embed_content(
                model=self.embedding_model,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY"
                )
            )
            return result.embeddings[0].values
        except AttributeError as e:
            logger.error(f"Error accessing embedding result structure: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting embedding: {e}", exc_info=True)
            return []

    def rag_search(self, query_text: str, limit: int = 3) -> List[Any]:
        """
        RAG search with embeddings and fallback to keyword search
        
        Args:
            query_text: Query text
            limit: Maximum results to return
            
        Returns:
            List of KnowledgeBase objects
        """
        if not self.client:
            logger.warning("RAG search without client - using keyword fallback")
            try:
                return list(KnowledgeBase.objects.filter(content__icontains=query_text)[:limit])
            except Exception as e:
                logger.error(f"Error in keyword search fallback: {e}", exc_info=True)
                return []

        # 1. Get embedding for query
        try:
            query_embedding = self.get_embedding(query_text)
        except Exception as e:
            logger.error(f"Error getting query embedding: {e}", exc_info=True)
            query_embedding = []
            
        if not query_embedding:
            # Fallback to keyword search
            try:
                return list(KnowledgeBase.objects.filter(content__icontains=query_text)[:limit])
            except Exception as e:
                logger.error(f"Error in keyword search: {e}", exc_info=True)
                return []
        
        # 2. Search in DB
        if 'sqlite' in settings.DATABASES['default']['ENGINE']:
             # Fallback: Keyword search for SQLite
            try:
                return list(KnowledgeBase.objects.filter(content__icontains=query_text)[:limit])
            except Exception as e:
                logger.error(f"Error in SQLite search: {e}", exc_info=True)
                return []
        else:
            try:
                from pgvector.django import L2Distance
                return list(KnowledgeBase.objects.order_by(L2Distance('embedding', query_embedding))[:limit])
            except ImportError as e:
                logger.warning(f"pgvector not available, falling back to keyword search: {e}")
                try:
                    return list(KnowledgeBase.objects.filter(content__icontains=query_text)[:limit])
                except Exception as e2:
                    logger.error(f"Error in keyword search fallback: {e2}", exc_info=True)
                    return []
            except Exception as e:
                logger.error(f"Vector search failed: {e}", exc_info=True)
                try:
                    return list(KnowledgeBase.objects.filter(content__icontains=query_text)[:limit])
                except Exception as e2:
                    logger.error(f"Error in fallback search: {e2}", exc_info=True)
                    return []

    @monitor_api_call('GeminiService', 'evaluate_homework', 'gemini-2.0-flash')
    def evaluate_homework(
        self, 
        homework_text: str,
        lesson: Any,
        user: Any
    ) -> Dict[str, Any]:
        """
        Оцінює домашнє завдання за критеріями з homework_instructions
        
        Args:
            homework_text: Текст домашнього завдання від учня
            lesson: Об'єкт Lesson з criteria
            user: Об'єкт користувача
            
        Returns:
            Dict з оцінками, feedback, помилками
        """
        if not self.client or not lesson.homework_instructions:
            return {
                'score': 5.0,
                'feedback': 'Unable to evaluate homework',
                'errors': [],
                'strengths': []
            }
        
        criteria = lesson.homework_instructions.get('criteria', {})
        focus_areas = lesson.homework_instructions.get('focus_areas', [])
        
        evaluation_prompt = f"""You are a {lesson.module.level}-level English language evaluator.

LESSON CONTEXT:
- Level: {lesson.module.level}
- Grammar focus: {lesson.grammar_focus}
- Vocabulary: {', '.join(lesson.vocabulary_list[:10])}
- Homework assignment: {lesson.homework_description}

EVALUATION CRITERIA:
{json.dumps(criteria, ensure_ascii=False, indent=2)}

STUDENT HOMEWORK:
{homework_text}

FOCUS AREAS: {', '.join(focus_areas)}

Evaluate and return ONLY valid JSON (no markdown):
{{
    "score": <0.0-10.0>,
    "criteria_scores": {{
        "criterion_name": <0.0-10.0>,
        ...
    }},
    "feedback": "Detailed constructive feedback in Ukrainian (3-5 sentences)",
    "errors": [
        {{"type": "grammar|vocabulary|structure", "original": "text", "correction": "correction", "explanation": "explanation in Ukrainian"}}
    ],
    "strengths": ["strength 1", "strength 2"],
    "improvements": ["area 1 to improve", "area 2 to improve"],
    "next_step": "Specific next learning step in Ukrainian"
}}
"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=evaluation_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            if not response or not response.text:
                logger.warning(f"Empty response from Gemini for homework evaluation")
                return {'score': 5.0, 'feedback': 'Empty response from AI', 'errors': [], 'strengths': []}
            
            evaluation = _parse_gemini_json(response.text)
            if evaluation and isinstance(evaluation, dict):
                # Save error memories if any
                try:
                    if evaluation.get('errors'):
                        for error in evaluation['errors'][:3]:  # Max 3 errors per submission
                            error_type = error.get('type', 'general')
                            Memory.objects.create(
                                user=user,
                                fact=f"{error.get('original', '')} → {error.get('correction', '')}",
                                memory_type='error',
                                error_category=error_type
                            )
                except Exception as e:
                    logger.error(f"Error saving error memories: {e}", exc_info=True)
                
                # Save success memory if high score
                try:
                    min_score = lesson.homework_instructions.get('min_passing_score', 6.0)
                    if evaluation.get('score', 0) >= min_score:
                        Memory.objects.create(
                            user=user,
                            fact=f"Successfully completed homework: {lesson.title}",
                            memory_type='progress'
                        )
                except Exception as e:
                    logger.error(f"Error saving success memory: {e}", exc_info=True)
                
                logger.info(f"Evaluated homework for user {user.id}, lesson {lesson.id}: score {evaluation.get('score')}")
                return evaluation
            else:
                logger.warning(f"Invalid homework evaluation response for lesson {lesson.id}")
                return {'score': 5.0, 'feedback': 'Invalid evaluation format', 'errors': [], 'strengths': []}
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error evaluating homework for lesson {lesson.id}: {e}", exc_info=True)
            return {'score': 5.0, 'feedback': 'JSON parsing error', 'errors': [], 'strengths': []}
        except AttributeError as e:
            logger.error(f"Attribute error evaluating homework for lesson {lesson.id}: {e}", exc_info=True)
            return {'score': 5.0, 'feedback': 'Response structure error', 'errors': [], 'strengths': []}
        except Exception as e:
            logger.error(f"Unexpected error evaluating homework for lesson {lesson.id}: {e}", exc_info=True)
            return {'score': 5.0, 'feedback': 'Evaluation error', 'errors': [], 'strengths': []}
    
    @monitor_api_call('GeminiService', 'evaluate_voice_practice', 'gemini-2.0-flash')
    def evaluate_voice_practice(
        self,
        user_responses: List[str],
        lesson: Any,
        user: Any
    ) -> Dict[str, Any]:
        """
        Оцінює голосову практику за промптами з voice_practice_prompts
        
        Args:
            user_responses: Список відповідей користувача на промпти
            lesson: Об'єкт Lesson з prompts
            user: Об'єкт користувача
            
        Returns:
            Dict з оцінками та feedback
        """
        if not self.client or not lesson.voice_practice_prompts:
            return {
                'score': 5.0,
                'feedback': 'Unable to evaluate voice practice',
                'items': []
            }
        
        # Побудувати порівняння: prompt vs response
        practice_items = []
        for i, (prompt, response) in enumerate(zip(lesson.voice_practice_prompts, user_responses)):
            practice_items.append({
                'prompt': prompt,
                'response': response,
                'number': i + 1
            })
        
        evaluation_prompt = f"""You are a {lesson.module.level}-level pronunciation and fluency evaluator.

LESSON CONTEXT:
- Level: {lesson.module.level}
- Voice practice type: {lesson.voice_practice_type}
- Grammar: {lesson.grammar_focus}
- Vocabulary: {', '.join(lesson.vocabulary_list[:5])}

PRACTICE ITEMS (Prompt → Student Response):
{json.dumps(practice_items, ensure_ascii=False, indent=2)}

Evaluate each response and return ONLY valid JSON:
{{
    "overall_score": <0.0-10.0>,
    "items": [
        {{
            "number": 1,
            "score": <0.0-10.0>,
            "fluency_score": <0.0-10.0>,
            "accuracy_score": <0.0-10.0>,
            "feedback": "Feedback in Ukrainian"
        }}
    ],
    "strengths": ["strength1", "strength2"],
    "improvements": ["improvement1", "improvement2"],
    "overall_feedback": "Overall assessment in Ukrainian"
}}
"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=evaluation_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            if not response or not response.text:
                logger.warning(f"Empty response from Gemini for voice practice evaluation")
                return {'overall_score': 5.0, 'feedback': 'Empty response from AI', 'items': []}
            
            evaluation = _parse_gemini_json(response.text)
            if evaluation and isinstance(evaluation, dict):
                logger.info(f"Evaluated voice practice for user {user.id}, lesson {lesson.id}: score {evaluation.get('overall_score')}")
                return evaluation
            else:
                logger.warning(f"Invalid voice practice evaluation response for lesson {lesson.id}")
                return {'overall_score': 5.0, 'feedback': 'Invalid evaluation format', 'items': []}
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error evaluating voice practice for lesson {lesson.id}: {e}", exc_info=True)
            return {'overall_score': 5.0, 'feedback': 'JSON parsing error', 'items': []}
        except AttributeError as e:
            logger.error(f"Attribute error evaluating voice practice for lesson {lesson.id}: {e}", exc_info=True)
            return {'overall_score': 5.0, 'feedback': 'Response structure error', 'items': []}
        except Exception as e:
            logger.error(f"Unexpected error evaluating voice practice for lesson {lesson.id}: {e}", exc_info=True)
            return {'overall_score': 5.0, 'feedback': 'Evaluation error', 'items': []}

    @monitor_api_call('GeminiService', 'get_chat_response', 'gemini-2.0-flash')
    def get_chat_response(self, user_message, chat_history_objects=[], user_profile=None):
        if not self.client:
            return {
                **GEMINI_ERROR_FALLBACK,
                "response": "Gemini API Key is missing. Please configure it in .env.",
                "translation": "Ключ Gemini API відсутній. Будь ласка, налаштуйте його в .env.",
            }

        # 1. RAG Search
        try:
            context_docs = self.rag_search(user_message)
            context_text = "\n\n".join([f"Topic: {doc.topic}\nContent: {doc.content}" for doc in context_docs])
        except Exception as e:
            logger.error(f"Error in RAG search: {e}", exc_info=True)
            context_text = ""
        
        # 2. Build Context
        user_info = ""
        if user_profile:
            user_info = f"""
            Student Level: {user_profile.level}
            Interests: {', '.join(user_profile.interests)}
            Native Language: {user_profile.native_language}
            """

        system_instruction = f"""You are an expert AI English Tutor. 
        Your goal is to help the student improve their English skills through natural conversation.
        
        {user_info}

        INTERNAL KNOWLEDGE BASE (Prioritize this info):
        {context_text}

        INTERACTION TRIGGERS (these override normal response structure):
        When you see "[ACTION: explain_detailed_ua]" or "[ACTION: explain_detailed_en]", the user message may contain context after "Поточне повідомлення:" or "Current message:". Extract that message if present.
        
        - "[ACTION: explain_detailed_ua]": Put a deep linguistic explanation of the student's English mistakes from the provided message (or from conversation history if no message provided) in the "explanation" field, IN UKRAINIAN. Cover grammar, vocabulary, word order, and why the corrections matter. Set corrected_text to null. Set phase to "detailed_explanation".
        - "[ACTION: explain_detailed_en]": Put a deep linguistic explanation of the student's English mistakes from the provided message (or from conversation history if no message provided) in the "explanation" field, IN ENGLISH. Be thorough and educational. Set corrected_text to null. Set phase to "detailed_explanation".
        - "[ACTION: practice_task]": When you see this action, the message will contain context:
          - "Оригінал:" - student's original message with error
          - "Виправлено:" - corrected version
          - "Помилка:" - explanation of the mistake
          
          Generate a SHORT, TARGETED practice exercise (1-3 sentences) specifically for THIS mistake type in "response".
          The exercise should:
          - Focus ONLY on the specific grammar/vocabulary issue found
          - Be at student's level
          - Have clear instructions in Ukrainian
          - Require student to construct similar correct sentence
          
          Set phase to "practice".
          Set all other fields (translation, explanation, corrected_text, full_english_version) to null.
        - "[ACTION: continue_lesson]": Natural transition back to the lesson in "response". Set phase to "initial".

        CORE RULES (for normal chat, when no ACTION is present):
        1. LANGUAGE DISTINCTION: You must accurately distinguish between Ukrainian and English.
        2. RESPONSE LANGUAGE - ALWAYS RESPOND IN ENGLISH:
           - **CRITICAL: Your response MUST ALWAYS be in English, regardless of input language.**
           - This is for the student's English practice. Always provide "translation" field with Ukrainian translation.
        3. MIXED LANGUAGE HANDLING:
           - If user input contains BOTH Ukrainian AND English words, always provide "full_english_version" field with the ENTIRE message translated to perfect English.
           - Example: "I like читати книги" → full_english_version: "I like to read books"
           - Set has_errors to true if there are English mistakes to correct.
        4. SELECTIVE CORRECTION:
           - ONLY correct English grammar, spelling, or vocabulary errors in the user's input.
           - DO NOT correct Ukrainian errors. Treat Ukrainian as the student's natural tool for communication.
        5. RESPONSE STRUCTURE (normal chat only):
           - Your response in "response" MUST ALWAYS be in English (even if user wrote in Ukrainian).
           - Always provide "translation" field with Ukrainian translation of your response.
           - If mixed language input: Also provide "full_english_version" with entire message in English.
           - If pure English AND contains mistakes: Also provide "corrected_text" with the perfect version. Set has_errors to true.
           - If pure English AND is CORRECT (no mistakes): Set corrected_text to null, explanation to null, and has_errors to false.
           - Put brief Ukrainian explanation of any ENGLISH mistakes in "explanation", or null if none.
        6. STYLE: Speak like a natural human tutor. Be encouraging. Use vocabulary appropriate for level {user_profile.level if user_profile else 'A1'}.
        7. FORMATTING: Output plain text only (no markdown, no bold, no asterisks).

        Output MUST be a JSON object:
        {{
            "corrected_text": "Perfect English version of user message if PURE English WITH MISTAKES, or null if mixed language OR if pure English is CORRECT",
            "full_english_version": "Full phrase in English only if mixed language input (e.g. 'I like to read books'), or null if pure English",
            "explanation": "Explanation of English mistakes. Language: Ukrainian for normal chat and [ACTION: explain_detailed_ua]; English for [ACTION: explain_detailed_en]. Null if no mistakes to explain.",
            "response": "Your tutor response in English (ALWAYS English, never Ukrainian)",
            "translation": "Ukrainian translation of your tutor response (ALWAYS provide this)",
            "phase": "initial" | "detailed_explanation" | "practice",
            "has_errors": true/false (true ONLY if there are English grammar/spelling/vocabulary mistakes)
        }}
        """

        # 3. Prepare History for Gemini (User/Model format)
        history = []
        try:
            for msg in chat_history_objects:
                role = "user" if msg.role == "user" else "model"
                # Since we now use JSON, we should try to feed it clean text for history 
                # if the previous messages were JSON. We'll handle that in the loop.
                try:
                    content_json = json.loads(msg.content)
                    text_content = content_json.get("response", msg.content)
                except:
                    text_content = msg.content
                    
                history.append(types.Content(role=role, parts=[types.Part(text=text_content)]))
        except Exception as e:
            logger.error(f"Error preparing chat history: {e}", exc_info=True)
            history = []

        # Create chat with system instruction and JSON output mode
        try:
            chat = self.client.chats.create(
                model=self.model_name,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json"
                ),
                history=history
            )
        except Exception as e:
            logger.error(f"Error creating chat session: {e}", exc_info=True)
            return dict(GEMINI_ERROR_FALLBACK)

        logger.debug(
            "Gemini request: user_message (first 200 chars)=%s, history_len=%d",
            (user_message or "")[:200],
            len(history),
        )

        raw_text = ""
        try:
            response = chat.send_message(message=user_message)
            
            # Check for safety/blocking issues
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                block_reason = getattr(response.prompt_feedback, 'block_reason', None)
                if block_reason:
                    logger.warning(
                        "Gemini prompt was blocked: block_reason=%s",
                        block_reason,
                    )
                    return dict(GEMINI_ERROR_FALLBACK)
            
            if hasattr(response, 'candidates') and response.candidates:
                finish_reason = getattr(response.candidates[0], 'finish_reason', None)
                if finish_reason and 'SAFETY' in str(finish_reason):
                    logger.warning("Gemini response blocked for safety reasons")
                    return dict(GEMINI_ERROR_FALLBACK)
            
            raw_text = response.text if hasattr(response, 'text') else ""
            parsed = _parse_gemini_json(raw_text)
            if parsed and isinstance(parsed, dict):
                logger.debug(
                    "Gemini response parsed OK: keys=%s",
                    list(parsed.keys()) if parsed else [],
                )
                return parsed
            logger.warning(
                "Gemini returned non-dict or empty JSON; raw response (first 500 chars): %s",
                (raw_text or "")[:500],
            )
            return dict(GEMINI_ERROR_FALLBACK)
        except Exception as e:
            # Log more specific information about the error
            error_msg = str(e)
            logger.error(
                "Gemini generation error: %s; raw response (first 500 chars): %s",
                error_msg,
                (raw_text or "")[:500],
                exc_info=True
            )
            # Check if it's a BlockedPromptException
            if "BlockedPromptException" in str(type(e)) or "blocked" in error_msg.lower():
                logger.warning("Request was blocked by Gemini safety filters")
            
            return dict(GEMINI_ERROR_FALLBACK)
