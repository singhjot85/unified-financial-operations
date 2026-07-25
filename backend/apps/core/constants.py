from enum import Enum

from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class DefaultLogStatusChoices(TextChoices):
    """Status Choices to a log-bydefault"""

    CREATED = "created", _("Created")
    IN_PROGRESS = "in_progress", _("In Progress")
    SUCESS = "succeded", _("Succeded")
    FAILED = "failed", _("Failed")


class SeederMethod(Enum):
    """Seeder Method to implement"""

    GET_OR_CREATE = "get_or_create"
    UPDATE_OR_CREATE = "update_or_create"


class SeederModes(Enum):
    """
    Mode in which to run the seeder
    - Single: Run an individual seeder.
    - All: Run all existing seeders
    - Model: Run seeder's only with FixtureMixin
    """

    FIXTURE = "fixture"
    SEEDER = "seeder"
    SINGLE = "single"


SENSITIVE_CONTENT_PHRASES = [
    "password",
    "pass",
    "id",
    "pk",
    "token",
    "secret",
    "key",
    "api_key",
    "auth",
    "credential",
    "authorization",
    "access_token",
    "refresh_token",
    "client_secret",
    "private_key",
    "pwd",
    "otp",
    "pin",
    "security_answer",
    "ssn",
    "social_security",
    "credit_card",
    "cvv",
    "cvc",
    "pan",
    "aadhar",
    "adhaar",
    "bank_account",
    "routing_number",
    "passphrase",
    "master_password",
    "user_password",
    "confirm_password",
    "old_password",
    "new_password",
]
