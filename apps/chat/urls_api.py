"""
API URLs для DRF
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.chat import viewsets

router = DefaultRouter()
router.register(r'modules', viewsets.ModuleViewSet, basename='api-module')
router.register(r'lessons', viewsets.LessonViewSet, basename='api-lesson')
router.register(r'quizzes', viewsets.QuizViewSet, basename='api-quiz')
router.register(r'quiz-attempts', viewsets.QuizAttemptViewSet, basename='api-quiz-attempt')
router.register(r'homework', viewsets.HomeworkViewSet, basename='api-homework')
router.register(r'roleplay', viewsets.RolePlayViewSet, basename='api-roleplay')
router.register(r'vocabulary/words', viewsets.VocabularyViewSet, basename='api-vocabulary')
router.register(r'vocabulary/progress', viewsets.VocabularyProgressViewSet, basename='api-vocabulary-progress')
router.register(r'achievements', viewsets.AchievementViewSet, basename='api-achievement')
router.register(r'user-achievements', viewsets.UserAchievementViewSet, basename='api-user-achievement')

urlpatterns = [
    path('', include(router.urls)),
]
