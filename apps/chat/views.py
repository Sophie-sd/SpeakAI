from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
import json
import logging
from .models import ChatSession, ChatMessage, Module, Lesson, UserLessonProgress, UserModuleProgress, RolePlaySession
from .services.gemini import GeminiService
from .services.chat_helpers import (
    get_or_create_session,
    create_user_message,
    create_ai_message,
    get_chat_history,
)
from apps.users.decorators import paid_user_required, onboarding_required
from .services.roleplay_engine import RolePlayEngine

logger = logging.getLogger(__name__)

@login_required
@paid_user_required
@require_POST
@csrf_protect
def check_homework(request, lesson_id):
    """
    AI перевірка домашнього завдання за критеріями з homework_instructions
    """
    from .models import HomeworkSubmission, HomeworkFeedback
    
    lesson = get_object_or_404(Lesson, id=lesson_id, is_active=True)
    user = request.user
    
    # Отримати текст ДЗ
    try:
        data = json.loads(request.body)
        homework_text = data.get('homework', '')
    except:
        homework_text = request.POST.get('homework', '')
    
    if not homework_text:
        return JsonResponse({'error': 'No homework submitted'}, status=400)
    
    if not lesson.homework_instructions:
        return JsonResponse({'error': 'No evaluation criteria for this lesson'}, status=400)
    
    # Підрахувати номер спроби
    previous_submissions = HomeworkSubmission.objects.filter(
        user=user,
        lesson=lesson
    ).count()
    attempt_number = previous_submissions + 1
    
    # Створити submission
    submission = HomeworkSubmission.objects.create(
        user=user,
        lesson=lesson,
        submission_text=homework_text,
        attempt_number=attempt_number,
        status='pending'
    )
    
    # Оцінити ДЗ через Gemini
    service = GeminiService()
    evaluation = service.evaluate_homework(homework_text, lesson, user)
    
    # Створити feedback
    feedback = HomeworkFeedback.objects.create(
        submission=submission,
        score=float(evaluation.get('score', 0)),
        criteria_scores=evaluation.get('criteria_scores', {}),
        feedback_text=evaluation.get('feedback', ''),
        errors=evaluation.get('errors', []),
        strengths=evaluation.get('strengths', []),
        improvements=evaluation.get('improvements', []),
        next_step=evaluation.get('next_step', ''),
        evaluator_type='ai'
    )
    
    # Оновити статус submission
    submission.status = 'evaluated'
    submission.save()
    
    # Отримати або створити прогрес
    progress, created = UserLessonProgress.objects.get_or_create(
        user=user,
        lesson=lesson
    )
    
    # Зберегти кращу оцінку
    if feedback.score > (progress.homework_score or 0):
        progress.homework_score = feedback.score
        progress.homework_completed = True
        progress.ai_feedback = evaluation  # Зберегти весь feedback
        progress.save()
        
        # Обновити загальну оцінку
        progress.calculate_overall_score()
    
    return JsonResponse({
        'success': True,
        'submission_id': submission.id,
        'attempt_number': attempt_number,
        'score': feedback.score,
        'feedback': feedback.feedback_text,
        'errors': feedback.errors,
        'strengths': feedback.strengths,
        'improvements': feedback.improvements,
        'next_step': feedback.next_step
    })


@login_required
@paid_user_required
def get_homework_history(request, lesson_id):
    """Отримати історію подань домашніх завдань для уроку"""
    from .models import HomeworkSubmission
    
    lesson = get_object_or_404(Lesson, id=lesson_id)
    submissions = HomeworkSubmission.objects.filter(
        user=request.user,
        lesson=lesson
    ).select_related('feedback').order_by('-submitted_at')
    
    history = []
    for submission in submissions:
        item = {
            'id': submission.id,
            'attempt_number': submission.attempt_number,
            'submitted_at': submission.submitted_at.isoformat(),
            'status': submission.status,
            'submission_text': submission.submission_text[:100] + '...' if len(submission.submission_text) > 100 else submission.submission_text
        }
        
        if hasattr(submission, 'feedback'):
            item['feedback'] = {
                'score': submission.feedback.score,
                'feedback_text': submission.feedback.feedback_text
            }
        
        history.append(item)
    
    return JsonResponse({'submissions': history})


@login_required
@paid_user_required
def get_homework_submission_detail(request, submission_id):
    """Отримати деталі конкретного submission"""
    from .models import HomeworkSubmission
    
    submission = get_object_or_404(
        HomeworkSubmission,
        id=submission_id,
        user=request.user
    )
    
    result = {
        'id': submission.id,
        'lesson_id': submission.lesson.id,
        'lesson_title': submission.lesson.title,
        'attempt_number': submission.attempt_number,
        'submission_text': submission.submission_text,
        'attachments': submission.attachments,
        'submitted_at': submission.submitted_at.isoformat(),
        'status': submission.status
    }
    
    if hasattr(submission, 'feedback'):
        result['feedback'] = {
            'score': submission.feedback.score,
            'criteria_scores': submission.feedback.criteria_scores,
            'feedback_text': submission.feedback.feedback_text,
            'errors': submission.feedback.errors,
            'strengths': submission.feedback.strengths,
            'improvements': submission.feedback.improvements,
            'next_step': submission.feedback.next_step,
            'evaluated_at': submission.feedback.evaluated_at.isoformat(),
            'evaluator_type': submission.feedback.evaluator_type
        }
    
    return JsonResponse(result)


@login_required
@paid_user_required
@require_POST
@csrf_protect
def voice_practice_session(request, lesson_id):
    """
    Сесія голосової практики з voice_practice_prompts
    """
    lesson = get_object_or_404(Lesson, id=lesson_id, is_active=True)
    user = request.user
    
    if not lesson.voice_practice_prompts:
        return JsonResponse({'error': 'No voice prompts for this lesson'}, status=400)
    
    try:
        data = json.loads(request.body)
        user_responses = data.get('responses', [])  # List of responses
    except:
        user_responses = request.POST.getlist('responses[]', [])
    
    if not user_responses:
        return JsonResponse({'error': 'No responses provided'}, status=400)
    
    # Отримати або створити прогрес
    progress, created = UserLessonProgress.objects.get_or_create(
        user=user,
        lesson=lesson
    )
    
    # Оцінити голосову практику
    service = GeminiService()
    evaluation = service.evaluate_voice_practice(user_responses, lesson, user)
    
    # Зберегти оцінку
    if evaluation.get('overall_score'):
        progress.voice_practice_score = float(evaluation['overall_score'])
        progress.voice_practice_completed = True
        progress.ai_feedback = evaluation
        progress.save()
        
        # Обновити загальну оцінку
        progress.calculate_overall_score()
    
    return JsonResponse({
        'success': True,
        'overall_score': evaluation.get('overall_score'),
        'items': evaluation.get('items', []),
        'feedback': evaluation.get('overall_feedback', ''),
        'strengths': evaluation.get('strengths', []),
        'improvements': evaluation.get('improvements', [])
    })


@login_required
def chat_view(request):
    # Get or create session
    session_id = request.GET.get('session_id')
    if session_id:
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    else:
        session = get_or_create_session(request.user)
    
    messages = session.messages.order_by('created_at')
    
    return render(request, 'chat/index.html', {
        'session': session,
        'messages': messages,
        'send_message_url': reverse('send_message')
    })

@login_required
@require_POST
def send_message(request):
    session_id = request.POST.get('session_id')
    content = request.POST.get('content')
    
    if not content:
        return HttpResponse("")
        
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    
    # Save user message using helper
    user_msg = create_user_message(session, content, source_type='text')
    
    # Get AI response
    service = GeminiService()
    previous_history = get_chat_history(session, exclude_message_id=user_msg.id)
    
    # Check if this session is linked to a lesson (for voice practice or role-play context)
    if session.lesson:
        # Use lesson-restricted response for topic boundary enforcement
        response_text = service.get_lesson_voice_response(
            user_message=content,
            lesson=session.lesson,
            chat_history_objects=previous_history,
            user_profile=request.user
        )
    else:
        # Use general chat response for free conversation
        response_text = service.get_chat_response(
            content, 
            chat_history_objects=previous_history, 
            user_profile=request.user
        )
    
    # Save AI message using helper
    ai_msg = create_ai_message(session, response_text, source_type='text')
    
    context = {
        'user_message': user_msg,
        'ai_message': ai_msg,
        'send_message_url': reverse('send_message')
    }
    return render(request, 'chat/partials/new_messages.html', context)


# Learning Program Views

@login_required
@paid_user_required
@onboarding_required
def learning_program(request):
    """Головна сторінка навчальної програми"""
    user = request.user
    
    # Отримати всі модулі для рівня користувача
    user_level = user.level
    modules = Module.objects.filter(level=user_level, is_active=True)
    
    # Якщо немає модулів для рівня користувача, показати fallback з доступними рівнями
    if not modules.exists():
        available_levels = Module.objects.filter(is_active=True).values_list('level', flat=True).distinct().order_by('level')
        return render(request, 'learning/program_empty.html', {
            'user_level': user_level,
            'available_levels': list(available_levels),
            'all_levels': ['A0', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2'],
            'message': f'Немає модулів для вашого рівня ({user_level}). Оберіть інший рівень:'
        })
    
    # Отримати або створити прогрес по модулях
    module_progress_list = []
    for module in modules:
        progress, created = UserModuleProgress.objects.get_or_create(
            user=user,
            module=module,
            defaults={'lessons_total': module.total_lessons}
        )
        if created or progress.status == 'locked':
            # Розблокувати перший модуль
            if module.module_number == 1:
                progress.status = 'available'
                progress.save()
        
        module_progress_list.append({
            'module': module,
            'progress': progress
        })
    
    return render(request, 'learning/program.html', {
        'module_progress_list': module_progress_list,
        'user_level': user_level,
        'all_levels': ['A0', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2']
    })


@login_required
@paid_user_required
def change_level(request, new_level):
    """Змінити рівень користувача"""
    level_choices = dict(request.user.LEVEL_CHOICES)
    
    if new_level.upper() not in level_choices:
        return redirect('learning_program')
    
    request.user.level = new_level.upper()
    request.user.save()
    
    return redirect('learning_program')


@login_required
@paid_user_required
def level_selector(request):
    """Сторінка вибору рівня"""
    levels = [
        {'code': 'A0', 'name': 'Starter', 'desc': 'Complete beginner'},
        {'code': 'A1', 'name': 'Beginner', 'desc': 'I know a few words'},
        {'code': 'A2', 'name': 'Elementary', 'desc': 'I can hold basic conversations'},
        {'code': 'B1', 'name': 'Intermediate', 'desc': 'I can discuss various topics'},
        {'code': 'B2', 'name': 'Upper Intermediate', 'desc': 'I\'m quite fluent'},
        {'code': 'C1', 'name': 'Advanced', 'desc': 'I speak fluently'},
        {'code': 'C2', 'name': 'Proficient', 'desc': 'Nearly native speaker'},
    ]
    
    return render(request, 'learning/level_selector.html', {
        'levels': levels,
        'current_level': request.user.level
    })


@login_required
@paid_user_required
def module_detail(request, module_id):
    """Детальна сторінка модуля з уроками"""
    module = get_object_or_404(Module, id=module_id, is_active=True)
    user = request.user
    
    # Перевірити чи має доступ користувач
    module_progress = UserModuleProgress.objects.get_or_create(
        user=user,
        module=module,
        defaults={'lessons_total': module.total_lessons}
    )[0]
    
    if module_progress.status == 'locked':
        return redirect('learning_program')
    
    # Отримати уроки модуля з прогресом
    lessons = module.lessons.filter(is_active=True).order_by('lesson_number')
    lesson_progress_list = []
    
    for lesson in lessons:
        progress, created = UserLessonProgress.objects.get_or_create(
            user=user,
            lesson=lesson
        )
        lesson_progress_list.append({
            'lesson': lesson,
            'progress': progress
        })
    
    return render(request, 'learning/module_detail.html', {
        'module': module,
        'module_progress': module_progress,
        'lesson_progress_list': lesson_progress_list
    })


@login_required
@paid_user_required
def lesson_detail(request, lesson_id):
    """Детальна сторінка уроку"""
    lesson = get_object_or_404(Lesson, id=lesson_id, is_active=True)
    user = request.user
    
    # Отримати або створити прогрес
    progress, created = UserLessonProgress.objects.get_or_create(
        user=user,
        lesson=lesson
    )
    
    if created or progress.status == 'not_started':
        progress.status = 'in_progress'
        progress.started_at = timezone.now()
        progress.save()
    
    # Перевірити чи є наступний урок
    next_lesson = lesson.get_next_lesson()
    previous_lesson = lesson.get_previous_lesson()
    
    return render(request, 'learning/lesson_detail.html', {
        'lesson': lesson,
        'progress': progress,
        'next_lesson': next_lesson,
        'previous_lesson': previous_lesson
    })


@login_required
@paid_user_required
@require_POST
def start_role_play(request, lesson_id):
    """Почати рольову гру для уроку"""
    from apps.voice.services.speech import SpeechService
    from apps.chat.services.chat_helpers import create_ai_message
    
    lesson = get_object_or_404(Lesson, id=lesson_id)
    user = request.user
    
    if not lesson.role_play_scenario:
        return JsonResponse({'error': 'No role-play scenario for this lesson'}, status=400)
    
    # Перевірити чи є активна сесія
    existing_session = RolePlaySession.objects.filter(
        user=user,
        lesson=lesson,
        status='active'
    ).first()
    
    if existing_session:
        # Продовжити існуючу сесію
        return JsonResponse({
            'session_id': existing_session.id,
            'messages': existing_session.messages_history,
            'continued': True
        })
    
    # Ініціалізувати Role-Play Engine
    engine = RolePlayEngine()
    
    # Додати lesson context
    lesson_context = {
        'grammar_focus': lesson.grammar_focus,
        'vocabulary': lesson.vocabulary_list[:30] if lesson.vocabulary_list else [],
        'theory': lesson.theory_content[:500] if lesson.theory_content else ''
    }
    
    result = engine.start_scenario(
        scenario=lesson.role_play_scenario,
        user_level=user.level,
        user_profile=user,
        lesson_context=lesson_context
    )
    
    # Побудувати system_prompt з lesson context
    system_prompt = engine._build_scenario_prompt(
        lesson.role_play_scenario,
        user.level,
        user,
        lesson_context=lesson_context
    )
    
    # Створити initial messages_history
    initial_history = [
        {'role': 'model', 'content': result['ai_message']}
    ]
    
    # Створити сесію (Phase 1.3 - зберігаємо system_prompt та messages_history)
    session = RolePlaySession.objects.create(
        user=user,
        lesson=lesson,
        scenario_name=lesson.role_play_scenario_name,
        system_prompt=system_prompt,
        messages_history=initial_history,
        dialogue=[{
            'role': 'ai',
            'content': result['ai_message'],
            'timestamp': timezone.now().isoformat()
        }],
        messages_count=1
    )
    
    # CREATE ChatSession for rendering (for consistent message display)
    chat_session = ChatSession.objects.create(
        user=user,
        lesson=lesson,
        session_type='roleplay_voice',
        title=f"Role-Play: {lesson.role_play_scenario_name}",
        is_active=True
    )
    
    # Generate TTS audio for initial message
    speech_service = SpeechService()
    try:
        audio_bytes = speech_service.synthesize_speech(result['ai_message'])
        filename = f"rp_{session.id}_init.mp3"
        audio_url = speech_service.save_audio_file(audio_bytes, filename)
    except Exception:
        audio_url = None
    
    # Save initial AI message to ChatMessage for rendering
    ai_response_dict = {
        'response': result.get('ai_message', ''),
        'translation': result.get('translation'),  # Now from RolePlayEngine
        'explanation': result.get('explanation'),  # Now from RolePlayEngine
        'corrected_text': result.get('corrected_text'),  # Now from RolePlayEngine
        'full_english_version': None,
        'phase': 'initial',
        'has_errors': False
    }
    
    ai_msg = create_ai_message(
        chat_session,
        ai_response_dict,
        source_type='voice',
        audio_url=audio_url
    )
    
    return JsonResponse({
        'session_id': session.id,
        'ai_message': result['ai_message'],
        'initial_message': {
            'id': ai_msg.id,
            'role': 'model',
            'content': result['ai_message']
        },
        'scenario_name': lesson.role_play_scenario_name,
        'continued': False,
        'audio_url': audio_url,
        'chat_session_id': chat_session.id  # For linking future messages
    })


@login_required
@paid_user_required
@require_POST
def continue_role_play(request, session_id):
    """Продовжити рольову гру (Phase 1.3 - з відновленням контексту)"""
    from apps.chat.services.roleplay_engine import RolePlayEngine
    from apps.chat.services.chat_helpers import create_user_message, create_ai_message
    
    session = get_object_or_404(RolePlaySession, id=session_id, user=request.user)
    
    user_message = request.POST.get('message')
    if not user_message:
        return JsonResponse({'error': 'No message provided'}, status=400)
    
    # Ініціалізувати engine
    engine = RolePlayEngine()
    
    # Додати user message до history
    session.messages_history.append({
        'role': 'user',
        'content': user_message
    })
    
    # Відновити chat session з збереженої history
    chat = engine.restore_session(
        system_prompt=session.system_prompt,
        messages_history=session.messages_history
    )
    
    if not chat:
        return JsonResponse({
            'error': 'Failed to restore conversation context'
        }, status=500)
    
    # Відправити повідомлення користувача
    try:
        result = engine.continue_dialogue(chat, user_message)
        
        if not result.get('success'):
            return JsonResponse({
                'error': result.get('error', 'Failed to get AI response')
            }, status=500)
        
        ai_message = result['ai_message']
        
        # Додати AI відповідь до history
        session.messages_history.append({
            'role': 'model',
            'content': ai_message
        })
        
        # Також оновити dialogue для відображення
        session.dialogue.append({
            'role': 'user',
            'content': user_message,
            'timestamp': timezone.now().isoformat()
        })
        session.dialogue.append({
            'role': 'ai',
            'content': ai_message,
            'timestamp': timezone.now().isoformat()
        })
        
        session.user_messages_count += 1
        session.messages_count += 2
        session.save()
        
        # GET or CREATE ChatSession for rendering
        chat_session, _ = ChatSession.objects.get_or_create(
            user=session.user,
            lesson=session.lesson,
            session_type='roleplay_voice',
            is_active=True,
            defaults={'title': f"Role-Play: {session.scenario_name}"}
        )
        
        # Save user message to ChatMessage
        user_msg = create_user_message(
            chat_session,
            user_message,
            source_type='text'
        )
        
        # Build AI response dict for helper
        ai_response_dict = {
            'response': result.get('ai_message', ''),
            'translation': result.get('translation'),  # From RolePlayEngine
            'explanation': result.get('explanation'),  # From RolePlayEngine
            'corrected_text': result.get('corrected_text'),  # From RolePlayEngine
            'full_english_version': None,
            'phase': 'initial',
            'has_errors': False
        }
        
        # Save AI message to ChatMessage
        ai_msg = create_ai_message(
            chat_session,
            ai_response_dict,
            source_type='text'
        )
        
        return JsonResponse({
            'ai_message': ai_message,
            'success': True,
            'message_id': ai_msg.id  # For rendering via server partial
        })
        
    except Exception as e:
        logger.error(f"Error in continue_role_play: {e}", exc_info=True)
        return JsonResponse({
            'error': 'Failed to continue conversation'
        }, status=500)


@login_required
@paid_user_required
@require_POST
@csrf_protect
def evaluate_roleplay(request, session_id):
    """Оцінити та завершити рольовий діалог (Phase 1.4)"""
    from apps.chat.services.roleplay_engine import RolePlayEngine
    
    session = get_object_or_404(RolePlaySession, id=session_id, user=request.user)
    
    if session.status == 'completed':
        return JsonResponse({'error': 'Session already evaluated'}, status=400)
    
    engine = RolePlayEngine()
    
    # Конвертувати messages_history в формат для evaluation
    dialogue = []
    for msg in session.messages_history:
        role = 'user' if msg['role'] == 'user' else 'ai'
        dialogue.append({'role': role, 'content': msg['content']})
    
    evaluation = engine.evaluate_performance(
        dialogue=dialogue,
        scenario_objectives=session.lesson.role_play_scenario.get('objectives', []),
        user_level=request.user.level
    )
    
    # Зберегти результати
    session.ai_evaluation = evaluation
    session.overall_score = evaluation.get('overall_score', 0)
    session.status = 'completed'
    session.completed_at = timezone.now()
    
    # Розрахувати тривалість
    duration = (session.completed_at - session.started_at).total_seconds() / 60
    session.duration_minutes = int(duration)
    session.save()
    
    # Оновити progress
    progress, _ = UserLessonProgress.objects.get_or_create(
        user=request.user,
        lesson=session.lesson
    )
    progress.role_play_completed = True
    progress.role_play_score = session.overall_score
    progress.save()
    progress.calculate_overall_score()
    
    return JsonResponse({
        'success': True,
        'evaluation': evaluation
    })


@login_required
@paid_user_required
def get_roleplay_session(request, session_id):
    """Отримати деталі рольової сесії"""
    session = get_object_or_404(RolePlaySession, id=session_id, user=request.user)
    
    return JsonResponse({
        'session_id': session.id,
        'scenario_name': session.scenario_name,
        'status': session.status,
        'messages_count': session.messages_count,
        'started_at': session.started_at.isoformat(),
        'completed_at': session.completed_at.isoformat() if session.completed_at else None,
        'overall_score': session.overall_score,
        'dialogue': session.dialogue,
        'evaluation': session.ai_evaluation if session.status == 'completed' else None
    })


@login_required
@paid_user_required
def get_lesson_roleplay_sessions(request, lesson_id):
    """Отримати список сесій рольової гри для уроку"""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    sessions = RolePlaySession.objects.filter(
        user=request.user,
        lesson=lesson
    ).order_by('-started_at')
    
    sessions_list = []
    for session in sessions:
        sessions_list.append({
            'id': session.id,
            'scenario_name': session.scenario_name,
            'status': session.status,
            'messages_count': session.messages_count,
            'started_at': session.started_at.isoformat(),
            'overall_score': session.overall_score
        })
    
    return JsonResponse({'sessions': sessions_list})


@login_required
@paid_user_required
@require_POST
def delete_roleplay_session(request, session_id):
    """Видалити незавершену рольову сесію"""
    session = get_object_or_404(RolePlaySession, id=session_id, user=request.user)
    
    if session.status == 'completed':
        return JsonResponse({'error': 'Cannot delete completed session'}, status=400)
    
    session.status = 'abandoned'
    session.save()
    
    return JsonResponse({'success': True})


@login_required
@paid_user_required
@require_POST
def complete_lesson_component(request, lesson_id):
    """Позначити компонент уроку як виконаний"""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    progress = get_object_or_404(UserLessonProgress, user=request.user, lesson=lesson)
    
    component = request.POST.get('component')
    
    if component == 'theory':
        progress.theory_completed = True
    elif component == 'voice_practice':
        progress.voice_practice_completed = True
        # Зберегти оцінку якщо є
        score = request.POST.get('score')
        if score:
            progress.voice_practice_score = float(score)
    elif component == 'role_play':
        progress.role_play_completed = True
        score = request.POST.get('score')
        if score:
            progress.role_play_score = float(score)
    elif component == 'homework':
        progress.homework_completed = True
        score = request.POST.get('score')
        if score:
            progress.homework_score = float(score)
    
    # Перевірити чи всі компоненти виконані
    if all([
        progress.theory_completed,
        progress.voice_practice_completed,
        progress.role_play_completed,
        progress.homework_completed
    ]):
        progress.status = 'completed'
        progress.completed_at = timezone.now()
        progress.calculate_overall_score()
    
    progress.save()
    
    # Оновити прогрес модуля
    module_progress = UserModuleProgress.objects.get(
        user=request.user,
        module=lesson.module
    )
    module_progress.update_progress()
    
    return JsonResponse({
        'success': True,
        'lesson_completed': progress.status == 'completed',
        'overall_score': progress.overall_score
    })


# ============================================
# Quiz Views (Phase 1.1)
# ============================================

@login_required
@paid_user_required
def get_lesson_quiz(request, lesson_id):
    """Отримати квіз для уроку"""
    lesson = get_object_or_404(Lesson, id=lesson_id, is_active=True)
    quiz = lesson.quizzes.filter(is_active=True).first()
    
    if not quiz:
        return JsonResponse({'error': 'No quiz available for this lesson'}, status=404)
    
    questions = []
    for question in quiz.questions.all().order_by('order'):
        questions.append({
            'id': question.id,
            'order': question.order,
            'question_type': question.question_type,
            'question_text': question.question_text,
            'options': question.options,
            'points': question.points
        })
    
    return JsonResponse({
        'quiz': {
            'id': quiz.id,
            'title': quiz.title,
            'description': quiz.description,
            'passing_score': quiz.passing_score,
            'time_limit_minutes': quiz.time_limit_minutes,
            'total_points': quiz.total_points,
            'questions': questions
        }
    })


@login_required
@paid_user_required
@require_POST
@csrf_protect
def start_quiz(request, quiz_id):
    """Почати новий квіз"""
    from .services.quiz_engine import QuizEngine
    from .models import Quiz
    
    quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)
    
    try:
        attempt = QuizEngine.start_quiz(quiz, request.user)
        
        return JsonResponse({
            'success': True,
            'attempt_id': attempt.id,
            'started_at': attempt.started_at.isoformat(),
            'time_limit_minutes': quiz.time_limit_minutes
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@paid_user_required
@require_POST
@csrf_protect
def submit_quiz_answer(request, attempt_id):
    """Відповісти на питання квізу"""
    from .services.quiz_engine import QuizEngine
    from .models import QuizAttempt, Question
    
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    
    # Перевірити ліміт часу
    if not QuizEngine.check_time_limit(attempt):
        return JsonResponse({
            'error': 'Time limit exceeded',
            'time_up': True
        }, status=400)
    
    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        user_answer = data.get('answer')
        
        if not question_id or user_answer is None:
            return JsonResponse({'error': 'Missing question_id or answer'}, status=400)
        
        question = get_object_or_404(Question, id=question_id, quiz=attempt.quiz)
        response = QuizEngine.submit_answer(attempt, question, user_answer)
        
        return JsonResponse({
            'success': True,
            'question_id': question.id,
            'is_correct': response.is_correct,
            'points_earned': response.points_earned
        })
        
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@paid_user_required
@require_POST
@csrf_protect
def complete_quiz(request, attempt_id):
    """Завершити квіз та отримати результати"""
    from .services.quiz_engine import QuizEngine
    from .models import QuizAttempt
    
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    
    try:
        result = QuizEngine.complete_quiz(attempt)
        
        return JsonResponse({
            'success': True,
            **result
        })
        
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@paid_user_required
def get_quiz_results(request, attempt_id):
    """Отримати детальні результати квізу"""
    from .services.quiz_engine import QuizEngine
    from .models import QuizAttempt
    
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    
    if not attempt.completed_at:
        return JsonResponse({'error': 'Quiz not completed yet'}, status=400)
    
    try:
        results = QuizEngine.get_quiz_results(attempt)
        return JsonResponse(results)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============= LESSON VOICE PRACTICE VIEWS (Phase 2.9) =============

@login_required
@paid_user_required
@require_POST
@csrf_protect
def start_lesson_voice_practice(request, lesson_id):
    """
    Start or resume Voice Practice session for a lesson.
    Creates/resumes ChatSession and returns initial AI message with audio.
    """
    from apps.voice.services.speech import SpeechService
    import logging
    logger = logging.getLogger(__name__)
    
    lesson = get_object_or_404(Lesson, id=lesson_id, is_active=True)
    user = request.user
    
    # Check for existing active session
    existing_session = ChatSession.objects.filter(
        user=user,
        lesson=lesson,
        session_type='lesson_voice_practice',
        is_active=True
    ).first()
    
    if existing_session:
        # Resume existing session
        messages = existing_session.messages.all().order_by('created_at')
        messages_list = []
        for msg in messages:
            messages_list.append({
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'translation': msg.translation,
                'audio_url': msg.audio_url if hasattr(msg, 'audio_url') else None
            })
        
        return JsonResponse({
            'session_id': existing_session.id,
            'messages': messages_list,
            'continued': True
        })
    
    # Create new session
    session = ChatSession.objects.create(
        user=user,
        lesson=lesson,
        title=f"Voice Practice: {lesson.title}",
        session_type='lesson_voice_practice',
        is_active=True
    )
    
    # Generate initial AI greeting
    gemini = GeminiService()
    initial_prompt = f"Start the voice practice session. Greet the student and introduce the first task from the lesson objectives."
    
    try:
        ai_response = gemini.get_lesson_voice_response(
            user_message=initial_prompt,
            lesson=lesson,
            chat_history_objects=[],
            user_profile=user
        )
        
        ai_content = ai_response.get('response', 'Hello! Let\'s start practicing English.')
        translation = ai_response.get('translation', '')
        
        # Generate TTS audio
        speech_service = SpeechService()
        audio_bytes = speech_service.synthesize_speech(ai_content)
        filename = f"vp_{session.id}_init.mp3"
        audio_url = speech_service.save_audio_file(audio_bytes, filename)
        
        # Save AI message using helper
        from apps.chat.services.chat_helpers import create_ai_message
        ai_message = create_ai_message(
            session,
            ai_response,
            source_type='voice',
            audio_url=audio_url
        )
        
        return JsonResponse({
            'session_id': session.id,
            'initial_message': {
                'id': ai_message.id,
                'role': 'model',
                'content': ai_content,
                'translation': translation,
                'audio_url': audio_url
            },
            'continued': False
        })
        
    except Exception as e:
        logger.error(f"Error starting voice practice: {e}", exc_info=True)
        session.delete()  # Clean up failed session
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@paid_user_required
@require_POST
@csrf_protect
def process_lesson_voice_audio(request, lesson_id):
    """
    Process audio input for Voice Practice: STT → AI response → TTS
    Uses FULL voice chat logic (corrections, translations, explanations)
    """
    from apps.voice.services.speech import SpeechService
    import logging
    logger = logging.getLogger(__name__)
    
    lesson = get_object_or_404(Lesson, id=lesson_id, is_active=True)
    user = request.user
    
    # Get active session
    session = ChatSession.objects.filter(
        user=user,
        lesson=lesson,
        session_type='lesson_voice_practice',
        is_active=True
    ).first()
    
    if not session:
        return JsonResponse({'error': 'No active voice practice session'}, status=400)
    
    # Get audio file from request
    audio_file = request.FILES.get('audio')
    if not audio_file:
        return JsonResponse({'error': 'No audio file provided'}, status=400)
    
    try:
        speech_service = SpeechService()
        
        # STT: Convert audio to text
        user_text = speech_service.transcribe_audio(audio_file)
        if not user_text or 'Error' in user_text:
            return JsonResponse({'error': 'Could not transcribe audio'}, status=400)
        
        # Save user message using helper
        from apps.chat.services.chat_helpers import create_user_message
        user_message = create_user_message(
            session,
            user_text,
            source_type='voice',
            transcript=user_text
        )
        
        # Get chat history using helper
        from apps.chat.services.chat_helpers import get_chat_history
        history = get_chat_history(session, exclude_message_id=user_message.id)
        
        # Get AI response with FULL logic
        gemini = GeminiService()
        ai_response = gemini.get_lesson_voice_response(
            user_message=user_text,
            lesson=lesson,
            chat_history_objects=history,
            user_profile=user
        )
        
        ai_content = ai_response.get('response', 'I see.')
        translation = ai_response.get('translation', '')
        corrected_text = ai_response.get('corrected_text', '')
        explanation = ai_response.get('explanation', '')
        full_english_version = ai_response.get('full_english_version', '')
        phase = ai_response.get('phase', 'initial')
        has_errors = ai_response.get('has_errors', False)
        should_finish = ai_response.get('should_finish', False)
        
        # TTS: Convert AI response to audio
        audio_bytes = speech_service.synthesize_speech(ai_content)
        filename = f"vp_{session.id}_{user_message.id}.mp3"
        audio_url = speech_service.save_audio_file(audio_bytes, filename)
        
        # Save AI message using helper
        from apps.chat.services.chat_helpers import create_ai_message
        ai_msg = create_ai_message(
            session,
            ai_response,
            source_type='voice',
            audio_url=audio_url
        )
        
        return JsonResponse({
            'user_text': user_text,
            'transcript': user_text,
            'ai_message': ai_content,
            'translation': translation,
            'corrected_text': corrected_text,
            'explanation': explanation,
            'full_english_version': full_english_version,
            'audio_url': audio_url,
            'phase': phase,
            'has_errors': has_errors,
            'should_finish': should_finish,
            'message_id': ai_msg.id,
            'session_id': session.id
        })
        
    except Exception as e:
        logger.error(f"Error processing audio: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@paid_user_required
@require_POST
@csrf_protect
def process_lesson_voice_text(request, lesson_id):
    """
    Process text input for Voice Practice (alternative to audio)
    Uses FULL voice chat logic (corrections, translations, explanations)
    """
    from apps.voice.services.speech import SpeechService
    import logging
    logger = logging.getLogger(__name__)
    
    lesson = get_object_or_404(Lesson, id=lesson_id, is_active=True)
    user = request.user
    
    # Get active session
    session = ChatSession.objects.filter(
        user=user,
        lesson=lesson,
        session_type='lesson_voice_practice',
        is_active=True
    ).first()
    
    if not session:
        return JsonResponse({'error': 'No active voice practice session'}, status=400)
    
    # Get text from request
    user_text = request.POST.get('text', '').strip()
    if not user_text:
        return JsonResponse({'error': 'No text provided'}, status=400)
    
    try:
        # Save user message using helper
        from apps.chat.services.chat_helpers import create_user_message
        user_message = create_user_message(
            session,
            user_text,
            source_type='voice'
        )
        
        # Get chat history using helper
        from apps.chat.services.chat_helpers import get_chat_history
        history = get_chat_history(session, exclude_message_id=user_message.id)
        
        # Get AI response with FULL logic
        gemini = GeminiService()
        ai_response = gemini.get_lesson_voice_response(
            user_message=user_text,
            lesson=lesson,
            chat_history_objects=history,
            user_profile=user
        )
        
        ai_content = ai_response.get('response', 'I see.')
        translation = ai_response.get('translation', '')
        corrected_text = ai_response.get('corrected_text', '')
        explanation = ai_response.get('explanation', '')
        full_english_version = ai_response.get('full_english_version', '')
        phase = ai_response.get('phase', 'initial')
        has_errors = ai_response.get('has_errors', False)
        should_finish = ai_response.get('should_finish', False)
        
        # TTS: Convert AI response to audio
        speech_service = SpeechService()
        audio_bytes = speech_service.synthesize_speech(ai_content)
        filename = f"vp_{session.id}_{user_message.id}.mp3"
        audio_url = speech_service.save_audio_file(audio_bytes, filename)
        
        # Save AI message using helper
        from apps.chat.services.chat_helpers import create_ai_message
        ai_msg = create_ai_message(
            session,
            ai_response,
            source_type='voice',
            audio_url=audio_url
        )
        
        return JsonResponse({
            'ai_message': ai_content,
            'translation': translation,
            'corrected_text': corrected_text,
            'explanation': explanation,
            'full_english_version': full_english_version,
            'audio_url': audio_url,
            'phase': phase,
            'has_errors': has_errors,
            'should_finish': should_finish,
            'message_id': ai_msg.id,
            'session_id': session.id,
            'user_message': user_text
        })
        
    except Exception as e:
        logger.error(f"Error processing text: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@paid_user_required
@require_POST
@csrf_protect
def evaluate_lesson_voice_practice(request, lesson_id):
    """
    Evaluate completed Voice Practice session and update user progress
    """
    import logging
    logger = logging.getLogger(__name__)
    
    lesson = get_object_or_404(Lesson, id=lesson_id, is_active=True)
    user = request.user
    
    # Get active session
    session = ChatSession.objects.filter(
        user=user,
        lesson=lesson,
        session_type='lesson_voice_practice',
        is_active=True
    ).first()
    
    if not session:
        return JsonResponse({'error': 'No active voice practice session'}, status=400)
    
    try:
        # Evaluate session
        gemini = GeminiService()
        evaluation = gemini.evaluate_lesson_voice_practice(
            session=session,
            lesson=lesson,
            user_profile=user
        )
        
        # Mark session as completed
        session.is_active = False
        session.save()
        
        # Update user progress
        progress, created = UserLessonProgress.objects.get_or_create(
            user=user,
            lesson=lesson
        )
        
        progress.voice_practice_completed = True
        progress.voice_practice_score = evaluation.get('overall_score', 7.0)
        progress.voice_practice_feedback = evaluation
        progress.save()
        
        # Update overall score
        progress.calculate_overall_score()
        
        return JsonResponse({
            'success': True,
            'evaluation': evaluation
        })
        
    except Exception as e:
        logger.error(f"Error evaluating voice practice: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@paid_user_required
@require_POST
@csrf_protect
def continue_roleplay_voice(request, session_id):
    """
    Continue Role-Play session with voice input (audio → STT → AI → TTS)
    Saves to ChatMessage for consistent rendering with rich UI
    """
    from apps.voice.services.speech import SpeechService
    from apps.chat.services.chat_helpers import create_user_message, create_ai_message
    import logging
    logger = logging.getLogger(__name__)
    
    session = get_object_or_404(RolePlaySession, id=session_id, user=request.user)
    
    # Get audio file
    audio_file = request.FILES.get('audio')
    if not audio_file:
        return JsonResponse({'error': 'No audio file provided'}, status=400)
    
    try:
        speech_service = SpeechService()
        
        # STT
        user_text = speech_service.transcribe_audio(audio_file)
        if not user_text:
            return JsonResponse({'error': 'Could not transcribe audio'}, status=400)
        
        # Continue Role-Play dialogue
        engine = RolePlayEngine()
        
        # Add user message to history
        session.messages_history.append({
            'role': 'user',
            'content': user_text
        })
        
        # Restore session
        chat = engine.restore_session(
            system_prompt=session.system_prompt,
            messages_history=session.messages_history
        )
        
        if not chat:
            return JsonResponse({'error': 'Failed to restore session'}, status=500)
        
        # Get AI response
        result = engine.continue_dialogue(chat, user_text)
        if not result.get('success'):
            return JsonResponse({'error': result.get('error', 'AI response failed')}, status=500)
        
        ai_message = result['ai_message']
        
        # Add AI response to history
        session.messages_history.append({
            'role': 'model',
            'content': ai_message
        })
        
        # Update dialogue
        session.dialogue.append({
            'role': 'user',
            'content': user_text,
            'timestamp': timezone.now().isoformat()
        })
        session.dialogue.append({
            'role': 'ai',
            'content': ai_message,
            'timestamp': timezone.now().isoformat()
        })
        
        session.user_messages_count += 1
        session.messages_count += 2
        session.save()
        
        # TTS
        audio_bytes = speech_service.synthesize_speech(ai_message)
        filename = f"rp_{session.id}_{session.messages_count}.mp3"
        audio_url = speech_service.save_audio_file(audio_bytes, filename)
        
        # GET or CREATE ChatSession for rendering
        chat_session, _ = ChatSession.objects.get_or_create(
            user=session.user,
            lesson=session.lesson,
            session_type='roleplay_voice',
            is_active=True,
            defaults={'title': f"Role-Play: {session.scenario_name}"}
        )
        
        # Save user message to ChatMessage
        user_msg = create_user_message(
            chat_session,
            user_text,
            source_type='voice',
            transcript=user_text
        )
        
        # Build AI response dict for helper
        ai_response_dict = {
            'response': result.get('ai_message', ''),
            'translation': result.get('translation'),  # From RolePlayEngine
            'explanation': result.get('explanation'),  # From RolePlayEngine
            'corrected_text': result.get('corrected_text'),  # From RolePlayEngine
            'full_english_version': None,
            'phase': 'initial',
            'has_errors': False
        }
        
        # Save AI message to ChatMessage with audio URL
        ai_msg = create_ai_message(
            chat_session,
            ai_response_dict,
            source_type='voice',
            audio_url=audio_url
        )
        
        return JsonResponse({
            'success': True,
            'user_text': user_text,
            'ai_message': ai_message,
            'audio_url': audio_url,
            'transcript': user_text,
            'message_id': ai_msg.id  # For rendering via server partial
        })
        
    except Exception as e:
        logger.error(f"Error in role-play voice: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
