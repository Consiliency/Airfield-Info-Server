#!/bin/bash
export DJANGO_SETTINGS_MODULE=config.settings
export GOOGLE_MAPS_API_KEY=AIzaSyDGLqiG9S1Y9qMOd4RM0P24UhrZPROJXTY
export DEBUG=True
export SECRET_KEY="django-insecure-vyu_^0zu!z2*+7@xd@m*dlrn2kc96$0^t#p6&z@++x0d2mj8e@"
export DATABASE_URL="postgres://airfield_user:airfield_password@localhost:5432/airfield_info"
export ALLOWED_HOSTS="localhost,127.0.0.1"

poetry run python manage.py runserver 