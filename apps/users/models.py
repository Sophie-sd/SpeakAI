from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    LEVEL_CHOICES = [
        ('A0', 'Starter'),
        ('A1', 'Beginner'),
        ('A2', 'Elementary'),
        ('B1', 'Intermediate'),
        ('B2', 'Upper Intermediate'),
        ('C1', 'Advanced'),
        ('C2', 'Proficient'),
    ]

    level = models.CharField(max_length=2, choices=LEVEL_CHOICES, default='A1')
    native_language = models.CharField(max_length=50, default='Ukrainian')
    is_paid = models.BooleanField(default=False)
    subscription_end = models.DateField(null=True, blank=True)
    interests = models.JSONField(default=list, blank=True)
    onboarding_completed = models.BooleanField(default=False)

    def __str__(self):
        return self.username
