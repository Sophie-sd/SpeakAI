"""
Management команда для валідації контенту уроків
"""

from django.core.management.base import BaseCommand, CommandError
from apps.chat.models import Lesson
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Validate lesson content structure: voice_practice_prompts & homework_instructions'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--level',
            type=str,
            default='all',
            choices=['A0', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'all'],
            help='Level to validate'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed report'
        )
        parser.add_argument(
            '--fix-weights',
            action='store_true',
            help='Automatically fix weight sums to 100'
        )
    
    def handle(self, *args, **options):
        level = options['level'].upper()
        verbose = options['verbose']
        fix_weights = options['fix_weights']
        
        # Get lessons
        if level == 'ALL':
            lessons = Lesson.objects.filter(is_active=True).order_by('module__level', 'lesson_number')
        else:
            lessons = Lesson.objects.filter(module__level=level, is_active=True).order_by('lesson_number')
        
        total = lessons.count()
        if total == 0:
            raise CommandError(f'No lessons found for level {level}')
        
        self.stdout.write(self.style.SUCCESS(f'\n🔍 Validating {total} lessons\n'))
        
        issues = {
            'no_voice_prompts': [],
            'invalid_voice_prompts': [],
            'no_homework_criteria': [],
            'invalid_homework_criteria': [],
            'weight_sum_errors': [],
        }
        
        fixed_count = 0
        
        for lesson in lessons:
            # Check voice_practice_prompts
            if not lesson.voice_practice_prompts or len(lesson.voice_practice_prompts) == 0:
                issues['no_voice_prompts'].append(f'{lesson.module.level}-L{lesson.lesson_number}')
            elif not isinstance(lesson.voice_practice_prompts, list):
                issues['invalid_voice_prompts'].append(f'{lesson.module.level}-L{lesson.lesson_number}')
            
            # Check homework_instructions
            if not lesson.homework_instructions or len(lesson.homework_instructions) == 0:
                issues['no_homework_criteria'].append(f'{lesson.module.level}-L{lesson.lesson_number}')
            elif not isinstance(lesson.homework_instructions, dict):
                issues['invalid_homework_criteria'].append(f'{lesson.module.level}-L{lesson.lesson_number}')
            else:
                # Validate homework_instructions structure
                criteria = lesson.homework_instructions.get('criteria', {})
                if not criteria:
                    issues['invalid_homework_criteria'].append(f'{lesson.module.level}-L{lesson.lesson_number}')
                else:
                    # Check weight sum
                    total_weight = sum(
                        c.get('weight', 0) 
                        for c in criteria.values()
                    )
                    
                    if abs(total_weight - 100) > 0.1:
                        issues['weight_sum_errors'].append(f'{lesson.module.level}-L{lesson.lesson_number} (sum={total_weight})')
                        
                        # Fix if requested
                        if fix_weights and total_weight > 0:
                            factor = 100 / total_weight
                            for criterion in criteria.values():
                                criterion['weight'] = round(criterion.get('weight', 0) * factor, 1)
                            lesson.homework_instructions['criteria'] = criteria
                            lesson.save(update_fields=['homework_instructions'])
                            fixed_count += 1
                            if verbose:
                                self.stdout.write(f'  ✓ Fixed weights for {lesson.module.level}-L{lesson.lesson_number}')
        
        # Report
        self.stdout.write(self.style.WARNING(f'\n📋 Validation Report\n'))
        
        issues_found = False
        for issue_type, lessons_list in issues.items():
            if lessons_list:
                issues_found = True
                color = self.style.ERROR if issue_type != 'weight_sum_errors' else self.style.WARNING
                self.stdout.write(color(f'{issue_type}: {len(lessons_list)}'))
                if verbose and len(lessons_list) <= 10:
                    for lesson_id in lessons_list:
                        self.stdout.write(f'   - {lesson_id}')
                elif verbose:
                    for lesson_id in lessons_list[:5]:
                        self.stdout.write(f'   - {lesson_id}')
                    self.stdout.write(f'   ... and {len(lessons_list) - 5} more')
        
        if not issues_found:
            self.stdout.write(self.style.SUCCESS(f'✅ All {total} lessons are valid!'))
        else:
            total_issues = sum(len(v) for v in issues.values())
            self.stdout.write(self.style.WARNING(f'\n⚠️  Total issues: {total_issues}'))
        
        if fixed_count > 0:
            self.stdout.write(self.style.SUCCESS(f'\n✓ Fixed {fixed_count} weight sum errors'))
