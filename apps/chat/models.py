from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from pgvector.django import VectorField
from .validators import (
    validate_homework_instructions,
    validate_role_play_scenario,
    validate_voice_practice_prompts
)

# Визначення рівнів CEFR локально (уникнення циклічного імпорту)
CEFR_LEVELS = [
    ('A0', 'Starter'),
    ('A1', 'Elementary'),
    ('A2', 'Pre-Intermediate'),
    ('B1', 'Intermediate'),
    ('B2', 'Upper-Intermediate'),
    ('C1', 'Advanced'),
    ('C2', 'Proficiency'),
]

LESSON_CONTENT_TYPES = [
    ('theory', 'Теорія (відео/текст)'),
    ('voice_practice', 'Голосова практика'),
    ('role_play', 'Рольова гра'),
    ('homework', 'Домашнє завдання'),
    ('quiz', 'Тест'),
]


class KnowledgeBase(models.Model):
    """База знань для RAG (тематичні статті, граматичні правила, культура)"""
    topic = models.CharField(max_length=255)
    content = models.TextField()
    # Gemini embeddings are 768 dimensions. 
    # Using VectorField requires pgvector extension in Postgres.
    # For SQLite, this might need handling or it won't work.
    embedding = VectorField(dimensions=768, null=True, blank=True) 
    image = models.ImageField(upload_to='knowledge_images/', null=True, blank=True)
    
    # RAG filtering (Phase 2.7)
    level = models.CharField(
        max_length=2,
        choices=CEFR_LEVELS,
        default='A1',
        help_text="Рівень складності контенту"
    )
    is_universal = models.BooleanField(
        default=False,
        help_text="Чи доступний для всіх рівнів"
    )
    
    # M2M relation з Module (Phase 2.8)
    modules = models.ManyToManyField(
        'Module',
        related_name='knowledge_items',
        blank=True,
        help_text="Модулі, до яких належить цей контент"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.topic


class Module(models.Model):
    """
    Модуль навчання (наприклад, "My World", "Travel & Experience")
    """
    title = models.CharField(max_length=255, verbose_name="Назва модуля")
    description = models.TextField(blank=True, verbose_name="Опис модуля")
    level = models.CharField(max_length=2, choices=CEFR_LEVELS, verbose_name="Рівень CEFR")
    module_number = models.IntegerField(verbose_name="Номер модуля в рівні")
    
    # Статистика модуля
    total_lessons = models.IntegerField(default=0, verbose_name="Кількість уроків")
    estimated_duration_weeks = models.IntegerField(
        default=2, 
        verbose_name="Очікувана тривалість (тижні)"
    )
    
    # Мета навчання
    learning_objectives = models.JSONField(
        default=list,
        blank=True,
        help_text="Список цілей навчання (JSON array)"
    )
    
    # Прапорці
    is_active = models.BooleanField(default=True)
    is_premium_only = models.BooleanField(default=True, verbose_name="Тільки для преміум")
    
    # Порядок відображення
    order = models.IntegerField(default=0, help_text="Порядок сортування")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['level', 'module_number']
        unique_together = ['level', 'module_number']
        verbose_name = "Модуль"
        verbose_name_plural = "Модулі"
    
    def __str__(self):
        return f"{self.level} - Module {self.module_number}: {self.title}"


class Lesson(models.Model):
    """
    Урок в модулі (наприклад, "Hello!", "Family", "Food")
    """
    module = models.ForeignKey(
        Module, 
        on_delete=models.CASCADE, 
        related_name='lessons',
        verbose_name="Модуль"
    )
    
    # Базова інформація
    lesson_number = models.IntegerField(verbose_name="Номер уроку")
    title = models.CharField(max_length=255, verbose_name="Тема уроку")
    description = models.TextField(blank=True, verbose_name="Опис уроку")
    
    # Навчальний контент
    grammar_focus = models.TextField(
        blank=True,
        verbose_name="Фокус граматики",
        help_text="Наприклад: 'Verb to be, Greetings'"
    )
    
    vocabulary_list = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Список слів",
        help_text="JSON array слів для вивчення"
    )
    
    vocabulary_count = models.IntegerField(
        default=0,
        verbose_name="Кількість слів для вивчення"
    )
    
    # Теоретична частина
    theory_content = models.TextField(
        blank=True,
        verbose_name="Теоретичний матеріал",
        help_text="Може бути в Markdown форматі"
    )
    
    theory_video_url = models.URLField(
        blank=True,
        verbose_name="Відео урок (Cloudinary URL)"
    )
    
    # AI Voice Practice
    voice_practice_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Тип голосової практики",
        help_text="Наприклад: 'Drill', 'Q&A', 'Story Chain', 'Shadowing'"
    )
    
    voice_practice_instructions = models.TextField(
        blank=True,
        verbose_name="Інструкції для голосової практики"
    )
    
    voice_practice_prompts = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Промпти для AI",
        help_text="Список промптів для генерації AI діалогу",
        validators=[validate_voice_practice_prompts]
    )
    
    # AI Role-Play Scenario
    role_play_scenario_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Назва сценарію",
        help_text="Наприклад: 'Coffee Shop Encounter', 'The Lost Tourist'"
    )
    
    role_play_scenario = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Сценарій рольової гри",
        help_text="JSON: {'setting': 'опис місця', 'ai_role': 'роль AI', 'user_role': 'роль користувача', 'objectives': [], 'difficulty': 'easy/medium/hard'}",
        validators=[validate_role_play_scenario]
    )
    
    # Домашнє завдання
    homework_description = models.TextField(
        blank=True,
        verbose_name="Опис домашнього завдання"
    )
    
    homework_instructions = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Інструкції для AI перевірки",
        help_text="Критерії оцінювання домашнього завдання",
        validators=[validate_homework_instructions]
    )
    
    # Зв'язок з Knowledge Base
    knowledge_base_items = models.ManyToManyField(
        'KnowledgeBase',
        blank=True,
        related_name='lessons',
        verbose_name="Зв'язані матеріали Knowledge Base"
    )
    
    # Метадані
    estimated_duration_minutes = models.IntegerField(
        default=60,
        verbose_name="Очікувана тривалість (хвилини)"
    )
    
    difficulty_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Початковий'),
            ('intermediate', 'Середній'),
            ('advanced', 'Складний'),
        ],
        default='beginner'
    )
    
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['module', 'lesson_number']
        unique_together = ['module', 'lesson_number']
        verbose_name = "Урок"
        verbose_name_plural = "Уроки"
    
    def __str__(self):
        return f"{self.module.level} - Lesson {self.lesson_number}: {self.title}"
    
    def get_next_lesson(self):
        """Отримати наступний урок"""
        return Lesson.objects.filter(
            module=self.module,
            lesson_number__gt=self.lesson_number
        ).first()
    
    def get_previous_lesson(self):
        """Отримати попередній урок"""
        return Lesson.objects.filter(
            module=self.module,
            lesson_number__lt=self.lesson_number
        ).order_by('-lesson_number').first()


class UserLessonProgress(models.Model):
    """
    Прогрес користувача по конкретному уроку
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lesson_progress'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='user_progress'
    )
    
    # Статус виконання
    STATUS_CHOICES = [
        ('not_started', 'Не розпочато'),
        ('in_progress', 'В процесі'),
        ('completed', 'Завершено'),
        ('mastered', 'Освоєно'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='not_started'
    )
    
    # Прогрес по компонентах уроку
    theory_completed = models.BooleanField(default=False)
    voice_practice_completed = models.BooleanField(default=False)
    role_play_completed = models.BooleanField(default=False)
    homework_completed = models.BooleanField(default=False)
    
    # Оцінки та результати
    voice_practice_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        help_text="Оцінка за голосову практику (0-10)"
    )
    
    role_play_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        help_text="Оцінка за рольову гру (0-10)"
    )
    
    homework_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        help_text="Оцінка за домашнє завдання (0-10)"
    )
    
    quiz_completed = models.BooleanField(default=False)
    quiz_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        help_text="Оцінка за тест (0-10)"
    )
    
    overall_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        help_text="Загальна оцінка за урок (0-10)"
    )
    
    # Кількість спроб
    attempts_count = models.IntegerField(default=0)
    
    # AI фідбек
    ai_feedback = models.JSONField(
        default=dict,
        blank=True,
        help_text="Зворотний зв'язок від AI по компонентах уроку"
    )
    
    # Детальний фідбек за Voice Practice та Role-Play
    voice_practice_feedback = models.JSONField(
        null=True,
        blank=True,
        help_text="Детальний фідбек за голосову практику (оцінки, помилки, рекомендації)"
    )
    
    role_play_feedback = models.JSONField(
        null=True,
        blank=True,
        help_text="Детальний фідбек за рольову гру (оцінки, помилки, рекомендації)"
    )
    
    # Часові мітки
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    # Час витрачений на урок
    time_spent_minutes = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['user', 'lesson']
        ordering = ['-last_activity']
        verbose_name = "Прогрес по уроку"
        verbose_name_plural = "Прогрес по урокам"
    
    def __str__(self):
        return f"{self.user.username} - {self.lesson.title} ({self.status})"
    
    def calculate_overall_score(self):
        """Розрахувати загальну оцінку"""
        scores = [
            s for s in [
                self.voice_practice_score,
                self.role_play_score,
                self.homework_score,
                self.quiz_score
            ] if s is not None
        ]
        if scores:
            self.overall_score = sum(scores) / len(scores)
            self.save(update_fields=['overall_score'])


class UserModuleProgress(models.Model):
    """
    Прогрес користувача по модулю
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='module_progress'
    )
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='user_progress'
    )
    
    # Статус модуля
    STATUS_CHOICES = [
        ('locked', 'Заблоковано'),
        ('available', 'Доступно'),
        ('in_progress', 'В процесі'),
        ('completed', 'Завершено'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='locked'
    )
    
    # Статистика
    lessons_total = models.IntegerField(default=0)
    lessons_completed = models.IntegerField(default=0)
    progress_percentage = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    
    # Середня оцінка по модулю
    average_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)]
    )
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'module']
        ordering = ['module__level', 'module__module_number']
        verbose_name = "Прогрес по модулю"
        verbose_name_plural = "Прогрес по модулях"
    
    def __str__(self):
        return f"{self.user.username} - {self.module.title} ({self.progress_percentage}%)"
    
    def update_progress(self):
        """Оновити прогрес по модулю"""
        from django.utils import timezone
        
        completed_lessons = UserLessonProgress.objects.filter(
            user=self.user,
            lesson__module=self.module,
            status='completed'
        ).count()
        
        self.lessons_completed = completed_lessons
        self.lessons_total = self.module.total_lessons
        
        if self.lessons_total > 0:
            self.progress_percentage = (completed_lessons / self.lessons_total) * 100
        
        if self.progress_percentage >= 100:
            self.status = 'completed'
            if not self.completed_at:
                self.completed_at = timezone.now()
        elif self.progress_percentage > 0:
            self.status = 'in_progress'
        
        self.save()


class RolePlaySession(models.Model):
    """
    Сесія рольової гри (окремий діалог з AI в сценарії)
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='roleplay_sessions'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='roleplay_sessions'
    )
    
    # Базова інформація
    scenario_name = models.CharField(max_length=255)
    session_number = models.IntegerField(default=1)
    
    # System prompt для відновлення контексту (Phase 1.3)
    system_prompt = models.TextField(
        blank=True,
        help_text="System prompt для Gemini API (зберігається для відновлення контексту)"
    )
    
    # Messages history для Gemini API (Phase 1.3)
    messages_history = models.JSONField(
        default=list,
        help_text="JSON: [{'role': 'user'/'model', 'content': 'текст'}] - формат для Gemini API"
    )
    
    # Діалог для відображення користувачу (deprecated, use messages_history)
    dialogue = models.JSONField(
        default=list,
        help_text="JSON: [{'role': 'user'/'ai', 'content': 'текст', 'timestamp': 'ISO datetime', 'audio_url': 'optional'}]"
    )
    
    # Оцінка AI
    ai_evaluation = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON з оцінками: grammar_score, vocabulary_score, fluency_score, overall_score, strengths, improvements, feedback"
    )
    
    overall_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)]
    )
    
    # Статус
    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('completed', 'Завершена'),
        ('abandoned', 'Покинута'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    
    # Часові мітки
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=0)
    
    # Метадані
    messages_count = models.IntegerField(default=0)
    user_messages_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-started_at']
        verbose_name = "Сесія рольової гри"
        verbose_name_plural = "Сесії рольових ігор"
    
    def __str__(self):
        return f"{self.user.username} - {self.scenario_name} (Session {self.session_number})"


class PronunciationAttempt(models.Model):
    """
    Спроба користувача відпрацювати вимову
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pronunciation_attempts'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='pronunciation_attempts',
        null=True,
        blank=True
    )
    
    # Аудіо та текст
    audio_url = models.URLField(verbose_name="Аудіо запис користувача")
    target_text = models.TextField(verbose_name="Цільова фраза для вимови")
    transcribed_text = models.TextField(
        blank=True,
        verbose_name="Розпізнаний текст (STT)"
    )
    
    # Оцінка вимови
    pronunciation_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Оцінка вимови (0-100)"
    )
    
    accuracy_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Точність слів"
    )
    
    fluency_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Плавність мовлення"
    )
    
    # Детальний аналіз
    pronunciation_analysis = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON: {'phonemes': [], 'words': [], 'improvements': []}"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Спроба вимови"
        verbose_name_plural = "Спроби вимови"


class Memory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memories')
    fact = models.TextField()
    memory_type = models.CharField(
        max_length=20,
        choices=[
            ('error', 'Типова помилка'),
            ('mastered', 'Освоєний навик'),
            ('interest', 'Інтерес'),
            ('goal', 'Ціль'),
            ('progress', 'Прогрес'),
        ],
        default='interest'
    )
    frequency = models.IntegerField(default=1, help_text="Скільки разів згадувалось")
    last_mentioned = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Для категоризації помилок
    error_category = models.CharField(
        max_length=50,
        blank=True,
        help_text="grammar_tense, vocabulary, pronunciation, word_order"
    )
    
    class Meta:
        verbose_name_plural = "Memories"
        ordering = ['-last_mentioned']

    def __str__(self):
        return f"{self.user.username} - {self.fact[:50]}"

class ChatSession(models.Model):
    SESSION_TYPE_CHOICES = [
        ('general', 'General Chat'),
        ('voice', 'Voice Chat'),
        ('lesson_voice_practice', 'Lesson Voice Practice'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_sessions')
    lesson = models.ForeignKey(
        Lesson, 
        on_delete=models.CASCADE, 
        related_name='chat_sessions',
        null=True,
        blank=True,
        help_text="Урок, якщо це сесія Voice Practice для конкретного уроку"
    )
    title = models.CharField(max_length=255, blank=True)
    session_type = models.CharField(
        max_length=50,
        choices=SESSION_TYPE_CHOICES,
        default='general',
        help_text="Тип сесії: генеральний чат, голосовий чат або голосова практика до уроку"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Активна сесія (можна продовжити) або завершена"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.title or self.session_type} ({self.created_at.strftime('%Y-%m-%d')})"

class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('model', 'Model'),
    ]
    SOURCE_TYPE_CHOICES = [
        ('text', 'Text Chat'),
        ('voice', 'Voice Chat'),
    ]
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    audio_url = models.URLField(null=True, blank=True)
    image_shown = models.ForeignKey(KnowledgeBase, on_delete=models.SET_NULL, null=True, blank=True)
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES, default='text')
    transcript = models.TextField(blank=True, help_text="Voice transcription or phase metadata (initial/detailed_explanation/practice)")
    translation = models.TextField(blank=True, null=True, help_text="Ukrainian translation of AI response")
    explanation = models.TextField(blank=True, null=True, help_text="Grammar explanation in Ukrainian")
    corrected_text = models.TextField(blank=True, null=True, help_text="Corrected version of user input")
    full_english_version = models.TextField(blank=True, null=True, help_text="Full phrase in English (for mixed language input)")
    has_errors = models.BooleanField(default=False, help_text="Indicates if message contains errors that need correction")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role}: {self.content[:20]}"


# ============================================
# Quiz/Test Models (Phase 1.1)
# ============================================

class Quiz(models.Model):
    """
    Квіз/тест для уроку
    """
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='quizzes',
        verbose_name="Урок"
    )
    title = models.CharField(max_length=255, verbose_name="Назва квізу")
    description = models.TextField(blank=True, verbose_name="Опис квізу")
    passing_score = models.FloatField(
        default=6.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        verbose_name="Прохідний бал (0-10)"
    )
    time_limit_minutes = models.IntegerField(
        null=True,
        blank=True,
        help_text="Ліміт часу в хвилинах (null = без ліміту)"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активний")
    order = models.IntegerField(default=0, help_text="Порядок відображення")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['lesson', 'order']
        verbose_name = "Квіз"
        verbose_name_plural = "Квізи"
    
    def __str__(self):
        return f"{self.lesson.title} - {self.title}"
    
    @property
    def total_points(self):
        """Загальна кількість балів за всі питання"""
        return self.questions.aggregate(total=models.Sum('points'))['total'] or 0


class Question(models.Model):
    """
    Питання в квізі
    """
    QUESTION_TYPES = [
        ('multiple_choice', 'Множинний вибір'),
        ('true_false', 'Правда/Неправда'),
        ('fill_blank', 'Заповнити пропуск'),
        ('matching', 'Співставлення'),
    ]
    
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name="Квіз"
    )
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        verbose_name="Тип питання"
    )
    question_text = models.TextField(verbose_name="Текст питання")
    options = models.JSONField(
        default=dict,
        help_text="Варіанти відповідей (JSON). Формат залежить від типу питання"
    )
    correct_answer = models.JSONField(
        help_text="Правильна відповідь (JSON). Формат залежить від типу питання"
    )
    points = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0)],
        verbose_name="Бали за питання"
    )
    explanation = models.TextField(
        blank=True,
        verbose_name="Пояснення правильної відповіді"
    )
    order = models.IntegerField(default=0, help_text="Порядок питання в квізі")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['quiz', 'order']
        verbose_name = "Питання"
        verbose_name_plural = "Питання"
    
    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}"
    
    def check_answer(self, user_answer):
        """
        Перевірити відповідь користувача
        Returns: (is_correct: bool, points_earned: float)
        """
        if self.question_type == 'multiple_choice':
            # correct_answer: {"answer": "option_id"}
            # user_answer: {"answer": "option_id"}
            is_correct = user_answer.get('answer') == self.correct_answer.get('answer')
            
        elif self.question_type == 'true_false':
            # correct_answer: {"answer": true/false}
            # user_answer: {"answer": true/false}
            is_correct = user_answer.get('answer') == self.correct_answer.get('answer')
            
        elif self.question_type == 'fill_blank':
            # correct_answer: {"answer": "text", "alternatives": ["alt1", "alt2"]}
            # user_answer: {"answer": "text"}
            correct = self.correct_answer.get('answer', '').lower().strip()
            alternatives = [alt.lower().strip() for alt in self.correct_answer.get('alternatives', [])]
            user_ans = user_answer.get('answer', '').lower().strip()
            is_correct = user_ans == correct or user_ans in alternatives
            
        elif self.question_type == 'matching':
            # correct_answer: {"pairs": [{"left": "id1", "right": "id2"}, ...]}
            # user_answer: {"pairs": [{"left": "id1", "right": "id2"}, ...]}
            correct_pairs = {(p['left'], p['right']) for p in self.correct_answer.get('pairs', [])}
            user_pairs = {(p['left'], p['right']) for p in user_answer.get('pairs', [])}
            is_correct = correct_pairs == user_pairs
        else:
            is_correct = False
        
        points_earned = self.points if is_correct else 0.0
        return is_correct, points_earned


class QuizAttempt(models.Model):
    """
    Спроба проходження квізу користувачем
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quiz_attempts',
        verbose_name="Користувач"
    )
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='attempts',
        verbose_name="Квіз"
    )
    score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        verbose_name="Оцінка (0-10)"
    )
    passed = models.BooleanField(default=False, verbose_name="Здано")
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Початок")
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Завершення"
    )
    time_spent_seconds = models.IntegerField(
        default=0,
        verbose_name="Витрачено часу (сек)"
    )
    answers = models.JSONField(
        default=dict,
        help_text="Всі відповіді користувача (JSON)"
    )
    
    class Meta:
        ordering = ['-started_at']
        verbose_name = "Спроба квізу"
        verbose_name_plural = "Спроби квізів"
    
    def __str__(self):
        status = "Completed" if self.completed_at else "In Progress"
        return f"{self.user.username} - {self.quiz.title} ({status})"
    
    def calculate_score(self):
        """
        Розрахувати оцінку на основі відповідей
        Returns: (score: float, passed: bool)
        """
        total_points = self.quiz.total_points
        if total_points == 0:
            return 0.0, False
        
        # Підрахувати зароблені бали
        earned_points = sum(
            response.points_earned 
            for response in self.responses.all()
        )
        
        # Конвертувати в шкалу 0-10
        score = (earned_points / total_points) * 10.0
        passed = score >= self.quiz.passing_score
        
        return score, passed


class QuestionResponse(models.Model):
    """
    Відповідь користувача на питання
    """
    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name="Спроба"
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name="Питання"
    )
    user_answer = models.JSONField(
        help_text="Відповідь користувача (JSON)"
    )
    is_correct = models.BooleanField(default=False, verbose_name="Правильно")
    points_earned = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0)],
        verbose_name="Зароблено балів"
    )
    answered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['question__order']
        unique_together = ['attempt', 'question']
        verbose_name = "Відповідь на питання"
        verbose_name_plural = "Відповіді на питання"
    
    def __str__(self):
        return f"{self.attempt.user.username} - Q{self.question.order} ({'✓' if self.is_correct else '✗'})"


# ============================================
# Homework Submission Models (Phase 1.2)
# ============================================

class HomeworkSubmission(models.Model):
    """
    Подання домашнього завдання користувачем
    """
    STATUS_CHOICES = [
        ('pending', 'Очікує оцінювання'),
        ('evaluated', 'Оцінено'),
        ('revised', 'Переглянуто/Виправлено'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='homework_submissions',
        verbose_name="Користувач"
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='homework_submissions',
        verbose_name="Урок"
    )
    submission_text = models.TextField(verbose_name="Текст домашнього завдання")
    attachments = models.JSONField(
        default=list,
        blank=True,
        help_text="URLs до файлів/зображень (якщо є)"
    )
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Подано")
    attempt_number = models.IntegerField(
        default=1,
        verbose_name="Номер спроби"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Статус"
    )
    
    class Meta:
        ordering = ['-submitted_at']
        verbose_name = "Подання домашнього завдання"
        verbose_name_plural = "Подання домашніх завдань"
    
    def __str__(self):
        return f"{self.user.username} - {self.lesson.title} (Attempt {self.attempt_number})"


class HomeworkFeedback(models.Model):
    """
    Зворотній зв'язок по домашньому завданню
    """
    EVALUATOR_TYPES = [
        ('ai', 'AI (Gemini)'),
        ('teacher', 'Вчитель'),
    ]
    
    submission = models.OneToOneField(
        HomeworkSubmission,
        on_delete=models.CASCADE,
        related_name='feedback',
        verbose_name="Подання"
    )
    score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        verbose_name="Оцінка (0-10)"
    )
    criteria_scores = models.JSONField(
        default=dict,
        help_text="Оцінки по критеріям (JSON)"
    )
    feedback_text = models.TextField(verbose_name="Фідбек (загальний)")
    errors = models.JSONField(
        default=list,
        help_text="Список помилок з поясненнями (JSON)"
    )
    strengths = models.JSONField(
        default=list,
        help_text="Сильні сторони (JSON list)"
    )
    improvements = models.JSONField(
        default=list,
        help_text="Рекомендації для покращення (JSON list)"
    )
    next_step = models.TextField(
        blank=True,
        verbose_name="Наступний крок у навчанні"
    )
    evaluated_at = models.DateTimeField(auto_now_add=True, verbose_name="Оцінено")
    evaluator_type = models.CharField(
        max_length=10,
        choices=EVALUATOR_TYPES,
        default='ai',
        verbose_name="Тип оцінювача"
    )
    
    class Meta:
        verbose_name = "Фідбек по домашньому завданню"
        verbose_name_plural = "Фідбеки по домашнім завданням"
    
    def __str__(self):
        return f"Feedback for {self.submission} - Score: {self.score}"


# ============================================
# Vocabulary Tracking Models (Phase 2.1)
# ============================================

class VocabularyWord(models.Model):
    """
    Слово в словнику
    """
    word = models.CharField(max_length=255, unique=True, verbose_name="Слово")
    translation_uk = models.CharField(max_length=255, verbose_name="Переклад українською")
    definition_en = models.TextField(verbose_name="Визначення англійською")
    example_sentence = models.TextField(blank=True, verbose_name="Приклад речення")
    
    WORD_TYPES = [
        ('noun', 'Noun'),
        ('verb', 'Verb'),
        ('adjective', 'Adjective'),
        ('adverb', 'Adverb'),
        ('preposition', 'Preposition'),
        ('conjunction', 'Conjunction'),
        ('pronoun', 'Pronoun'),
        ('interjection', 'Interjection'),
        ('phrase', 'Phrase'),
    ]
    word_type = models.CharField(
        max_length=20,
        choices=WORD_TYPES,
        default='noun',
        verbose_name="Частина мови"
    )
    
    CEFR_LEVELS = [
        ('A0', 'A0 - Starter'),
        ('A1', 'A1 - Beginner'),
        ('A2', 'A2 - Elementary'),
        ('B1', 'B1 - Intermediate'),
        ('B2', 'B2 - Upper Intermediate'),
        ('C1', 'C1 - Advanced'),
        ('C2', 'C2 - Proficient'),
    ]
    difficulty_level = models.CharField(
        max_length=2,
        choices=CEFR_LEVELS,
        default='A1',
        verbose_name="Рівень складності"
    )
    
    frequency_rank = models.IntegerField(
        null=True,
        blank=True,
        help_text="Частота використання (1 = найпопулярніше)"
    )
    
    audio_url = models.URLField(
        null=True,
        blank=True,
        verbose_name="URL аудіо вимови"
    )
    
    image_url = models.URLField(
        null=True,
        blank=True,
        verbose_name="URL зображення"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['word']
        verbose_name = "Словникове слово"
        verbose_name_plural = "Словникові слова"
    
    def __str__(self):
        return f"{self.word} ({self.difficulty_level})"


class LessonVocabulary(models.Model):
    """
    Зв'язок між уроком та словом
    """
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='vocabulary_items',
        verbose_name="Урок"
    )
    word = models.ForeignKey(
        VocabularyWord,
        on_delete=models.CASCADE,
        related_name='lesson_usages',
        verbose_name="Слово"
    )
    is_primary = models.BooleanField(
        default=True,
        help_text="Основне слово уроку чи додаткове"
    )
    context = models.TextField(
        blank=True,
        verbose_name="Контекст використання в уроці"
    )
    order = models.IntegerField(default=0, help_text="Порядок в списку")
    
    class Meta:
        ordering = ['lesson', 'order']
        unique_together = ['lesson', 'word']
        verbose_name = "Словник уроку"
        verbose_name_plural = "Словники уроків"
    
    def __str__(self):
        return f"{self.lesson.title} - {self.word.word}"


class UserVocabularyProgress(models.Model):
    """
    Прогрес користувача по словам (Spaced Repetition)
    """
    STATUS_CHOICES = [
        ('new', 'Нове'),
        ('learning', 'Вивчається'),
        ('learned', 'Вивчено'),
        ('mastered', 'Засвоєно'),
        ('forgotten', 'Забуто'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vocabulary_progress',
        verbose_name="Користувач"
    )
    word = models.ForeignKey(
        VocabularyWord,
        on_delete=models.CASCADE,
        related_name='user_progress',
        verbose_name="Слово"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name="Статус"
    )
    
    # Статистика
    times_seen = models.IntegerField(
        default=0,
        verbose_name="Скільки разів зустрічалося"
    )
    times_correct = models.IntegerField(
        default=0,
        verbose_name="Скільки разів правильно використано"
    )
    times_incorrect = models.IntegerField(
        default=0,
        verbose_name="Скільки разів неправильно"
    )
    
    # Spaced Repetition (SM-2 algorithm)
    last_reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Останній перегляд"
    )
    next_review_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Наступний перегляд"
    )
    ease_factor = models.FloatField(
        default=2.5,
        help_text="Ease Factor для SM-2 алгоритму"
    )
    interval_days = models.IntegerField(
        default=1,
        help_text="Інтервал повторення в днях"
    )
    repetitions = models.IntegerField(
        default=0,
        help_text="Кількість успішних повторень підряд"
    )
    
    learned_from_lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vocabulary_learned',
        verbose_name="Вивчено з уроку"
    )
    
    first_seen_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['next_review_at']
        unique_together = ['user', 'word']
        verbose_name = "Прогрес по словнику"
        verbose_name_plural = "Прогрес по словнику"
    
    def __str__(self):
        return f"{self.user.username} - {self.word.word} ({self.status})"
    
    @property
    def accuracy(self):
        """Точність використання слова (%)"""
        total = self.times_correct + self.times_incorrect
        if total == 0:
            return 0
        return (self.times_correct / total) * 100
    
    @property
    def is_due_for_review(self):
        """Чи потрібно повторити слово сьогодні"""
        if not self.next_review_at:
            return True
        return timezone.now() >= self.next_review_at


# ============================================
# Achievements & Gamification (Phase 3.1)
# ============================================

class Achievement(models.Model):
    """Досягнення для користувачів"""
    CATEGORIES = [
        ('progress', 'Progress'),
        ('streak', 'Streak'),
        ('mastery', 'Mastery'),
        ('social', 'Social'),
    ]
    TIERS = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ]
    
    code = models.CharField(max_length=100, unique=True)
    title_en = models.CharField(max_length=255)
    title_uk = models.CharField(max_length=255)
    description_en = models.TextField()
    description_uk = models.TextField()
    icon = models.CharField(max_length=50, help_text="Emoji або URL")
    points = models.IntegerField(default=10, help_text="Бали за досягнення")
    category = models.CharField(max_length=20, choices=CATEGORIES)
    tier = models.CharField(max_length=20, choices=TIERS)
    requirements = models.JSONField(help_text="Умови для отримання")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', 'tier']
        verbose_name = "Досягнення"
        verbose_name_plural = "Досягнення"
    
    def __str__(self):
        return f"{self.title_uk} ({self.tier})"


class UserAchievement(models.Model):
    """Досягнення користувача"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='achievements'
    )
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)
    progress = models.FloatField(
        default=100.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Прогрес для прогресивних досягнень (0-100)"
    )
    is_notified = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-unlocked_at']
        unique_together = ['user', 'achievement']
        verbose_name = "Досягнення користувача"
        verbose_name_plural = "Досягнення користувачів"
    
    def __str__(self):
        return f"{self.user.username} - {self.achievement.title_en}"


class LearningStreak(models.Model):
    """Стрік користувача"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_streak'
    )
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(auto_now=True)
    total_active_days = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Стрік навчання"
        verbose_name_plural = "Стріки навчання"
    
    def __str__(self):
        return f"{self.user.username} - {self.current_streak} days"


class DailyActivity(models.Model):
    """Денна активність користувача"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='daily_activities'
    )
    date = models.DateField()
    lessons_completed = models.IntegerField(default=0)
    time_spent_minutes = models.IntegerField(default=0)
    homework_submitted = models.IntegerField(default=0)
    roleplay_sessions = models.IntegerField(default=0)
    voice_practice_sessions = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['user', 'date']
        verbose_name = "Денна активність"
        verbose_name_plural = "Денна активність"
    
    def __str__(self):
        return f"{self.user.username} - {self.date}"


class UserFeedback(models.Model):
    """Відгуки користувачів"""
    FEEDBACK_TYPES = [
        ('lesson_difficulty', 'Складність уроку'),
        ('ai_quality', 'Якість AI'),
        ('bug_report', 'Звіт про помилку'),
        ('suggestion', 'Пропозиція'),
    ]
    SENTIMENTS = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    feedback_type = models.CharField(max_length=50, choices=FEEDBACK_TYPES)
    target_type = models.CharField(max_length=50)
    target_id = models.IntegerField()
    rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    sentiment = models.CharField(max_length=20, choices=SENTIMENTS, default='neutral')
    created_at = models.DateTimeField(auto_now_add=True)
    is_reviewed = models.BooleanField(default=False)
    admin_response = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Відгук користувача"
        verbose_name_plural = "Відгуки користувачів"
    
    def __str__(self):
        return f"{self.user.username} - {self.feedback_type} ({self.created_at.date()})"
