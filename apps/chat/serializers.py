"""
DRF Serializers для всіх моделей
"""
from rest_framework import serializers
from apps.chat.models import (
    Module, Lesson, UserLessonProgress, UserModuleProgress,
    Quiz, Question, QuizAttempt, QuestionResponse,
    HomeworkSubmission, HomeworkFeedback,
    RolePlaySession, VocabularyWord, UserVocabularyProgress,
    Achievement, UserAchievement, LearningStreak
)


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'title', 'description', 'level', 'module_number', 
                  'total_lessons', 'estimated_duration_weeks', 'is_active']


class LessonSerializer(serializers.ModelSerializer):
    module_title = serializers.CharField(source='module.title', read_only=True)
    
    class Meta:
        model = Lesson
        fields = ['id', 'module', 'module_title', 'lesson_number', 'title',
                  'description', 'grammar_focus', 'vocabulary_list', 'is_active']


class LessonDetailSerializer(serializers.ModelSerializer):
    module = ModuleSerializer(read_only=True)
    
    class Meta:
        model = Lesson
        fields = '__all__'


class UserLessonProgressSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    
    class Meta:
        model = UserLessonProgress
        fields = ['id', 'lesson', 'lesson_title', 'status', 'overall_score',
                  'theory_completed', 'voice_practice_completed', 'voice_practice_score',
                  'role_play_completed', 'role_play_score', 'homework_completed',
                  'homework_score', 'started_at', 'completed_at']
        read_only_fields = ['started_at', 'completed_at']


class UserModuleProgressSerializer(serializers.ModelSerializer):
    module_title = serializers.CharField(source='module.title', read_only=True)
    
    class Meta:
        model = UserModuleProgress
        fields = ['id', 'module', 'module_title', 'status', 'lessons_completed',
                  'lessons_total', 'progress_percentage', 'average_score']
        read_only_fields = ['progress_percentage', 'average_score']


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'question_type', 'question_text', 'options', 'points', 'order']


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Quiz
        fields = ['id', 'lesson', 'title', 'description', 'passing_score',
                  'time_limit_minutes', 'is_active', 'questions']


class QuestionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionResponse
        fields = ['id', 'question', 'user_answer', 'is_correct', 'points_earned']


class QuizAttemptSerializer(serializers.ModelSerializer):
    responses = QuestionResponseSerializer(many=True, read_only=True)
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    
    class Meta:
        model = QuizAttempt
        fields = ['id', 'quiz', 'quiz_title', 'score', 'passed', 'started_at',
                  'completed_at', 'time_spent_seconds', 'responses']
        read_only_fields = ['started_at', 'completed_at']


class HomeworkFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeworkFeedback
        fields = ['id', 'score', 'criteria_scores', 'feedback_text', 'errors',
                  'strengths', 'improvements', 'next_step', 'evaluated_at', 'evaluator_type']
        read_only_fields = ['evaluated_at']


class HomeworkSubmissionSerializer(serializers.ModelSerializer):
    feedback = HomeworkFeedbackSerializer(read_only=True)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    
    class Meta:
        model = HomeworkSubmission
        fields = ['id', 'lesson', 'lesson_title', 'submission_text', 'attachments',
                  'submitted_at', 'attempt_number', 'status', 'feedback']
        read_only_fields = ['submitted_at', 'attempt_number']


class RolePlaySessionSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    
    class Meta:
        model = RolePlaySession
        fields = ['id', 'lesson', 'lesson_title', 'scenario_name', 'status',
                  'overall_score', 'messages_count', 'started_at', 'completed_at']
        read_only_fields = ['started_at', 'completed_at', 'messages_count']


class RolePlaySessionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePlaySession
        fields = '__all__'


class VocabularyWordSerializer(serializers.ModelSerializer):
    class Meta:
        model = VocabularyWord
        fields = ['id', 'word', 'translation_uk', 'definition_en', 'example_sentence',
                  'word_type', 'difficulty_level', 'audio_url', 'image_url']


class UserVocabularyProgressSerializer(serializers.ModelSerializer):
    word_details = VocabularyWordSerializer(source='word', read_only=True)
    accuracy = serializers.FloatField(read_only=True)
    is_due_for_review = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = UserVocabularyProgress
        fields = ['id', 'word', 'word_details', 'status', 'times_seen', 'times_correct',
                  'times_incorrect', 'accuracy', 'last_reviewed_at', 'next_review_at',
                  'is_due_for_review']
        read_only_fields = ['times_seen', 'times_correct', 'times_incorrect', 'last_reviewed_at']


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = ['id', 'code', 'title_uk', 'description_uk', 'icon', 'points',
                  'category', 'tier']


class UserAchievementSerializer(serializers.ModelSerializer):
    achievement_details = AchievementSerializer(source='achievement', read_only=True)
    
    class Meta:
        model = UserAchievement
        fields = ['id', 'achievement', 'achievement_details', 'unlocked_at', 'progress']
        read_only_fields = ['unlocked_at']


class LearningStreakSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningStreak
        fields = ['id', 'current_streak', 'longest_streak', 'last_activity_date', 'total_active_days']
        read_only_fields = ['last_activity_date']
