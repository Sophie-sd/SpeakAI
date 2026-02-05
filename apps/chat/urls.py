from django.urls import path
from . import views

urlpatterns = [
    # Existing URLs
    path('', views.chat_view, name='chat'),
    path('send/', views.send_message, name='send_message'),
    
    # Learning Program URLs
    path('program/', views.learning_program, name='learning_program'),
    path('level/select/', views.level_selector, name='level_selector'),
    path('level/change/<str:new_level>/', views.change_level, name='change_level'),
    path('module/<int:module_id>/', views.module_detail, name='module_detail'),
    path('lesson/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('lesson/<int:lesson_id>/roleplay/start/', views.start_role_play, name='start_role_play'),
    path('roleplay/<int:session_id>/continue/', views.continue_role_play, name='continue_role_play'),
    path('roleplay/<int:session_id>/evaluate/', views.evaluate_roleplay, name='evaluate_roleplay'),
    path('roleplay/<int:session_id>/', views.get_roleplay_session, name='get_roleplay_session'),
    path('lesson/<int:lesson_id>/roleplay-sessions/', views.get_lesson_roleplay_sessions, name='lesson_roleplay_sessions'),
    path('roleplay/<int:session_id>/delete/', views.delete_roleplay_session, name='delete_roleplay_session'),
    path('lesson/<int:lesson_id>/complete/', views.complete_lesson_component, name='complete_lesson_component'),
    
    # Homework & Voice Practice URLs
    path('lesson/<int:lesson_id>/check-homework/', views.check_homework, name='check_homework'),
    path('lesson/<int:lesson_id>/homework-history/', views.get_homework_history, name='homework_history'),
    path('homework-submission/<int:submission_id>/', views.get_homework_submission_detail, name='homework_submission_detail'),
    path('lesson/<int:lesson_id>/voice-practice/', views.voice_practice_session, name='voice_practice_session'),
    
    # Quiz URLs (Phase 1.1)
    path('lesson/<int:lesson_id>/quiz/', views.get_lesson_quiz, name='get_lesson_quiz'),
    path('quiz/<int:quiz_id>/start/', views.start_quiz, name='start_quiz'),
    path('quiz-attempt/<int:attempt_id>/answer/', views.submit_quiz_answer, name='submit_quiz_answer'),
    path('quiz-attempt/<int:attempt_id>/submit/', views.complete_quiz, name='complete_quiz'),
    path('quiz-attempt/<int:attempt_id>/results/', views.get_quiz_results, name='get_quiz_results'),
]
