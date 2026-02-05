# Fixtures для тестування

"""
python manage.py loaddata test_fixtures
"""

from apps.users.models import CustomUser
from apps.chat.models import Module, Lesson
from django.core.management import call_command


def create_test_user():
    """Створити тестового користувача"""
    user, created = CustomUser.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'level': 'A1',
            'is_paid': True,
            'onboarding_completed': True
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
    return user


def create_test_module():
    """Створити тестовий модуль"""
    module, _ = Module.objects.get_or_create(
        level='A1',
        module_number=1,
        defaults={
            'title': "Test Module: My World",
            'description': "Introduction to English",
            'total_lessons': 2,
            'estimated_duration_weeks': 1,
            'learning_objectives': ['Learn greetings', 'Basic vocabulary'],
            'is_active': True
        }
    )
    return module


def create_test_lesson(module):
    """Створити тестовий урок"""
    lesson, _ = Lesson.objects.get_or_create(
        module=module,
        lesson_number=1,
        defaults={
            'title': "Greetings and Introductions",
            'description': "Learn how to greet people",
            'grammar_focus': "Present Simple - to be",
            'vocabulary_list': ['hello', 'goodbye', 'thank you', 'please'],
            'theory_content': "<h2>Greetings</h2><p>Hello - вітання</p>",
            'homework_description': "Write 5 sentences introducing yourself",
            'homework_instructions': {
                'criteria': {
                    'grammar': {'weight': 50, 'description': 'Grammar accuracy'},
                    'vocabulary': {'weight': 50, 'description': 'Vocabulary usage'}
                },
                'min_passing_score': 6.0,
                'feedback_language': 'ukrainian'
            },
            'role_play_scenario': {
                'setting': 'Meeting a new friend',
                'ai_role': 'A friendly person',
                'user_role': 'Student',
                'objectives': ['Introduce yourself', 'Ask their name'],
                'difficulty': 'easy'
            },
            'voice_practice_prompts': [
                "Hello, my name is...",
                "Nice to meet you",
                "How are you?"
            ],
            'is_active': True
        }
    )
    return lesson


if __name__ == '__main__':
    print("Creating test fixtures...")
    user = create_test_user()
    print(f"✓ Created user: {user.username}")
    
    module = create_test_module()
    print(f"✓ Created module: {module.title}")
    
    lesson = create_test_lesson(module)
    print(f"✓ Created lesson: {lesson.title}")
    
    print("\nTest fixtures created successfully!")
    print(f"Login: testuser / testpass123")
