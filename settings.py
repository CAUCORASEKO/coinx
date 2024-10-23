import os
import sys
from pathlib import Path
from cryptography.fernet import Fernet
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Secret key and debug settings
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-05zaqfi0rmq(+6xw70jpted)-6wy*$lnp&)&4k=(6-x-no)fa0')
DEBUG = os.getenv('DEBUG', 'True') == 'True'

# Allowed hosts settings
ALLOWED_HOSTS = ['*'] if DEBUG else ['coinx-production.up.railway.app', 'localhost', '127.0.0.1']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'web',  # Custom app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Whitenoise middleware for serving static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'web/templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'wsgi.application'

# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3' if DEBUG else 'django.db.backends.postgresql',
        'NAME': str(BASE_DIR / 'db.sqlite3') if DEBUG else '',
        **(dj_database_url.config(default=os.getenv('DATABASE_URL')) if not DEBUG else {}),
    }
}

# Debug information for the console
print(f"BASE_DIR: {BASE_DIR}", file=sys.stderr)
print(f"DATABASE PATH: {DATABASES['default'].get('NAME', 'Not set')}", file=sys.stderr)

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Static files storage configuration for production
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Additional locations of static files
STATICFILES_DIRS = [BASE_DIR / 'web/static']

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email configuration
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
    DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# CoinPayments API Keys
COINPAYMENTS_API_KEY = os.getenv('COINPAYMENTS_API_KEY')
COINPAYMENTS_API_SECRET = os.getenv('COINPAYMENTS_API_SECRET')

# Encryption key
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

# Check if the encryption key is set and valid
if not ENCRYPTION_KEY:
    print("WARNING: No encryption key found. Set the 'ENCRYPTION_KEY' environment variable.", file=sys.stderr)
else:
    try:
        # Verify that the encryption key is valid
        Fernet(ENCRYPTION_KEY)
    except Exception as e:
        print(f"ERROR: Invalid encryption key: {e}", file=sys.stderr)
        ENCRYPTION_KEY = None  # Set to None to handle it gracefully later if needed

# Login redirect URL
LOGIN_REDIRECT_URL = '/dashboard/'

# CSRF trusted origins
if not DEBUG:
    CSRF_TRUSTED_ORIGINS = ['https://coinx-production.up.railway.app']

# Security settings for production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'web': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
