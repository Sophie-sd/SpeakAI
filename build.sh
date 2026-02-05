#!/bin/bash
# Build script for Render deployment

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput --clear

# Run migrations
python manage.py migrate

echo "Build completed successfully!"
