"""
Custom decorators for user authentication and authorization
"""
from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse


def paid_user_required(view_func):
    """
    Decorator to check if user has active paid subscription
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse('login'))
        
        if not request.user.is_paid:
            return redirect(reverse('subscription_required'))
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


def onboarding_required(view_func):
    """
    Decorator to check if user has completed onboarding
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse('login'))
        
        # Check if user has completed onboarding (if field exists)
        if hasattr(request.user, 'onboarding_completed') and not request.user.onboarding_completed:
            return redirect(reverse('onboarding_test'))
        
        return view_func(request, *args, **kwargs)
    
    return wrapped_view
