#!/bin/bash

# Install system dependencies
sudo yum update -y
sudo yum install -y python3.11-devel postgresql-devel

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
export PATH="/root/.local/bin:$PATH"

# Install project dependencies
cd /var/app/staging
poetry config virtualenvs.create false
poetry install --no-dev

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate --noinput 