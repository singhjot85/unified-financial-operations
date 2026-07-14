"""
Infra specific varibles will stay in this files
.base_models : All model related settings and registration, this avoids circular imports.
.variables : Settings that may vary at runtime
.resolvers : Keeps this file clean and perevent circular imports.
"""

from config.settings.base_models import *

# from config.logging_config import get_logging_config
from config.settings.constances import (  # noqa: F401
    CONSTANCE_ADDITIONAL_FIELDS,
    CONSTANCE_CONFIG,
    CONSTANCE_CONFIG_FIELDSETS,
    DJANGO_CONSOLE_BACKEND,
    DJANGO_FILE_BACKEND,
    DJANGO_SMTP_BACKEND,
)
from config.settings.setting_variables import *

PROJECT_NAME = "unified-financial-operations"
PROJECT_LABEL = "Unified Financial Operations"


# -----------------------------
#   Django Runtime Settings
# -----------------------------
STATICFILES_DIRS = [PROJECT_STATIC_PATH]
STATIC_ROOT = COLLECTED_STATIC_FILES
STATIC_URL = "static/"

ROOT_URLCONF = "config.routers"
PUBLIC_SCHEMA_URLCONF = "config.public_routers"

# TENANT_MODEL = TENANTS_ORGANIZATION_TENANT
# TENANT_DOMAIN_MODEL = TENANTS_ORGANIZATION_DOMAIN

INSTALLED_APPS = [
    *DEFAULT_DJANGO_APPS,
    *SHARED_EXTRA_DEPENDENCIES,
    *PUBLIC_ONLY_EXTRA_DEPENDENCIES,
    *PROJECT_APPS,
]

# -----------------------------
#   Database Configuration
# -----------------------------
SHARED_APPS = DJANGO_TENANT_PUBLIC_APPS
TENANT_APPS = DJANGO_TENANT_PRIVATE_APPS
TENANT_SYNC_ROUTER = "django_tenants.routers.TenantSyncRouter"

DATABASE_ROUTERS = [TENANT_SYNC_ROUTER]  # This is what figure's out what will go in INSTALLED_APPS, when running

DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": DATABASE_NAME,
        "USER": DATABASE_USER,
        "PASSWORD": DATABASE_PASSWORD,
        "HOST": DATABASE_HOST,
        "PORT": DATABASE_PORT,
    }
}

# -----------------------------
#   Cache Configuration
# -----------------------------
CACHE_URL = get_cache_url()
CACHE_BACKEND, RESOLVED_CACHE_OPTIONS = get_cache_ops()
CACHES = {
    "default": {
        "BACKEND": CACHE_BACKEND,
        "LOCATION": CACHE_URL,
        "OPTIONS": RESOLVED_CACHE_OPTIONS,
        "IGNORE_EXCEPTIONS": True,
        "TIMEOUT": 3600,
    },
}

# -----------------------------
#   Celery Configuration
# https://docs.celeryq.dev/en/latest/userguide/configuration.html#
# -----------------------------

CELERY_BROKER_URL = get_broker_url()
CELERY_RESULT_BACKEND = RESULT_BACKEND

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

CELERY_TIMEZONE = APPLICATION_TIMEZONE

CELERY_TASK_ALWAYS_EAGER = False  # Eager task run on same caller process
CELERY_TASK_TRACK_STARTED = True  # Save's `Started` as one of the task status.
CELERY_TASK_TIME_LIMIT = TASK_TIME_LIMIT
CELERY_TASK_SOFT_TIME_LIMIT = TASK_SOFT_TIME_LIMIT

# Writes extended results to backend (name, args, kwargs, worker, retries, queue, delivery_info).
CELERY_RESULT_EXTENDED = True
CELERY_DEFAULT_TASK_QUEUE = DEFAULT_TASK_QUEUE_NAME

# Need to define this explicilty fo celery
TENANT_DB_ALIAS = "default"

# CELERY_TASK_ROUTES = {
#     "task_name": {"queue": "queue_name"}
# }
# CELERY_BEAT_SCHEDULER = "config.beat.CustomDatabaseScheduler"


# -----------------------------
#   Django Templates
# -----------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [TEMPLATES_DIR],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# -----------------------------
#   Django Middleware
# -----------------------------
MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # "backend.config.middlewares.RequestLoggingMiddleware",
]


# -----------------------------
#   Django Password Validators
# -----------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# -----------------------------
#   dj-rest-auth
# -----------------------------
REST_AUTH = {"USER_DETAILS_SERIALIZER": "apps.tenants.serializers.UserSerializer"}


# ------------------
#  drf settings
# ------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

# ------------------
#  django-mail
# ------------------
DEFAULT_FROM_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_BACKEND = DJANGO_FILE_BACKEND  # overriden in constance, check there


# ------------------
#  django-constance
# ------------------
CONSTANCE_REDIS_CONNECTION = get_cache_url()

USE_TZ = True
TIME_ZONE = APPLICATION_TIMEZONE

USE_I18N = True
LANGUAGE_CODE = "en-us"

TASK_RESULT_CHECK_RETRIES = 10
TASK_RESULT_CHECK_TIMEOUT = 10  # Seconds

LOCAL_ENVS = ["local", "dev", "devlopment"]

if CURRENT_ENV in LOCAL_ENVS:
    DEBUG = True
    ALLOWED_HOSTS = []
    WSGI_APPLICATION = "config.wsgi.application"
else:
    # TODO: Write WSGI and  ALLOWED_HOSTS configuration for production
    DEBUG = False
    ALLOWED_HOSTS = []
    WSGI_APPLICATION = ""

# LOGGING = get_logging_config(debug=DEBUG, log_level=LOG_LEVEL)
