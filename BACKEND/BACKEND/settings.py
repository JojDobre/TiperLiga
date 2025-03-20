from pathlib import Path
from celery.schedules import crontab

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-7a@-n(nuewk2l3id((bb1xsw++2!g44gg22^7ej1-cxwbs$h@m'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Celery konfigurácia
CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Periodické úlohy
CELERY_BEAT_SCHEDULE = {
    'process-achievements': {
        'task': 'tipperliga.tasks.process_achievements',
        'schedule': crontab(hour=1, minute=0),  # denne o 1:00
    },
    'process-league-scoring': {
        'task': 'tipperliga.tasks.process_league_scoring',
        'schedule': crontab(minute=0, hour='*/1'),  # každú hodinu
    },
    'generate-leaderboards': {
        'task': 'tipperliga.tasks.generate_league_leaderboards',
        'schedule': crontab(minute=30, hour='*/4'),  # štyrikrát denne
    },

    'generate-league-reports': {
        'task': 'tipperliga.tasks.generate_periodic_league_reports',
        'schedule': crontab(day_of_month=1, hour=0, minute=0),  # prvý deň v mesiaci
    },
    'update-betting-trends': {
        'task': 'tipperliga.tasks.update_user_betting_trends',
        'schedule': crontab(hour=0, minute=0),  # denne o polnoci
    },
    'update-league-performances': {
        'task': 'tipperliga.tasks.update_league_performances',
        'schedule': crontab(hour=1, minute=0),  # denne o 1:00
    },
        'update-competition-statuses': {
        'task': 'tipperliga.tasks.update_competition_statuses',
        'schedule': crontab(hour=0, minute=0),  # denne o polnoci
    },
        'update-team-statistics': {
        'task': 'tipperliga.tasks.update_team_statistics',
        'schedule': crontab(hour='*/1'),  # každú hodinu
    },
    'update-user-betting-history': {
        'task': 'tipperliga.tasks.update_user_betting_history',
        'schedule': crontab(hour='*/1'),  # každú hodinu
    },
    'update-daily-betting-trends': {
        'task': 'tipperliga.tasks.update_daily_betting_trends',
        'schedule': crontab(hour=0, minute=0),  # denne o polnoci
    }
}


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tipperliga',
    'rest_framework',
    'rest_framework_simplejwt',
    'django_crontab',
    'notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'tipperliga.middleware.UserActivityMiddleware',
]

ROOT_URLCONF = 'BACKEND.urls'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# Konfigurácia JWT
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Nastavenie custom user modelu
AUTH_USER_MODEL = 'tipperliga.CustomUser'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'BACKEND.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

import os
from dotenv import load_dotenv
load_dotenv()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'





# Notifikačné nastavenia
NOTIFICATIONS_SOFT_DELETE = True

# Email konfigurácia
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your_email@gmail.com'
EMAIL_HOST_PASSWORD = 'your_app_password'
DEFAULT_FROM_EMAIL = 'your_email@gmail.com'

# Logging konfigurácia
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'user_actions': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'system_errors': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
        },
    },
}