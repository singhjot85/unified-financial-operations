from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class CustomerTypeChoices(TextChoices):
    """Customer type choices for Customer model"""

    DONOR = "donor", _("Donor")
    BACKOFFICE = "bo", _("BackOffice")
    CLIENT = "client", _("Client")


class PartyTypeChoices(TextChoices):
    """Party type choices for Customer model"""

    INDIVIDUAL = "individual", _("Individual")
    ENTITY = "entity", _("Entity")


class EmailTypeChoices(TextChoices):
    """Email type choices for CustomerEmail model"""

    PRIMARY = "primary", _("Primary")
    SECONDARY = "secondary", _("Secondary")
    TERTIARY = "tertiary", _("Tertiary")


class PhoneTypeChoices(TextChoices):
    """Phone type choices for CustomerPhone model"""

    PRIMARY = "primary", _("Primary")
    SECONDARY = "secondary", _("Secondary")
    TERTIARY = "tertiary", _("Tertiary")


class PreferenceDataTypeChoices(TextChoices):
    """Preference Type Choices"""

    INTEGER = "integer", _("Integer")
    BOOLEAN = "boolean", _("Boolean")
    STRING = "string", _("String")
    CHOICES = "choices", _("Choices")
