"""
Custom throttles для AI endpoints
"""
from rest_framework.throttling import UserRateThrottle


class AIEvaluationThrottle(UserRateThrottle):
    """
    Throttle для AI evaluation endpoints (homework)
    Обмеження: 10 запитів на годину на користувача
    """
    scope = 'ai_evaluation'


class RolePlayThrottle(UserRateThrottle):
    """
    Throttle для role-play messages
    Обмеження: 50 повідомлень на годину
    """
    scope = 'roleplay'


class VoicePracticeThrottle(UserRateThrottle):
    """
    Throttle для voice practice
    Обмеження: 20 спроб на годину
    """
    scope = 'voice_practice'
