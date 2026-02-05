from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.urls import reverse
import json
import uuid
import logging
from .models import Avatar
from .services.speech import SpeechService
from apps.chat.services.gemini import GeminiService
from apps.chat.models import ChatSession, ChatMessage
from apps.chat.services.chat_helpers import (
    get_or_create_session,
    create_user_message,
    create_ai_message,
    get_chat_history,
)

logger = logging.getLogger(__name__)

@login_required
def voice_mode(request):
    """Voice-only mode with 3 bars visualizer and chat history"""
    avatar = Avatar.objects.filter(is_active=True).first()
    
    # Get or create voice session using helper
    session = get_or_create_session(request.user, title="Voice Session")
    messages = session.messages.order_by('created_at')
    
    return render(request, 'voice/voice-only.html', {
        'avatar': avatar,
        'session': session,
        'messages': messages,
        'send_message_url': reverse('send_message')
    })

@login_required
def avatar_mode(request):
    """Avatar mode with video + visualizer and chat history"""
    avatar = Avatar.objects.filter(is_active=True).first()
    
    # Get or create voice session using helper
    session = get_or_create_session(request.user, title="Voice Session")
    messages = session.messages.order_by('created_at')
    
    return render(request, 'voice/avatar.html', {
        'avatar': avatar,
        'session': session,
        'messages': messages,
        'send_message_url': reverse('send_message')
    })

@login_required
@require_POST
def process_audio(request):
    """Process audio: STT -> Gemini -> TTS and save to database"""
    try:
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return JsonResponse({'error': 'No audio file provided'}, status=400)
        
        # Get or create voice session using helper
        session = get_or_create_session(request.user, title="Voice Session")
        
        # Initialize services
        speech_service = SpeechService()
        gemini_service = GeminiService()
        
        # Step 1: Speech-to-Text
        transcript = speech_service.transcribe_audio(audio_file)
        if not transcript or 'Error' in transcript:
            return JsonResponse({
                'text': 'Sorry, I could not understand your speech. Please try again.',
                'audio_url': None,
                'history': []
            })
        
        # Save user message with transcript using helper
        user_msg = create_user_message(
            session, 
            transcript, 
            source_type='voice', 
            transcript=transcript
        )
        
        # Step 2: Get AI response with chat history
        history = get_chat_history(session, exclude_message_id=user_msg.id)
        response_text = gemini_service.get_chat_response(
            transcript,
            chat_history_objects=history,
            user_profile=request.user
        )
        
        # Step 3: Text-to-Speech (only English response)
        audio_bytes = speech_service.synthesize_speech(response_text.get('response'))
        
        # Step 4: Save audio file
        filename = f"response_{uuid.uuid4().hex[:8]}.mp3"
        audio_url = speech_service.save_audio_file(audio_bytes, filename)
        
        # Save AI message using helper
        ai_msg = create_ai_message(
            session,
            response_text,
            source_type='voice',
            audio_url=audio_url
        )
        
        # Build conversation history for frontend
        history = ChatMessage.objects.filter(session=session).order_by('created_at')
        history_data = [
            {
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'translation': msg.translation,
                'explanation': msg.explanation,
                'corrected_text': msg.corrected_text,
                'full_english_version': msg.full_english_version,
                'audio_url': msg.audio_url,
                'source_type': msg.source_type
            }
            for msg in history
        ]
        
        return JsonResponse({
            'text': response_text.get('response'),
            'translation': response_text.get('translation'),
            'explanation': response_text.get('explanation'),
            'corrected_text': response_text.get('corrected_text'),
            'full_english_version': response_text.get('full_english_version'),
            'audio_url': audio_url,
            'transcript': transcript,
            'session_id': session.id,
            'message_id': ai_msg.id,
            'phase': response_text.get('phase', 'initial'),
            'user_message': transcript,
            'history': history_data
        })
    
    except Exception as e:
        logger.error(f"Error in process_audio: {e}")
        return JsonResponse({
            'error': str(e),
            'text': 'An error occurred while processing your request.',
            'history': []
        }, status=500)

@login_required
@require_POST
def process_voice_text(request):
    """Process text input in voice mode: Gemini -> TTS and save to database"""
    try:
        text = request.POST.get('text')
        if not text:
            return JsonResponse({'error': 'No text provided'}, status=400)
        
        # Get or create voice session using helper
        session = get_or_create_session(request.user, title="Voice Session")
        
        # Initialize services
        speech_service = SpeechService()
        gemini_service = GeminiService()
        
        # Save user message using helper
        user_msg = create_user_message(
            session, 
            text, 
            source_type='voice'
        )
        
        # Step 1: Get AI response with chat history
        history = get_chat_history(session, exclude_message_id=user_msg.id)
        response_text = gemini_service.get_chat_response(
            text,
            chat_history_objects=history,
            user_profile=request.user
        )
        
        # Step 2: Text-to-Speech (only English response)
        audio_bytes = speech_service.synthesize_speech(response_text.get('response'))
        
        # Step 3: Save audio file
        filename = f"response_{uuid.uuid4().hex[:8]}.mp3"
        audio_url = speech_service.save_audio_file(audio_bytes, filename)
        
        # Save AI message using helper
        ai_msg = create_ai_message(
            session,
            response_text,
            source_type='voice',
            audio_url=audio_url
        )
        
        return JsonResponse({
            'text': ai_msg.content,
            'translation': ai_msg.translation,
            'explanation': ai_msg.explanation,
            'corrected_text': ai_msg.corrected_text,
            'full_english_version': ai_msg.full_english_version,
            'audio_url': audio_url,
            'message_id': ai_msg.id,
            'session_id': session.id,
            'phase': response_text.get('phase', 'initial'),
            'user_message': text
        })
    
    except Exception as e:
        logger.error(f"Error in process_voice_text: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def render_message(request, message_id):
    """Render single message HTML for AJAX requests (used by voice JS)"""
    try:
        message = get_object_or_404(ChatMessage, id=message_id)
        
        # Security check - ensure message belongs to current user
        if message.session.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        # Get previous user message for context
        user_messages = message.session.messages.filter(role='user').order_by('-created_at')
        user_message = user_messages.first() if user_messages else None
        
        return render(request, 'chat/partials/single_message.html', {
            'message': message,
            'user_message': user_message,
            'send_message_url': reverse('send_message')
        })
    except Exception as e:
        logger.error(f"Error rendering message: {e}")
        return JsonResponse({'error': str(e)}, status=500)
