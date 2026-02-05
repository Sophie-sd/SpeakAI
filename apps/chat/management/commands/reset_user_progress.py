from django.core.management.base import BaseCommand
from apps.users.models import CustomUser
from apps.chat.models import UserModuleProgress, UserLessonProgress


class Command(BaseCommand):
    help = 'Reset user progress to start from beginning'
    
    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to reset progress for')
        parser.add_argument(
            '--level',
            type=str,
            default=None,
            help='Optionally change user level (A0-C2)'
        )
    
    def handle(self, *args, **options):
        username = options['username']
        new_level = options.get('level')
        
        try:
            user = CustomUser.objects.get(username=username)
        except CustomUser.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ User "{username}" not found'))
            return
        
        # Delete all progress
        module_progress_count = UserModuleProgress.objects.filter(user=user).count()
        lesson_progress_count = UserLessonProgress.objects.filter(user=user).count()
        
        UserModuleProgress.objects.filter(user=user).delete()
        UserLessonProgress.objects.filter(user=user).delete()
        
        # Optionally change level
        if new_level:
            valid_levels = dict(user.LEVEL_CHOICES)
            if new_level.upper() not in valid_levels:
                self.stdout.write(
                    self.style.ERROR(f'❌ Invalid level: {new_level}. Valid levels: {", ".join(valid_levels.keys())}')
                )
                return
            
            user.level = new_level.upper()
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Progress reset for "{username}"\n'
                    f'   - Deleted {module_progress_count} module progress records\n'
                    f'   - Deleted {lesson_progress_count} lesson progress records\n'
                    f'   - Level changed to: {new_level.upper()}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Progress reset for "{username}"\n'
                    f'   - Deleted {module_progress_count} module progress records\n'
                    f'   - Deleted {lesson_progress_count} lesson progress records\n'
                    f'   - Level: {user.level} (unchanged)'
                )
            )
