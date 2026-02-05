from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'level', 'is_paid', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('level', 'native_language', 'is_paid', 'subscription_end', 'interests')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
