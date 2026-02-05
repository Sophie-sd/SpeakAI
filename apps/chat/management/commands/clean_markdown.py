import re
from django.core.management.base import BaseCommand
from apps.chat.models import Lesson


class Command(BaseCommand):
    help = 'Remove markdown formatting symbols from lesson theory_content'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test',
            action='store_true',
            help='Test on first lesson only',
        )
        parser.add_argument(
            '--lesson-id',
            type=int,
            help='Process specific lesson by ID',
        )

    def clean_markdown(self, text):
        if not text:
            return text

        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            cleaned = line

            cleaned = re.sub(r'^#{1,6}\s+', '', cleaned)

            cleaned = re.sub(r'\*\*(.+?)\*\*', r'\1', cleaned)

            cleaned = re.sub(r'__(.+?)__', r'\1', cleaned)

            cleaned = re.sub(r'\*(.+?)\*', r'\1', cleaned)

            cleaned = re.sub(r'_(.+?)_', r'\1', cleaned)

            cleaned = re.sub(r'`(.+?)`', r'\1', cleaned)

            cleaned_lines.append(cleaned)

        result = '\n'.join(cleaned_lines)

        result = re.sub(r'\n\n\n+', '\n\n', result)

        return result.strip()

    def handle(self, *args, **options):
        test_mode = options.get('test', False)
        lesson_id = options.get('lesson_id', None)

        if lesson_id:
            lessons = Lesson.objects.filter(id=lesson_id)
            self.stdout.write(self.style.WARNING(f'Processing lesson ID: {lesson_id}'))
        elif test_mode:
            lessons = Lesson.objects.all()[:1]
            self.stdout.write(self.style.WARNING('TEST MODE: Processing first lesson only'))
        else:
            lessons = Lesson.objects.all()
            self.stdout.write(f'Processing all {lessons.count()} lessons')

        updated_count = 0
        unchanged_count = 0

        for lesson in lessons:
            if not lesson.theory_content:
                unchanged_count += 1
                continue

            original = lesson.theory_content
            cleaned = self.clean_markdown(original)

            if original != cleaned:
                lesson.theory_content = cleaned
                lesson.save(update_fields=['theory_content'])
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Updated lesson {lesson.id}: {lesson.title[:50]}')
                )
            else:
                unchanged_count += 1

        self.stdout.write(self.style.SUCCESS(f'\nCompleted!'))
        self.stdout.write(f'Updated: {updated_count} lessons')
        self.stdout.write(f'Unchanged: {unchanged_count} lessons')
