import pytest
from django.contrib.contenttypes.models import ContentType

from apps.crm.constants import (
    CustomerTypeChoices,
    EmailTypeChoices,
    PartyTypeChoices,
    PhoneTypeChoices,
    PreferenceDataTypeChoices,
)
from apps.crm.models import CustomerEntity, CustomerPreference, CustomerPreferenceType
from tests.factories import (
    CustomerEmailFactory,
    CustomerFactory,
    CustomerPhoneFactory,
    CustomerPreferenceFactory,
    CustomerPreferenceTypeFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestCustomerModels:
    """Tests for the CRM models."""

    def test_create_customer(self):
        """Happy path for creating a Customer."""
        user = UserFactory()
        customer = CustomerFactory(
            suffix="Dr.",
            first_name="John",
            middle_name="M.",
            last_name="Doe",
            business_name="Doe Enterprises",
            party_type=PartyTypeChoices.INDIVIDUAL,
            customer_type=CustomerTypeChoices.DONOR,
            user=user,
        )
        assert customer.suffix == "Dr."
        assert customer.first_name == "John"
        assert customer.middle_name == "M."
        assert customer.last_name == "Doe"
        assert customer.business_name == "Doe Enterprises"
        assert customer.party_type == PartyTypeChoices.INDIVIDUAL
        assert customer.customer_type == CustomerTypeChoices.DONOR
        assert customer.user == user

    def test_customer_self_relation(self):
        """Test Customer foreign key relation to self."""
        parent_customer = CustomerFactory()
        child_customer = CustomerFactory(customer=parent_customer)
        assert child_customer.customer == parent_customer
        assert parent_customer.related_customer.first() == child_customer

    def test_customer_email(self):
        """Test CustomerEmail creation and relation."""
        customer = CustomerFactory()
        email = CustomerEmailFactory(
            customer=customer,
            email="test@example.com",
            type=EmailTypeChoices.PRIMARY,
            is_primary=True,
        )
        assert email.customer == customer
        assert email.email == "test@example.com"
        assert email.type == EmailTypeChoices.PRIMARY
        assert email.is_primary is True
        assert customer.emails.first() == email

    def test_customer_phone(self):
        """Test CustomerPhone creation and relation."""
        customer = CustomerFactory()
        phone = CustomerPhoneFactory(
            customer=customer,
            phone="1234567890",
            type=PhoneTypeChoices.SECONDARY,
            is_primary=False,
        )
        assert phone.customer == customer
        assert phone.phone == "1234567890"
        assert phone.type == PhoneTypeChoices.SECONDARY
        assert phone.is_primary is False
        assert customer.phones.first() == phone

    def test_customer_entity_generic_fk(self):
        """Test CustomerEntity GenericForeignKey behavior."""
        customer = CustomerFactory()
        user = UserFactory()
        user_content_type = ContentType.objects.get_for_model(user)

        customer_entity = CustomerEntity.objects.create(
            customer=customer,
            entity_content_type=user_content_type,
            entity_object_id=str(user.id),
        )
        assert customer_entity.customer == customer
        assert customer_entity.entity == user


@pytest.mark.django_db
class TestCustomerPreferenceModels:
    """Tests for CustomerPreferenceType and CustomerPreference models."""

    def test_preference_type_metadata_cleaning(self):
        """Test metadata cleaning and validation on CustomerPreferenceType."""
        pref_type = CustomerPreferenceTypeFactory(
            preference_name="Test Preference",
            data_type=PreferenceDataTypeChoices.BOOLEAN,
            additional_meta_data={
                "is_multi_type": True,
                "label": "Test Label",
                "default_value": True,
            },
        )
        pref_type.full_clean()
        metadata = pref_type.additional_meta_data
        assert metadata["is_multi_type"] is True
        assert metadata["label"] == "Test Label"
        assert metadata["default_value"] is True

    def test_preference_type_metadata_fallback_default(self):
        """Test fallback default values for different data types."""
        pref_type_bool = CustomerPreferenceType.objects.create(
            preference_name="bool_pref",
            data_type=PreferenceDataTypeChoices.BOOLEAN,
            additional_meta_data={},
        )
        pref_type_bool.full_clean()
        assert pref_type_bool.additional_meta_data["default_value"] is False

        pref_type_int = CustomerPreferenceType.objects.create(
            preference_name="int_pref",
            data_type=PreferenceDataTypeChoices.INTEGER,
            additional_meta_data={},
        )
        pref_type_int.full_clean()
        assert pref_type_int.additional_meta_data["default_value"] == 0

        pref_type_string = CustomerPreferenceType.objects.create(
            preference_name="string_pref",
            data_type=PreferenceDataTypeChoices.STRING,
            additional_meta_data={},
        )
        pref_type_string.full_clean()
        assert pref_type_string.additional_meta_data["default_value"] == ""

    def test_preference_type_choices_appended_to_metadata(self):
        """Test that choices are cleaned and appended for CHOICES data type."""
        pref_type = CustomerPreferenceType.objects.create(
            preference_name="choices_pref",
            data_type=PreferenceDataTypeChoices.CHOICES,
            additional_meta_data={"choices": ["A", "B"]},
        )
        pref_type.full_clean()
        assert pref_type.additional_meta_data["choices"] == ["A", "B"]

    def test_validate_preference_value_choices_valid(self):
        """Happy path: CHOICES type with a list value."""
        pref_type = CustomerPreferenceTypeFactory(data_type=PreferenceDataTypeChoices.CHOICES)
        pref = CustomerPreferenceFactory(
            preference_type=pref_type,
            value=["option1", "option2"],
        )
        pref.full_clean()  # should not raise

    def test_validate_preference_value_choices_invalid(self):
        """Error path: CHOICES type with a non-list value."""
        pref_type = CustomerPreferenceTypeFactory(data_type=PreferenceDataTypeChoices.CHOICES)
        pref = CustomerPreference(
            preference_type=pref_type,
            customer=CustomerFactory(),
            value="not-a-list",
        )
        with pytest.raises(ValueError, match="Choices must have value of type"):
            pref.save()

    def test_validate_preference_value_non_choices_invalid(self):
        """Error path: Non-CHOICES type with a list value."""
        pref_type = CustomerPreferenceTypeFactory(data_type=PreferenceDataTypeChoices.STRING)
        pref = CustomerPreference(
            preference_type=pref_type,
            customer=CustomerFactory(),
            value=["should-not-be-a-list"],
        )
        with pytest.raises(ValueError, match="Non-Choices should not have value of type"):
            pref.save()
