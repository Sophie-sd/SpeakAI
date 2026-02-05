"""
Vocabulary Tracker з SM-2 Spaced Repetition Algorithm
"""
from typing import Optional
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from apps.chat.models import VocabularyWord, UserVocabularyProgress, Lesson
import logging

logger = logging.getLogger(__name__)


class VocabularyTracker:
    """
    Система відстеження словникового запасу з алгоритмом SuperMemo 2 (SM-2)
    """
    
    @staticmethod
    def mark_word_encountered(user, word: VocabularyWord, lesson: Optional[Lesson] = None):
        """
        Позначити слово як зустрінуте
        
        Args:
            user: User object
            word: VocabularyWord object
            lesson: Optional Lesson object де зустрілося слово
        """
        progress, created = UserVocabularyProgress.objects.get_or_create(
            user=user,
            word=word,
            defaults={
                'status': 'new',
                'learned_from_lesson': lesson,
                'next_review_at': timezone.now()
            }
        )
        
        progress.times_seen += 1
        
        # Якщо нове слово і це перша зустріч з уроку
        if created and lesson:
            progress.learned_from_lesson = lesson
        
        # Якщо вже було забуто, повернути в learning
        if progress.status == 'forgotten':
            progress.status = 'learning'
        elif progress.status == 'new' and progress.times_seen >= 2:
            progress.status = 'learning'
        
        progress.save()
        
        logger.info(f"User {user.id} encountered word '{word.word}' ({progress.times_seen} times)")
    
    @staticmethod
    @transaction.atomic
    def mark_word_correct(user, word: VocabularyWord, quality: int = 4):
        """
        Позначити правильне використання слова
        
        Args:
            user: User object
            word: VocabularyWord object
            quality: Якість відповіді (0-5), де:
                0 - повна невдача
                1 - неправильно, але згадав
                2 - неправильно, але легко виправити
                3 - правильно з зусиллям
                4 - правильно без зусиль
                5 - ідеально
        """
        progress, created = UserVocabularyProgress.objects.get_or_create(
            user=user,
            word=word,
            defaults={
                'status': 'learning',
                'next_review_at': timezone.now()
            }
        )
        
        progress.times_correct += 1
        progress.last_reviewed_at = timezone.now()
        
        # Застосувати SM-2 алгоритм
        VocabularyTracker._calculate_next_review(progress, quality)
        
        # Оновити статус
        if progress.repetitions >= 3 and progress.ease_factor >= 2.5:
            if progress.status != 'mastered':
                progress.status = 'learned'
        elif progress.repetitions >= 5 and progress.ease_factor >= 3.0:
            progress.status = 'mastered'
        
        progress.save()
        
        logger.info(
            f"User {user.id} used word '{word.word}' correctly. "
            f"Next review in {progress.interval_days} days"
        )
    
    @staticmethod
    @transaction.atomic
    def mark_word_incorrect(user, word: VocabularyWord):
        """
        Позначити неправильне використання слова
        
        Args:
            user: User object
            word: VocabularyWord object
        """
        progress, created = UserVocabularyProgress.objects.get_or_create(
            user=user,
            word=word,
            defaults={
                'status': 'learning',
                'next_review_at': timezone.now()
            }
        )
        
        progress.times_incorrect += 1
        progress.last_reviewed_at = timezone.now()
        
        # При помилці - скинути інтервал (якість = 0)
        VocabularyTracker._calculate_next_review(progress, quality=0)
        
        # Якщо було learned/mastered, повернути до learning
        if progress.status in ['learned', 'mastered']:
            progress.status = 'learning'
        
        # Якщо багато помилок, позначити як forgotten
        if progress.times_incorrect > progress.times_correct * 2:
            progress.status = 'forgotten'
        
        progress.save()
        
        logger.info(
            f"User {user.id} used word '{word.word}' incorrectly. "
            f"Reset to {progress.interval_days} day interval"
        )
    
    @staticmethod
    def _calculate_next_review(progress: UserVocabularyProgress, quality: int):
        """
        Розрахувати наступний перегляд за алгоритмом SM-2
        
        Args:
            progress: UserVocabularyProgress object
            quality: Якість відповіді (0-5)
        """
        # Оновити Ease Factor
        new_ef = progress.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        
        # EF не може бути менше 1.3
        if new_ef < 1.3:
            new_ef = 1.3
        
        progress.ease_factor = new_ef
        
        # Розрахувати новий інтервал
        if quality < 3:
            # Невдача - скинути інтервал
            progress.repetitions = 0
            progress.interval_days = 1
        else:
            # Успіх - збільшити інтервал
            if progress.repetitions == 0:
                progress.interval_days = 1
            elif progress.repetitions == 1:
                progress.interval_days = 6
            else:
                progress.interval_days = int(progress.interval_days * progress.ease_factor)
            
            progress.repetitions += 1
        
        # Встановити дату наступного перегляду
        progress.next_review_at = timezone.now() + timedelta(days=progress.interval_days)
    
    @staticmethod
    def get_words_for_review(user, limit: int = 20):
        """
        Отримати слова для повторення сьогодні
        
        Args:
            user: User object
            limit: Максимальна кількість слів
            
        Returns:
            QuerySet of UserVocabularyProgress
        """
        now = timezone.now()
        
        return UserVocabularyProgress.objects.filter(
            user=user,
            next_review_at__lte=now
        ).select_related('word').order_by('next_review_at')[:limit]
    
    @staticmethod
    def get_vocabulary_stats(user):
        """
        Отримати статистику словника користувача
        
        Args:
            user: User object
            
        Returns:
            Dict з статистикою
        """
        from django.db.models import Count, Avg
        
        progress_qs = UserVocabularyProgress.objects.filter(user=user)
        
        stats = {
            'total_words': progress_qs.count(),
            'new': progress_qs.filter(status='new').count(),
            'learning': progress_qs.filter(status='learning').count(),
            'learned': progress_qs.filter(status='learned').count(),
            'mastered': progress_qs.filter(status='mastered').count(),
            'forgotten': progress_qs.filter(status='forgotten').count(),
            'due_for_review': progress_qs.filter(
                next_review_at__lte=timezone.now()
            ).count(),
        }
        
        # Середня точність
        total_correct = sum(p.times_correct for p in progress_qs)
        total_attempts = sum(p.times_correct + p.times_incorrect for p in progress_qs)
        
        stats['average_accuracy'] = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
        
        return stats
    
    @staticmethod
    def mark_word_as_known(user, word: VocabularyWord):
        """
        Позначити слово як вже відоме (пропустити навчання)
        
        Args:
            user: User object
            word: VocabularyWord object
        """
        progress, created = UserVocabularyProgress.objects.get_or_create(
            user=user,
            word=word
        )
        
        progress.status = 'mastered'
        progress.repetitions = 10
        progress.ease_factor = 3.0
        progress.interval_days = 180  # Перегляд через пів року
        progress.next_review_at = timezone.now() + timedelta(days=180)
        progress.save()
        
        logger.info(f"User {user.id} marked word '{word.word}' as already known")
