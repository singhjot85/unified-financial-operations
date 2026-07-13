from core.app_settings.base import BaseSettings
from core.app_settings.types import Constance, LazyImport


class CRMSettings(BaseSettings):

    class Meta:
        app = "crm"

    PARTY_TYPE_CHOICES = LazyImport(
        default="apps.crm.constants.PartyTypeChoices", help_text="Party type choices for Customer Party Type"
    )

    CUSTOMER_TYPE_CHOICES = LazyImport(default="apps.crm.constants.CustomerTypeChoices", help_text="")

    PREFERENCE_DATA_TYPE_CHOICES = LazyImport(default="apps.crm.constants.PreferenceDataTypeChoices", help_text="")

    PREFERNCE_TYPE_VALIDATOR = LazyImport(default="apps.crm.models.PreferenceTypeValidator", help_text="")

    AUTH_USER = LazyImport(default="django.contrib.auth.models.User", help_text="Auth User Model")

    ENABLE_SOME_CUSTOMER_RELATED_FLAG = Constance(
        default=True, type=bool, help_text="Party type choices for Customer Party Type"
    )


app_settings = CRMSettings()
