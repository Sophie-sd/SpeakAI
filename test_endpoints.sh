#!/bin/bash

# Quick test script for Lesson Voice Chat features
# Run this to verify all endpoints are working

echo "Testing Lesson Voice Chat endpoints..."
echo "======================================="

# Test 1: Start Voice Practice
echo ""
echo "Test 1: Start Voice Practice for lesson 372"
curl -X POST http://127.0.0.1:8000/chat/lesson/372/voice-practice-chat/ \
  -H "Content-Type: application/json" \
  -d '{}' \
  --cookie-jar cookies.txt \
  --silent | jq .

# Test 2: Start Role-Play
echo ""
echo "Test 2: Start Role-Play for lesson 372"
curl -X POST http://127.0.0.1:8000/chat/lesson/372/roleplay/start/ \
  -H "Content-Type: application/json" \
  -d '{}' \
  --cookie cookies.txt \
  --silent | jq .

echo ""
echo "======================================="
echo "If you see JSON responses above, endpoints are working!"
echo "If you see HTML login page, run: python manage.py createsuperuser"
echo "Then login at http://127.0.0.1:8000/admin/ and try again"
