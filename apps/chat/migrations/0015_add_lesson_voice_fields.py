# Generated migration for lesson voice practice features

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0014_userlessonprogress_quiz_completed_and_more'),
    ]

    operations = [
        # Add SESSION_TYPE_CHOICES to ChatSession
        migrations.AddField(
            model_name='chatsession',
            name='lesson',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='chat_sessions',
                to='chat.lesson'
            ),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='session_type',
            field=models.CharField(
                choices=[
                    ('general', 'General Chat'),
                    ('voice', 'Voice Chat'),
                    ('lesson_voice_practice', 'Lesson Voice Practice'),
                ],
                default='general',
                max_length=50
            ),
        ),
        migrations.AddField(
            model_name='chatsession',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        # Add feedback fields to UserLessonProgress
        migrations.AddField(
            model_name='userlessonprogress',
            name='voice_practice_feedback',
            field=models.JSONField(
                null=True,
                blank=True,
                help_text='Детальний фідбек за голосову практику'
            ),
        ),
        migrations.AddField(
            model_name='userlessonprogress',
            name='role_play_feedback',
            field=models.JSONField(
                null=True,
                blank=True,
                help_text='Детальний фідбек за рольову гру'
            ),
        ),
    ]
