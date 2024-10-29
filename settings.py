# settings.py 
import os
import sys
from pathlib import Path
from cryptography.fernet import Fernet
import dj_database_url

# Rakentaa projektin polut tällä tavoin: BASE_DIR / 'alihakemisto'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Salainen avain ja debug-asetukset
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-05zaqfi0rmq(+6xw70jpted)-6wy*$lnp&)&4k=(6-x-no)fa0')
DEBUG = os.getenv('DEBUG', 'True') == 'True'

# Sallitut isännät
ALLOWED_HOSTS = ['*'] if DEBUG else ['coinx-production.up.railway.app', 'localhost', '127.0.0.1']

# Sovellusmääritykset
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'web',  # Mukautettu sovellus
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Whitenoise middleware staattisten tiedostojen palvelua varten
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

# Tietokannan konfigurointi
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3' if DEBUG else 'django.db.backends.postgresql',
        'NAME': str(BASE_DIR / 'db.sqlite3') if DEBUG else '',
        **(dj_database_url.config(default=os.getenv('DATABASE_URL')) if not DEBUG else {}),
    }
}

# Debug-tiedot konsolille
print(f"BASE_DIR: {BASE_DIR}", file=sys.stderr)
print(f"DATABASE PATH: {DATABASES['default'].get('NAME', 'Not set')}", file=sys.stderr)

# Salasanan validointiasetukset
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Kansainvälistymisasetukset
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Staattiset tiedostot (CSS, JavaScript, kuvat)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Staattisten tiedostojen varastointiasetus tuotannolle
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Muita staattisten tiedostojen sijainteja
STATICFILES_DIRS = [BASE_DIR / 'web/static'] if (BASE_DIR / 'web/static').exists() else []

# Ensisijainen avainkentän tyyppi
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Sähköpostin konfigurointi
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')  # Variable de entorno para el correo
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')  # Variable de entorno para la contraseña
    DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# CoinPayments API-avaimet
COINPAYMENTS_API_KEY = os.getenv('COINPAYMENTS_API_KEY')
COINPAYMENTS_API_SECRET = os.getenv('COINPAYMENTS_API_SECRET')


# ENCRYPTION_KEY pakotettu asetuksissa testausta varten (korvaa tämä avaimella tuotantokäyttöön)
ENCRYPTION_KEY = b'pkx0QTEggCmVkVwWoHXVzivoNw8AHd9KxLvYU1piCCQ='  # Avain bytes-muodossa

# Tarkistetaan, onko ENCRYPTION_KEY asetettu ja kelvollinen
if not ENCRYPTION_KEY:
    print("WARNING: 'ENCRYPTION_KEY' is not set in the environment variables.", file=sys.stderr)
else:
    print(f"ENCRYPTION_KEY (forced in settings.py file): {ENCRYPTION_KEY}", file=sys.stderr)  # Tulostetaan avain vahvistusta varten
    
    try:
        # Testataan, onko avain kelvollinen Fernetille
        Fernet(ENCRYPTION_KEY)
        print("ENCRYPTION_KEY loaded correctly and is valid.", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: Invalid encryption key: {e}", file=sys.stderr)
        ENCRYPTION_KEY = None  # Asetetaan None jos avain on virheellinen



# Kirjautumisen uudelleenohjaus-URL
LOGIN_REDIRECT_URL = '/dashboard/'

# CSRF-luotetut lähteet
if not DEBUG:
    CSRF_TRUSTED_ORIGINS = ['https://coinx-production.up.railway.app']

# Tuotannon turvallisuusasetukset
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Lokiasetukset
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
