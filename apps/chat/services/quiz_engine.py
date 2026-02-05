"""
Quiz Engine для оцінювання квізів та обробки відповідей
"""
from typing import Dict, Any, List
from django.utils import timezone
from django.db import transaction
from apps.chat.models import Quiz, Question, QuizAttempt, QuestionResponse
import logging

logger = logging.getLogger(__name__)


class QuizEngine:
    """Движок для роботи з квізами"""
    
    @staticmethod
    def start_quiz(quiz: Quiz, user: Any) -> QuizAttempt:
        """
        Почати новий квіз
        
        Args:
            quiz: Об'єкт Quiz
            user: Об'єкт користувача
            
        Returns:
            QuizAttempt object
        """
        attempt = QuizAttempt.objects.create(
            user=user,
            quiz=quiz
        )
        
        logger.info(f"Started quiz {quiz.id} for user {user.id}, attempt {attempt.id}")
        return attempt
    
    @staticmethod
    def submit_answer(
        attempt: QuizAttempt,
        question: Question,
        user_answer: Dict[str, Any]
    ) -> QuestionResponse:
        """
        Зберегти відповідь на питання
        
        Args:
            attempt: QuizAttempt object
            question: Question object
            user_answer: Dict з відповіддю користувача
            
        Returns:
            QuestionResponse object
        """
        if attempt.completed_at:
            raise ValueError("Cannot submit answer to completed quiz")
        
        # Перевірити відповідь
        is_correct, points_earned = question.check_answer(user_answer)
        
        # Створити або оновити відповідь
        response, created = QuestionResponse.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={
                'user_answer': user_answer,
                'is_correct': is_correct,
                'points_earned': points_earned
            }
        )
        
        logger.debug(
            f"Answer submitted for attempt {attempt.id}, "
            f"question {question.id}: correct={is_correct}, points={points_earned}"
        )
        
        return response
    
    @staticmethod
    @transaction.atomic
    def complete_quiz(attempt: QuizAttempt) -> Dict[str, Any]:
        """
        Завершити квіз та розрахувати результат
        
        Args:
            attempt: QuizAttempt object
            
        Returns:
            Dict з результатами
        """
        if attempt.completed_at:
            raise ValueError("Quiz already completed")
        
        # Розрахувати час
        time_spent = (timezone.now() - attempt.started_at).total_seconds()
        attempt.time_spent_seconds = int(time_spent)
        
        # Розрахувати оцінку
        score, passed = attempt.calculate_score()
        attempt.score = score
        attempt.passed = passed
        attempt.completed_at = timezone.now()
        
        # Зберегти всі відповіді в answers field
        answers_data = {}
        for response in attempt.responses.all():
            answers_data[str(response.question.id)] = {
                'question_order': response.question.order,
                'user_answer': response.user_answer,
                'is_correct': response.is_correct,
                'points_earned': response.points_earned
            }
        attempt.answers = answers_data
        attempt.save()
        
        # Оновити progress уроку
        from apps.chat.models import UserLessonProgress
        progress, created = UserLessonProgress.objects.get_or_create(
            user=attempt.user,
            lesson=attempt.quiz.lesson
        )
        
        # Зберегти кращу оцінку
        if not hasattr(progress, 'quiz_score') or score > progress.quiz_score:
            # Note: quiz_score field не існує в UserLessonProgress
            # Можна додати пізніше або використовувати іншу логіку
            pass
        
        result = {
            'attempt_id': attempt.id,
            'score': score,
            'passed': passed,
            'time_spent_seconds': attempt.time_spent_seconds,
            'total_questions': attempt.quiz.questions.count(),
            'correct_answers': attempt.responses.filter(is_correct=True).count(),
            'total_points': attempt.quiz.total_points,
            'earned_points': sum(r.points_earned for r in attempt.responses.all()),
            'passing_score': attempt.quiz.passing_score
        }
        
        logger.info(
            f"Completed quiz {attempt.quiz.id} for user {attempt.user.id}: "
            f"score={score}, passed={passed}"
        )
        
        return result
    
    @staticmethod
    def get_quiz_results(attempt: QuizAttempt) -> Dict[str, Any]:
        """
        Отримати детальні результати квізу
        
        Args:
            attempt: QuizAttempt object
            
        Returns:
            Dict з детальними результатами
        """
        responses = attempt.responses.select_related('question').order_by('question__order')
        
        questions_results = []
        for response in responses:
            questions_results.append({
                'question_id': response.question.id,
                'question_text': response.question.question_text,
                'question_type': response.question.question_type,
                'user_answer': response.user_answer,
                'correct_answer': response.question.correct_answer,
                'is_correct': response.is_correct,
                'points': response.question.points,
                'points_earned': response.points_earned,
                'explanation': response.question.explanation
            })
        
        return {
            'attempt_id': attempt.id,
            'quiz_title': attempt.quiz.title,
            'score': attempt.score,
            'passed': attempt.passed,
            'time_spent_seconds': attempt.time_spent_seconds,
            'started_at': attempt.started_at.isoformat(),
            'completed_at': attempt.completed_at.isoformat() if attempt.completed_at else None,
            'questions': questions_results,
            'statistics': {
                'total_questions': len(questions_results),
                'correct_answers': sum(1 for q in questions_results if q['is_correct']),
                'total_points': attempt.quiz.total_points,
                'earned_points': sum(q['points_earned'] for q in questions_results),
                'passing_score': attempt.quiz.passing_score
            }
        }
    
    @staticmethod
    def check_time_limit(attempt: QuizAttempt) -> bool:
        """
        Перевірити чи не вийшов ліміт часу
        
        Args:
            attempt: QuizAttempt object
            
        Returns:
            True якщо ліміт не вийшов, False якщо вийшов
        """
        if not attempt.quiz.time_limit_minutes:
            return True
        
        if attempt.completed_at:
            return True
        
        elapsed = (timezone.now() - attempt.started_at).total_seconds() / 60
        return elapsed <= attempt.quiz.time_limit_minutes
