from django.http import HttpResponse
from django.shortcuts import render


def home(request):
    return render(request, 'core/home.html')


def healthz(request):
    """Health check endpoint for Render zero-downtime deploys."""
    return HttpResponse("OK", status=200)
