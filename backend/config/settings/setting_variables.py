import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

APP_NAME = "apps"
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Path to /backend
APP_DIR = os.path.join(BASE_DIR, APP_NAME)  # Path to /backend/apps

# PROJECT_STATIC_PATH = os.path.join(BASE_DIR, "django_templates", "static")
# COLLECTED_STATIC_FILES = os.path.join(BASE_DIR, "django_templates", "staticfiles")

TEMPLATES_DIR = os.path.join(BASE_DIR, "django_templates", "templates")

SECRET_KEY = os.getenv("DJANGO_SECRETE_KEY", "")
APPLICATION_TIMEZONE = os.getenv("TIME_ZONE", "UTC")
DEFAULT_AUTO_FIELD = os.getenv("DJANGO_DEFAULT_ID", "django.db.models.BigAutoField")
CURRENT_ENV = os.getenv("DJANGO_ENV", "devlopment")


# -----------------------------
#   Database Settings
# -----------------------------
DATABASE_NAME = os.getenv("POSTGRES_DB")
DATABASE_USER = os.getenv("POSTGRES_USER")
DATABASE_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DATABASE_HOST = os.getenv("POSTGRES_HOST")
DATABASE_PORT = os.getenv("POSTGRES_PORT")


# -----------------------------
#   Razorpay Settings
# -----------------------------
RAZORPAY_API_KEY = os.getenv("RAZORPAY_API_KEY", "")
RAZORPAY_API_SECRETE = os.getenv("RAZORPAY_API_SECRETE", "")


# -----------------------------
#   Cache Settings
# -----------------------------
CACHE_PROTCOL = os.getenv("CACHE_PROTCOL", "redis")
CACHE_HOST = os.getenv("CACHE_HOST", "unfo_cache")
CACHE_PORT = os.getenv("CACHE_PORT", "6379")
CACHE_DATABASE = os.getenv("CACHE_DATABASE", 0)


def get_cache_url():
    if not any([CACHE_PROTCOL, CACHE_HOST, CACHE_PORT]):
        raise ImproperlyConfigured("Cache url is incorrect")

    return f"{CACHE_PROTCOL}://{CACHE_HOST}:{CACHE_PORT}/{CACHE_DATABASE}"


# django_redis paths
DJANGO_REDIS_IGNORE_EXCEPTIONS = True
REDIS_DEFAULT_OPTIONS = {
    "CLIENT_CLASS": "django_redis.client.DefaultClient",
}
REDIS_CLUSTER_DEFAULT_OPTIONS = {
    "CLIENT_CLASS": "django_redis.client.DefaultClient",
    "PICKLED_VERSION": 5,
}
REDIS_DEFAULT_BACKEND = "django_redis.cache.RedisCache"

# django_valkey paths
VALKEY_DEFAULT_OPTIONS = {
    "CLIENT_CLASS": "django_valkey.client.DefaultClient",
}
VALKEY_DEFAULT_BACKEND = "django_valkey.cluster_cache.cache.ClusterValkeyCache"

# Valkey clustering settings
VALKEY_CLUSTER_DEFAULT_OPTIONS = {
    "CLIENT_CLASS": "config.valkey_cluster_client.PatchedClusterClient",
    "CONNECTION_POOL_KWARGS": {
        "socket_connection_timeout": 5,
        "socket_timeout": 5,
    },
}
VALKEY_SOCKET_CONN_TIMEOUT = os.getenv("VALKEY_SOCKET_CONN_TIMEOUT")
VALKEY_SOCKER_TIMEOUT = os.getenv("VALKEY_SOCKER_TIMEOUT")


def get_cache_ops():
    CACHE_BACKEND = None
    RESOLVED_CACHE_OPTIONS = None

    if CACHE_PROTCOL == "valkey":
        CACHE_BACKEND = VALKEY_DEFAULT_BACKEND
        RESOLVED_CACHE_OPTIONS = VALKEY_DEFAULT_OPTIONS

    elif CACHE_PROTCOL == "redis":  # Redis cold-swap readiness
        CACHE_BACKEND = REDIS_DEFAULT_BACKEND
        RESOLVED_CACHE_OPTIONS = REDIS_DEFAULT_OPTIONS

    else:
        raise ImproperlyConfigured(f"Invalid Cache provider [{CACHE_PROTCOL}].")

    return CACHE_BACKEND, RESOLVED_CACHE_OPTIONS


# -----------------------------
#   Broker Settings
# -----------------------------
BROKER_PROTOCOL = os.getenv("BROKER_PROTOCOL", "redis")
BROKER_HOST = os.getenv("BROKER_HOST", "unfo_broker")
BROKER_PORT = os.getenv("BROKER_PORT", "6378")
BROKER_DATABASE = os.getenv("BROKER_DATABASE", 0)


def get_broker_url():
    if not any([BROKER_PROTOCOL, BROKER_HOST, BROKER_PORT]):
        raise ImproperlyConfigured("Celery Broker url is incorrect")

    return f"{BROKER_PROTOCOL}://{BROKER_HOST}:{BROKER_PORT}/{BROKER_DATABASE}"


# -----------------------------
#   Celery Settings
# -----------------------------
DEFAULT_TASK_QUEUE_NAME = os.getenv("CELERY_DEFAULT_TASK_QUEUE", "celery_default_queue")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "django-db")
TASK_TIME_LIMIT = os.getenv("CELERY_TASK_TIME_LIMIT", 9 * 60)
TASK_SOFT_TIME_LIMIT = os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", 8 * 60)


# -----------------------------
#   Django mail Settings
# -----------------------------
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = os.getenv("EMAIL_PORT", 587)
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", False)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

EMAIL_FILE_PATH = os.path.join(APP_DIR, "logs", "django-mails")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "dev@mailing.com")


# -----------------------------
#   Logging Config Settings
# -----------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
