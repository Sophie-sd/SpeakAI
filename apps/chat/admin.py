from django.contrib import admin
from .models import (
    KnowledgeBase, ChatSession, ChatMessage, Memory,
    Module, Lesson, UserLessonProgress, UserModuleProgress,
    RolePlaySession, PronunciationAttempt,
    Quiz, Question, QuizAttempt, QuestionResponse,
    HomeworkSubmission, HomeworkFeedback,
    VocabularyWord, LessonVocabulary, UserVocabularyProgress
)


# Existing registrations
admin.site.register(KnowledgeBase)
admin.site.register(ChatSession)
admin.site.register(ChatMessage)
admin.site.register(Memory)


# Learning Program Admin

class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ['lesson_number', 'title', 'grammar_focus', 'vocabulary_count', 'is_active']
    readonly_fields = ['vocabulary_count']


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = [
        'level', 'module_number', 'title', 
        'total_lessons', 'estimated_duration_weeks', 'is_active'
    ]
    list_filter = ['level', 'is_active', 'is_premium_only']
    search_fields = ['title', 'description']
    ordering = ['level', 'module_number']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'level', 'module_number')
        }),
        ('Content', {
            'fields': ('total_lessons', 'estimated_duration_weeks', 'learning_objectives')
        }),
        ('Settings', {
            'fields': ('is_active', 'is_premium_only', 'order')
        }),
    )
    
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = [
        'module', 'lesson_number', 'title', 
        'grammar_focus', 'vocabulary_count', 'is_active'
    ]
    list_filter = ['module__level', 'is_active', 'difficulty_level']
    search_fields = ['title', 'grammar_focus']
    ordering = ['module__level', 'module__module_number', 'lesson_number']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('module', 'lesson_number', 'title', 'description')
        }),
        ('Learning Content', {
            'fields': (
                'grammar_focus', 'vocabulary_list', 'vocabulary_count',
                'theory_content', 'theory_video_url'
            )
        }),
        ('Voice Practice', {
            'fields': (
                'voice_practice_type', 'voice_practice_instructions',
                'voice_practice_prompts'
            ),
            'classes': ('collapse',)
        }),
        ('Role-Play Scenario', {
            'fields': (
                'role_play_scenario_name', 'role_play_scenario'
            ),
            'classes': ('collapse',)
        }),
        ('Homework', {
            'fields': ('homework_description', 'homework_instructions'),
            'classes': ('collapse',)
        }),
        ('Knowledge Base', {
            'fields': ('knowledge_base_items',),
            'classes': ('collapse',)
        }),
        ('Meta', {
            'fields': (
                'estimated_duration_minutes', 'difficulty_level',
                'is_active', 'order'
            )
        }),
    )
    
    filter_horizontal = ['knowledge_base_items']


@admin.register(UserLessonProgress)
class UserLessonProgressAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'lesson', 'status', 'overall_score',
        'theory_completed', 'voice_practice_completed',
        'role_play_completed', 'homework_completed'
    ]
    list_filter = ['status', 'lesson__module__level']
    search_fields = ['user__username', 'lesson__title']
    readonly_fields = ['started_at', 'completed_at', 'last_activity']


@admin.register(UserModuleProgress)
class UserModuleProgressAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'module', 'status',
        'lessons_completed', 'lessons_total',
        'progress_percentage', 'average_score'
    ]
    list_filter = ['status', 'module__level']
    search_fields = ['user__username', 'module__title']
    readonly_fields = ['started_at', 'completed_at']


@admin.register(RolePlaySession)
class RolePlaySessionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'lesson', 'scenario_name',
        'messages_count', 'overall_score', 'status', 'started_at'
    ]
    list_filter = ['status', 'lesson__module__level']
    search_fields = ['user__username', 'scenario_name']
    readonly_fields = ['started_at', 'completed_at']


@admin.register(PronunciationAttempt)
class PronunciationAttemptAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'lesson', 'target_text',
        'pronunciation_score', 'accuracy_score', 'fluency_score',
        'created_at'
    ]
    list_filter = ['lesson__module__level']
    search_fields = ['user__username', 'target_text']
    readonly_fields = ['created_at']


# Quiz/Test Admin

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fields = ['order', 'question_type', 'question_text', 'points']
    ordering = ['order']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = [
        'lesson', 'title', 'passing_score',
        'time_limit_minutes', 'is_active', 'order'
    ]
    list_filter = ['is_active', 'lesson__module__level']
    search_fields = ['title', 'lesson__title']
    ordering = ['lesson__module', 'lesson__lesson_number', 'order']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('lesson', 'title', 'description')
        }),
        ('Settings', {
            'fields': ('passing_score', 'time_limit_minutes', 'is_active', 'order')
        }),
    )
    
    inlines = [QuestionInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = [
        'quiz', 'order', 'question_type',
        'question_text_short', 'points'
    ]
    list_filter = ['question_type', 'quiz__lesson__module__level']
    search_fields = ['question_text', 'quiz__title']
    ordering = ['quiz__lesson', 'quiz__order', 'order']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('quiz', 'order', 'question_type')
        }),
        ('Question Content', {
            'fields': ('question_text', 'options', 'correct_answer', 'explanation')
        }),
        ('Scoring', {
            'fields': ('points',)
        }),
    )
    
    def question_text_short(self, obj):
        return obj.question_text[:50] + '...' if len(obj.question_text) > 50 else obj.question_text
    question_text_short.short_description = 'Question'


class QuestionResponseInline(admin.TabularInline):
    model = QuestionResponse
    extra = 0
    fields = ['question', 'is_correct', 'points_earned']
    readonly_fields = ['question', 'is_correct', 'points_earned', 'answered_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'quiz', 'score', 'passed',
        'started_at', 'completed_at', 'time_spent_display'
    ]
    list_filter = ['passed', 'quiz__lesson__module__level']
    search_fields = ['user__username', 'quiz__title']
    ordering = ['-started_at']
    readonly_fields = ['started_at', 'completed_at', 'time_spent_seconds']
    
    fieldsets = (
        ('Attempt Information', {
            'fields': ('user', 'quiz', 'started_at', 'completed_at')
        }),
        ('Results', {
            'fields': ('score', 'passed', 'time_spent_seconds')
        }),
        ('Answers', {
            'fields': ('answers',),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [QuestionResponseInline]
    
    def time_spent_display(self, obj):
        minutes = obj.time_spent_seconds // 60
        seconds = obj.time_spent_seconds % 60
        return f"{minutes}m {seconds}s"
    time_spent_display.short_description = 'Time Spent'


@admin.register(QuestionResponse)
class QuestionResponseAdmin(admin.ModelAdmin):
    list_display = [
        'attempt', 'question', 'is_correct',
        'points_earned', 'answered_at'
    ]
    list_filter = ['is_correct', 'question__question_type']
    search_fields = ['attempt__user__username', 'question__question_text']
    ordering = ['-answered_at']
    readonly_fields = ['answered_at']


# Homework Submission Admin

class HomeworkFeedbackInline(admin.StackedInline):
    model = HomeworkFeedback
    extra = 0
    can_delete = False
    fields = ['score', 'feedback_text', 'evaluator_type', 'evaluated_at']
    readonly_fields = ['evaluated_at']


@admin.register(HomeworkSubmission)
class HomeworkSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'lesson', 'attempt_number',
        'status', 'submitted_at', 'has_feedback'
    ]
    list_filter = ['status', 'lesson__module__level']
    search_fields = ['user__username', 'lesson__title', 'submission_text']
    ordering = ['-submitted_at']
    readonly_fields = ['submitted_at']
    
    fieldsets = (
        ('Submission Information', {
            'fields': ('user', 'lesson', 'attempt_number', 'status')
        }),
        ('Content', {
            'fields': ('submission_text', 'attachments')
        }),
        ('Meta', {
            'fields': ('submitted_at',)
        }),
    )
    
    inlines = [HomeworkFeedbackInline]
    
    def has_feedback(self, obj):
        return hasattr(obj, 'feedback')
    has_feedback.boolean = True
    has_feedback.short_description = 'Feedback'


@admin.register(HomeworkFeedback)
class HomeworkFeedbackAdmin(admin.ModelAdmin):
    list_display = [
        'submission', 'score', 'evaluator_type', 'evaluated_at'
    ]
    list_filter = ['evaluator_type', 'submission__lesson__module__level']
    search_fields = ['submission__user__username', 'submission__lesson__title']
    ordering = ['-evaluated_at']
    readonly_fields = ['evaluated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('submission', 'evaluator_type', 'evaluated_at')
        }),
        ('Scores', {
            'fields': ('score', 'criteria_scores')
        }),
        ('Feedback', {
            'fields': ('feedback_text', 'errors', 'strengths', 'improvements', 'next_step')
        }),
    )


# Vocabulary Admin

class LessonVocabularyInline(admin.TabularInline):
    model = LessonVocabulary
    extra = 1
    fields = ['word', 'is_primary', 'order']
    autocomplete_fields = ['word']


@admin.register(VocabularyWord)
class VocabularyWordAdmin(admin.ModelAdmin):
    list_display = [
        'word', 'translation_uk', 'word_type',
        'difficulty_level', 'frequency_rank'
    ]
    list_filter = ['word_type', 'difficulty_level']
    search_fields = ['word', 'translation_uk', 'definition_en']
    ordering = ['word']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('word', 'translation_uk', 'definition_en', 'example_sentence')
        }),
        ('Classification', {
            'fields': ('word_type', 'difficulty_level', 'frequency_rank')
        }),
        ('Media', {
            'fields': ('audio_url', 'image_url'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LessonVocabulary)
class LessonVocabularyAdmin(admin.ModelAdmin):
    list_display = ['lesson', 'word', 'is_primary', 'order']
    list_filter = ['is_primary', 'lesson__module__level']
    search_fields = ['lesson__title', 'word__word']
    autocomplete_fields = ['lesson', 'word']
    ordering = ['lesson', 'order']


@admin.register(UserVocabularyProgress)
class UserVocabularyProgressAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'word', 'status', 'accuracy',
        'times_seen', 'next_review_at', 'ease_factor'
    ]
    list_filter = ['status', 'word__difficulty_level']
    search_fields = ['user__username', 'word__word']
    readonly_fields = ['first_seen_at', 'updated_at', 'accuracy']
    ordering = ['next_review_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'word', 'status', 'learned_from_lesson')
        }),
        ('Statistics', {
            'fields': (
                'times_seen', 'times_correct', 'times_incorrect', 'accuracy'
            )
        }),
        ('Spaced Repetition', {
            'fields': (
                'ease_factor', 'interval_days', 'repetitions',
                'last_reviewed_at', 'next_review_at'
            )
        }),
        ('Timestamps', {
            'fields': ('first_seen_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def accuracy(self, obj):
        return f"{obj.accuracy:.1f}%"
    accuracy.short_description = 'Accuracy'
