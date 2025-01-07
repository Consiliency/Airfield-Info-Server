from .settings import *

DEBUG = False
ALLOWED_HOSTS = ['*']  # You should update this with your EB URL once created

# Configure database for RDS
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('RDS_DB_NAME'),
        'USER': os.environ.get('RDS_USERNAME'),
        'PASSWORD': os.environ.get('RDS_PASSWORD'),
        'HOST': os.environ.get('RDS_HOSTNAME'),
        'PORT': os.environ.get('RDS_PORT'),
    }
}

# Static files configuration
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATIC_URL = '/static/'

# Security settings
SECURE_SSL_REDIRECT = False  # Set to True if you have SSL configured
SESSION_COOKIE_SECURE = False  # Set to True if you have SSL configured
CSRF_COOKIE_SECURE = False  # Set to True if you have SSL configured 