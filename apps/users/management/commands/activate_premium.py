from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.users.models import CustomUser


class Command(BaseCommand):
    help = 'Активує або деактивує премієм доступ для користувача'

    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            type=str,
            help='Ім\'я користувача'
        )
        parser.add_argument(
            '--deactivate',
            action='store_true',
            help='Деактивувати премієм'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='Кількість днів для активації (за замовчуванням: 365)'
        )

    def handle(self, *args, **options):
        username = options['username']
        deactivate = options['deactivate']
        days = options['days']

        try:
            user = CustomUser.objects.get(username=username)
        except CustomUser.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Користувач "{username}" не знайдений'))
            return

        if deactivate:
            # Деактивувати премієм
            user.is_paid = False
            user.subscription_end = None
            user.save()
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Премієм деактивовано для користувача "{username}"'
                )
            )
        else:
            # Активувати премієм
            user.is_paid = True
            user.subscription_end = timezone.now().date() + timedelta(days=days)
            user.onboarding_completed = True
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Премієм активовано для користувача "{username}"\n'
                    f'   - Status: PREMIUM\n'
                    f'   - Subscription end: {user.subscription_end}\n'
                    f'   - Onboarding: Completed'
                )
            )
