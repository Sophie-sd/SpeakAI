"""
DRF ViewSets для REST API
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.chat.models import (
    Module, Lesson, UserLessonProgress, UserModuleProgress,
    Quiz, QuizAttempt, HomeworkSubmission, RolePlaySession,
    VocabularyWord, UserVocabularyProgress, Achievement, UserAchievement
)
from apps.chat.serializers import (
    ModuleSerializer, LessonSerializer, LessonDetailSerializer,
    UserLessonProgressSerializer, UserModuleProgressSerializer,
    QuizSerializer, QuizAttemptSerializer, HomeworkSubmissionSerializer,
    RolePlaySessionSerializer, RolePlaySessionDetailSerializer,
    VocabularyWordSerializer, UserVocabularyProgressSerializer,
    AchievementSerializer, UserAchievementSerializer
)


class ModuleViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для модулів (read-only)"""
    queryset = Module.objects.filter(is_active=True)
    serializer_class = ModuleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Module.objects.filter(is_active=True, level=self.request.user.level)


class LessonViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для уроків (read-only)"""
    queryset = Lesson.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LessonDetailSerializer
        return LessonSerializer


class UserProgressViewSet(viewsets.ModelViewSet):
    """ViewSet для прогресу користувача"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if 'lesson' in self.request.path:
            return UserLessonProgress.objects.filter(user=self.request.user)
        return UserModuleProgress.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if 'lesson' in self.request.path:
            return UserLessonProgressSerializer
        return UserModuleProgressSerializer


class QuizViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для квізів"""
    queryset = Quiz.objects.filter(is_active=True)
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]


class QuizAttemptViewSet(viewsets.ModelViewSet):
    """ViewSet для спроб квізів"""
    serializer_class = QuizAttemptSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return QuizAttempt.objects.filter(user=self.request.user)


class HomeworkViewSet(viewsets.ModelViewSet):
    """ViewSet для домашніх завдань"""
    serializer_class = HomeworkSubmissionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return HomeworkSubmission.objects.filter(user=self.request.user)


class RolePlayViewSet(viewsets.ModelViewSet):
    """ViewSet для рольових ігор"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return RolePlaySession.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RolePlaySessionDetailSerializer
        return RolePlaySessionSerializer


class VocabularyViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для словника"""
    queryset = VocabularyWord.objects.all()
    serializer_class = VocabularyWordSerializer
    permission_classes = [IsAuthenticated]


class VocabularyProgressViewSet(viewsets.ModelViewSet):
    """ViewSet для прогресу по словнику"""
    serializer_class = UserVocabularyProgressSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserVocabularyProgress.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def due_for_review(self, request):
        """Слова для повторення"""
        from apps.chat.services.vocabulary_tracker import VocabularyTracker
        words = VocabularyTracker.get_words_for_review(request.user)
        serializer = self.get_serializer(words, many=True)
        return Response(serializer.data)


class AchievementViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для досягнень"""
    queryset = Achievement.objects.all()
    serializer_class = AchievementSerializer
    permission_classes = [IsAuthenticated]


class UserAchievementViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для досягнень користувача"""
    serializer_class = UserAchievementSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserAchievement.objects.filter(user=self.request.user)
