from enum import Enum

from django.core.exceptions import ImproperlyConfigured


# =================
#   Field Classes
# =================
class YesNoChoices(Enum):
    BLANK = (None, "-----")
    YES = (True, "Yes")
    NO = (False, "No")

    @staticmethod
    def default_value():
        return YesNoChoices.YES.value[0]  # Fixed: access the first element of the tuple

    @staticmethod
    def get_field_kwargs():
        """Return Kwargs required to register a field"""
        return "django.forms.fields.ChoiceField", {
            "widget": "django.forms.Select",
            "widget_kwargs": None,
            "choices": [(item.value[0], item.value[1]) for item in YesNoChoices],
        }


DJANGO_SMTP_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
DJANGO_FILE_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
DJANGO_CONSOLE_BACKEND = "django.core.mail.backends.console.EmailBackend"


class EmailBackendChoices(Enum):
    """Email Backend Choices"""

    BLANK = (None, "-----")
    SMTP_BACKEND = (DJANGO_SMTP_BACKEND, "SMTP (!! This Sends Real Mail !!)")
    FILE_BACKEND = (DJANGO_FILE_BACKEND, "File Based")
    CONSOLE_BASED = (DJANGO_CONSOLE_BACKEND, "Console Backend")

    @staticmethod
    def default_value():
        return EmailBackendChoices.CONSOLE_BASED.value[0]

    @staticmethod
    def get_field_kwargs():
        """Return Kwargs required to register a field"""
        return "django.forms.fields.ChoiceField", {
            "widget": "django.forms.Select",
            "widget_kwargs": None,
            "choices": [(item.value[0], item.value[1]) for item in EmailBackendChoices],
        }


# ===============================
#   Registration of those classes
# ===============================


class ConstanceFields(Enum):
    """
    Constance Custom Field Configurations, value should be:
    (FieldName, FieldDescription, ImplementationClass)
    """

    EMAIL_BE_CHOICES = ("EMAIL_BACKEND_CHOICES", "Which Email Backend to use", EmailBackendChoices)
    MOCK_EMAIL_SERV = ("USE_MOCK_EMAIL_SERVICE", "Should Use Mock Email Service or Real Emails", YesNoChoices)

    @property
    def field_name(self):
        return self.value[0]

    @property
    def description(self):
        return self.value[1]

    @property
    def implementation_class(self):
        return self.value[2]

    @property
    def default(self):
        if hasattr(self.value[2], "default_value"):
            return self.value[2].default_value()
        return None

    @staticmethod
    def additional_field_registration():
        result = {}
        for member in ConstanceFields:
            field_name, _, impl_class = member.value
            if not field_name or not impl_class or not hasattr(impl_class, "get_field_kwargs"):
                raise ImproperlyConfigured(f"Malformed Constance Fields for {member.name}")

            result[field_name] = impl_class.get_field_kwargs()
        return result


# ===============================
#   Constance Settings
# ===============================

CONSTANCE_ADDITIONAL_FIELDS = ConstanceFields.additional_field_registration()

# Fixed: CONSTANCE_CONFIG format
CONSTANCE_CONFIG = {
    ConstanceFields.EMAIL_BE_CHOICES.field_name: (
        ConstanceFields.EMAIL_BE_CHOICES.default,
        ConstanceFields.EMAIL_BE_CHOICES.description,
        ConstanceFields.EMAIL_BE_CHOICES.field_name,
    ),
    ConstanceFields.MOCK_EMAIL_SERV.field_name: (
        ConstanceFields.MOCK_EMAIL_SERV.default,
        ConstanceFields.MOCK_EMAIL_SERV.description,
        ConstanceFields.MOCK_EMAIL_SERV.field_name,
    ),
}

# Fixed: CONSTANCE_CONFIG_FIELDSETS format
CONSTANCE_CONFIG_FIELDSETS = {
    "Email Configuration": {
        "fields": (
            ConstanceFields.EMAIL_BE_CHOICES.field_name,
            ConstanceFields.MOCK_EMAIL_SERV.field_name,
        ),
        "collapse": False,
    },
}
