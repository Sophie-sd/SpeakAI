#!/usr/bin/env bash
# Build script for Render Blueprint deployment
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

echo "Build completed successfully!"
