"""
Management команда для генерації AI контенту для уроків
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.chat.models import Lesson, Module
from apps.chat.services.lesson_enhancer import LessonContentEnhancer
import time
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate AI prompts and evaluation criteria for lessons (voice_practice_prompts & homework_instructions)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--level',
            type=str,
            default='all',
            choices=['A0', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'all'],
            help='Level to process: A0, A1, A2, B1, B2, C1, C2, or all'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of lessons per batch (API rate limiting)'
        )
        parser.add_argument(
            '--prompts-only',
            action='store_true',
            help='Only generate voice_practice_prompts'
        )
        parser.add_argument(
            '--homework-only',
            action='store_true',
            help='Only generate homework_instructions'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without saving'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed progress'
        )
    
    def handle(self, *args, **options):
        level = options['level'].upper()
        batch_size = options['batch_size']
        prompts_only = options['prompts_only']
        homework_only = options['homework_only']
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        # Validate level
        valid_levels = ['A0', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'ALL']
        if level not in valid_levels:
            raise CommandError(f'Invalid level: {level}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        
        # Get lessons
        if level == 'ALL':
            lessons = Lesson.objects.filter(is_active=True).order_by('module__level', 'lesson_number')
            levels_to_process = ['A0', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2']
        else:
            lessons = Lesson.objects.filter(module__level=level, is_active=True).order_by('lesson_number')
            levels_to_process = [level]
        
        total_lessons = lessons.count()
        if total_lessons == 0:
            raise CommandError(f'No lessons found for level {level}')
        
        self.stdout.write(self.style.SUCCESS(f'\n📚 Found {total_lessons} lessons to process'))
        self.stdout.write(f'   Batch size: {batch_size} lessons per batch\n')
        
        enhancer = LessonContentEnhancer()
        processed = 0
        skipped = 0
        
        try:
            for i, lesson in enumerate(lessons):
                # Skip if already has content (unless force)
                has_prompts = lesson.voice_practice_prompts and len(lesson.voice_practice_prompts) > 0
                has_homework = lesson.homework_instructions and len(lesson.homework_instructions) > 0
                
                if (has_prompts and has_homework) and not prompts_only and not homework_only:
                    if verbose:
                        self.stdout.write(f'⏭️  Skipping {lesson.module.level}-L{lesson.lesson_number}: already has content')
                    skipped += 1
                    continue
                
                # Generate content
                updated_fields = []
                
                if not prompts_only and (not has_prompts or homework_only):
                    if dry_run:
                        prompts = ['[DRY] Prompt 1', '[DRY] Prompt 2', '[DRY] Prompt 3']
                        if verbose:
                            self.stdout.write(f'  ✓ Would generate {len(prompts)} voice prompts')
                    else:
                        prompts = enhancer.generate_voice_prompts(lesson)
                        if prompts:
                            lesson.voice_practice_prompts = prompts
                            updated_fields.append('voice_practice_prompts')
                            if verbose:
                                self.stdout.write(f'  ✓ Generated {len(prompts)} voice prompts')
                
                if not homework_only and (not has_homework or prompts_only):
                    if dry_run:
                        criteria = {'criteria': {'dummy': {'weight': 100, 'description': '[DRY]'}}, 'min_passing_score': 6.0}
                        if verbose:
                            self.stdout.write(f'  ✓ Would generate homework criteria')
                    else:
                        criteria = enhancer.generate_homework_criteria(lesson)
                        if criteria and 'criteria' in criteria:
                            lesson.homework_instructions = criteria
                            updated_fields.append('homework_instructions')
                            if verbose:
                                self.stdout.write(f'  ✓ Generated homework criteria')
                
                # Save if not dry-run
                if updated_fields and not dry_run:
                    lesson.save(update_fields=updated_fields)
                    processed += 1
                elif not dry_run:
                    skipped += 1
                else:
                    processed += 1
                
                if verbose:
                    self.stdout.write(f'[{i+1}/{total_lessons}] {lesson.module.level}-L{lesson.lesson_number}: {lesson.title}')
                
                # Rate limiting: pause between batches
                if (i + 1) % batch_size == 0 and i + 1 < total_lessons:
                    self.stdout.write(self.style.WARNING(f'\n⏸️  Batch {(i+1)//batch_size} complete. Waiting 2s for API rate limit...'))
                    time.sleep(2)
        
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            raise CommandError(f'Error during generation: {str(e)}')
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n✅ Complete!'))
        self.stdout.write(f'   Processed: {processed}')
        self.stdout.write(f'   Skipped: {skipped}')
        if dry_run:
            self.stdout.write(self.style.WARNING(f'   (DRY RUN - no changes saved)'))
