from django.urls import path
from . import views

urlpatterns = [
    path('', views.voice_mode, name='voice_mode'),
    path('avatar/', views.avatar_mode, name='avatar_mode'),
    path('process/', views.process_audio, name='process_audio'),
    path('process-text/', views.process_voice_text, name='process_voice_text'),
    path('render-message/<int:message_id>/', views.render_message, name='render_message'),
]
