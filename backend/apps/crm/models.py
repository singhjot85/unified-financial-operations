from __future__ import annotations

from django.contrib.contenttypes import fields
from django.contrib.contenttypes import models as cttype_models
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AbstractParty, BaseModel
from apps.crm.abstacts import AbstractPreferenceTypeValidator
from apps.crm.app_settings import app_settings
from apps.crm.constants import (
    EmailTypeChoices,
    PhoneTypeChoices,
    PreferenceDataTypeChoices,
)

PreferenceTypeValidatorOverride: type[AbstractPreferenceTypeValidator] = app_settings.PREFERNCE_TYPE_VALIDATOR


class Customer(BaseModel, AbstractParty):

    party_type = models.CharField(null=True, blank=True, choices=app_settings.PARTY_TYPE_CHOICES.choices)
    customer_type = models.CharField(null=True, blank=True, choices=app_settings.CUSTOMER_TYPE_CHOICES.choices)
    customer = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="related_customer"
    )
    dob = models.DateField(null=True, blank=True)
    user = models.ForeignKey(to=app_settings.AUTH_USER, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"


class CustomerEmail(BaseModel):

    is_primary = models.BooleanField(null=True, blank=True, default=False)
    email = models.CharField(_("Email ID"), null=False, blank=False)
    type = models.CharField(null=False, blank=False, choices=EmailTypeChoices.choices)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=False, blank=False, related_name="emails")

    class Meta:
        verbose_name = "Customer Email"
        verbose_name_plural = "Customer Emails"


class CustomerPhone(BaseModel):

    is_primary = models.BooleanField(null=True, blank=True, default=False)
    phone = models.CharField(_("Phone Number"), null=False, blank=False)
    type = models.CharField(null=False, blank=False, choices=PhoneTypeChoices.choices)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=False, blank=False, related_name="phones")

    class Meta:
        verbose_name = "Customer Phone"
        verbose_name_plural = "Customer Phones"


class CustomerEntity(BaseModel):

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=False, blank=False)
    entity = fields.GenericForeignKey("entity_content_type", "entity_object_id")
    entity_content_type = models.ForeignKey(
        cttype_models.ContentType, on_delete=models.CASCADE, null=False, blank=False
    )
    entity_object_id = models.CharField(null=True, blank=True, max_length=255)

    class Meta:
        verbose_name = "Customer Entity"
        verbose_name_plural = "Customer Entities"


class CustomerPreferenceType(BaseModel, PreferenceTypeValidatorOverride):

    key_multi_type: str = "is_multi_type"
    key_label: str = "label"
    key_default: str = "default_value"

    preference_name = models.CharField(null=False, blank=False)
    data_type = models.CharField(
        max_length=124, null=False, blank=False, choices=app_settings.PREFERENCE_DATA_TYPE_CHOICES.choices
    )
    additional_meta_data = models.JSONField(
        _("Additional Preferances Metadata (defaults, labels, is_multi_select)"),
        default=dict,
        encoder=DjangoJSONEncoder,
        blank=True,
    )

    def clean_fields(self, exclude=...):
        """
        Validate individual fields, validating and cleaning ``additional_meta_data``
        Doesn't define the implementation directly, uses a helper method ``validate_metadata``
        Override that instead of clean_fields directly for any custom logic.
        """

        if hasattr(self, "validate_metadata"):
            self.additional_meta_data = getattr(self, "validate_metadata")()

        return super().clean_fields(exclude)

    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)


class CustomerPreference(BaseModel):

    preference_type = models.ForeignKey(CustomerPreferenceType, on_delete=models.PROTECT, null=False, blank=False)
    customer = models.ForeignKey(
        Customer, null=False, blank=False, on_delete=models.PROTECT, related_name="preferences"
    )
    value = models.JSONField(_("Preferances Value"), default=dict, encoder=DjangoJSONEncoder, blank=True)

    def __str__(self):
        return f"{self.preference_type} - {self.customer}"

    def validate_preference_value(self):
        """Common Validations Related to value field, Extend for more complex logics."""
        if not self.value or not self.preference_type:
            return

        if self.preference_type.data_type == PreferenceDataTypeChoices.CHOICES and not isinstance(self.value, list):
            raise ValueError(f"Choices must have value of type ``list`` instead of {type(self.value)}")

        if self.preference_type.data_type != PreferenceDataTypeChoices.CHOICES and isinstance(self.value, list):
            raise ValueError("Non-Choices should not have value of type ``list``")

    def save(self, *args, **kwargs):
        if self.value:
            self.validate_preference_value()

        return super().save(*args, **kwargs)
