"""
Перегенерація voice_practice_prompts для уроків де вони не були створені
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.chat.models import Lesson
from apps.chat.services.lesson_enhancer import LessonContentEnhancer
import time
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Regenerate missing voice_practice_prompts with longer delays between requests'
    
    def add_arguments(self, parser):
        parser.add_argument('--delay', type=int, default=5, help='Delay between requests in seconds')
        parser.add_argument('--dry-run', action='store_true')
    
    def handle(self, *args, **options):
        delay = options['delay']
        dry_run = options['dry_run']
        
        # Find lessons without voice prompts
        lessons_without_prompts = Lesson.objects.filter(
            voice_practice_prompts=[],
            is_active=True
        ).order_by('module__level', 'lesson_number')
        
        total = lessons_without_prompts.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✓ All lessons have voice prompts!'))
            return
        
        self.stdout.write(self.style.WARNING(f'\n🔄 Regenerating {total} missing voice prompts (delay: {delay}s between requests)\n'))
        
        enhancer = LessonContentEnhancer()
        success_count = 0
        
        for i, lesson in enumerate(lessons_without_prompts):
            prompts = enhancer.generate_voice_prompts(lesson)
            
            if prompts:
                if not dry_run:
                    lesson.voice_practice_prompts = prompts
                    lesson.save(update_fields=['voice_practice_prompts'])
                    success_count += 1
                
                self.stdout.write(f'[{i+1}/{total}] ✓ {lesson.module.level}-L{lesson.lesson_number}: {len(prompts)} prompts')
            else:
                self.stdout.write(self.style.WARNING(f'[{i+1}/{total}] ✗ {lesson.module.level}-L{lesson.lesson_number}: failed'))
            
            # Delay before next request
            if i < total - 1:
                time.sleep(delay)
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Regenerated {success_count}/{total} prompts'))
        if dry_run:
            self.stdout.write(self.style.WARNING('(DRY RUN - no changes saved)'))
