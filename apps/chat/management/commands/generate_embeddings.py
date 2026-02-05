"""
Management command to generate embeddings for KnowledgeBase items
Usage: python manage.py generate_embeddings
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.chat.models import KnowledgeBase
import logging

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class Command(BaseCommand):
    help = 'Generate embeddings for KnowledgeBase items using Google Gemini'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip items that already have embeddings',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of items to process before saving',
        )

    def handle(self, *args, **options):
        if not GENAI_AVAILABLE:
            self.stderr.write(self.style.ERROR('google-genai package not installed'))
            return

        if not settings.GEMINI_API_KEY:
            self.stderr.write(self.style.ERROR('GEMINI_API_KEY not configured in .env'))
            return

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        skip_existing = options['skip_existing']
        batch_size = options['batch_size']

        # Get items to process
        if skip_existing:
            items = KnowledgeBase.objects.filter(embedding__isnull=True)
        else:
            items = KnowledgeBase.objects.all()

        total = items.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('No items to process'))
            return

        self.stdout.write(f"Processing {total} items...")

        processed = 0
        for i, item in enumerate(items, 1):
            try:
                # Generate embedding
                embedding_response = client.models.embed_content(
                    model='gemini-embedding-001',
                    contents=f"{item.topic}: {item.content}",
                    config=types.EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT"
                    )
                )
                
                # Save embedding
                item.embedding = embedding_response.embeddings[0].values
                item.save(update_fields=['embedding'])

                processed += 1

                if i % batch_size == 0:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Processed {i}/{total} items")
                    )

            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"Error processing item {item.id}: {e}")
                )
                continue

        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Successfully processed {processed}/{total} items")
        )
