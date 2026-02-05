from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import UserRegistrationForm

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('chat')
    else:
        form = UserRegistrationForm()
    return render(request, 'users/register.html', {'form': form})


@login_required
def subscription_required(request):
    """Сторінка для не-платних користувачів"""
    return render(request, 'users/subscription_required.html')


@login_required
def onboarding_test(request):
    """Сторінка onboarding тесту"""
    if request.method == 'POST':
        # Обробити вибір рівня
        level = request.POST.get('level')
        goals = request.POST.getlist('goal')
        frequency = request.POST.get('frequency')
        
        # Оновити користувача
        user = request.user
        if level:
            user.level = level
        if frequency:
            user.practice_frequency = frequency
        user.onboarding_completed = True
        user.save()
        
        # Редірект на learning program або chat
        if user.is_paid:
            return redirect('learning_program')
        else:
            return redirect('chat')
    
    # Показати форму оцінювання рівня
    level_options = [
        {'value': 'A0', 'label': 'A0 - Starter (Complete beginner)'},
        {'value': 'A1', 'label': 'A1 - Beginner (I know a few words)'},
        {'value': 'A2', 'label': 'A2 - Elementary (I can hold basic conversations)'},
        {'value': 'B1', 'label': 'B1 - Intermediate (I can discuss various topics)'},
        {'value': 'B2', 'label': 'B2 - Upper Intermediate (I\'m quite fluent)'},
        {'value': 'C1', 'label': 'C1 - Advanced (I speak fluently)'},
        {'value': 'C2', 'label': 'C2 - Proficient (Nearly native speaker)'},
    ]
    
    frequency_options = [
        {'value': 'daily', 'label': 'Daily (30-60 min)'},
        {'value': '3-4times', 'label': '3-4 times per week'},
        {'value': '2times', 'label': '2 times per week'},
        {'value': 'weekly', 'label': 'Once a week'},
    ]
    
    goal_options = [
        {'value': 'conversation', 'label': 'Improve conversation skills'},
        {'value': 'grammar', 'label': 'Master grammar rules'},
        {'value': 'vocabulary', 'label': 'Expand vocabulary'},
        {'value': 'pronunciation', 'label': 'Improve pronunciation'},
        {'value': 'exam', 'label': 'Prepare for an exam'},
    ]
    
    return render(request, 'users/onboarding_test.html', {
        'level_options': level_options,
        'frequency_options': frequency_options,
        'goal_options': goal_options,
    })
