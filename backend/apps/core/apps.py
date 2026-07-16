from django.apps import AppConfig

_SENSITIVE_MATCHER = None


class CrmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"

    def ready(self):
        from apps.core.utils import get_sensitive_matcher

        get_sensitive_matcher()
