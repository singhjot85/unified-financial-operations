"""
This file list all the apps and models that are used in the project,
this keep the settings.py file clean, and helps lazy importing models.
"""

# ----------------------------
#   Model and App Naming
# Naming Convention:
#   APPS: APP_<app_name>,
#   MODELS: <app_name>_<model_name>
# ----------------------------
APP_CORE = "apps.core"

APP_CRM = "apps.crm"
CRM_CUSTOMER = "crm.Customer"
CRM_CUSTOMER_EMAIL = "crm.CustomerEmail"
CRM_CUSTOMER_PHONE = "crm.CustomerPhone"
CRM_CUSTOMER_ENTITY = "crm.CustomerEntity"
CRM_CUSTOMER_PREFERENCE_TYPE = "crm.CustomerPreferenceType"
CRM_CUSTOMER_PREFERENCE = "crm.CustomerPreference"

APP_TENANTS = "apps.tenants"
TENANTS_TENANT = "tenants.Tenants"
TENANTS_DOMAIN = "tenants.Domain"
TENANTS_CONTACT_INFO = "tenants.TenantContactInfo"
TENANTS_CONFIGURATION = "tenants.TenantConfiguration"
TENANTS_BRANDING = "tenants.TenantBranding"


# ----------------------------
#   Runtime App Classification
# ----------------------------
DEFAULT_DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

SHARED_EXTRA_DEPENDENCIES = [
    "rest_framework",
    # "django_tenants",
    # "rest_framework.authtoken",
    # "dj_rest_auth",
    "constance",
]

PUBLIC_ONLY_EXTRA_DEPENDENCIES = [
    "django_celery_results",
]

PROJECT_APPS = [
    APP_TENANTS,
    APP_CRM,
    # "apps.tenants",
    # "apps.setup",
    # "apps.customer_management",
    # "apps.payments_management",
    # "apps.notifications",
    APP_CORE,  # NOTE: Should always stay at last
]


# -----------------------------
#   Database App Classification
# -----------------------------
DJANGO_TENANT_PUBLIC_APPS = [
    *DEFAULT_DJANGO_APPS,
    *SHARED_EXTRA_DEPENDENCIES,
    *PUBLIC_ONLY_EXTRA_DEPENDENCIES,
    # "apps.tenants",
    # "apps.setup",
    APP_TENANTS,
    # APP_CORE,  # NOTE: Should always stay at last
]

DJANGO_TENANT_PRIVATE_APPS = [
    *DEFAULT_DJANGO_APPS,
    *SHARED_EXTRA_DEPENDENCIES,
    APP_CRM,
    # "apps.customer_management",
    # "apps.payments_management",
    # "apps.setup",
    # "apps.notifications",
]
