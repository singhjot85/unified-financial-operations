from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class DefaultLogStatusChoices(TextChoices):
    """Status Choices to a log-bydefault"""

    CREATED = "created", _("Created")
    IN_PROGRESS = "in_progress", _("In Progress")
    SUCESS = "success", _("Sucess")
    ERROR = "error", _("Error")
