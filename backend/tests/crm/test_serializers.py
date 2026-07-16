import pytest
from rest_framework.exceptions import MethodNotAllowed

from apps.crm.constants import (
    CustomerTypeChoices,
    EmailTypeChoices,
    PartyTypeChoices,
    PhoneTypeChoices,
    PreferenceDataTypeChoices,
)
from apps.crm.serializers import (
    CustomerEmailSerializer,
    CustomerPhoneSerializer,
    CustomerPreferenceSerializer,
    CustomerPreferenceTypeSerializer,
    CustomerSerializer,
    UserSerializer,
)
from tests.factories import (
    CustomerEmailFactory,
    CustomerFactory,
    CustomerPhoneFactory,
    CustomerPreferenceFactory,
    CustomerPreferenceTypeFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestUserSerializer:
    """Tests for UserSerializer."""

    def test_user_serializer_fields(self):
        """Verify serialized fields on UserSerializer."""
        user = UserFactory(
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            username="alice",
            is_active=True,
            is_staff=False,
        )
        serializer = UserSerializer(instance=user)
        data = serializer.data
        assert data["first_name"] == "Alice"
        assert data["last_name"] == "Smith"
        assert data["email"] == "alice@example.com"
        assert data["username"] == "alice"
        assert data["is_active"] is True
        assert data["is_staff"] is False


@pytest.mark.django_db
class TestCustomerEmailSerializer:
    """Tests for CustomerEmailSerializer and its ListSerializer."""

    def test_bulk_create_emails(self):
        """Test bulk creation of CustomerEmail instances."""
        customer = CustomerFactory()
        data = [
            {"email": "one@example.com", "type": EmailTypeChoices.PRIMARY, "is_primary": True},
            {"email": "two@example.com", "type": EmailTypeChoices.SECONDARY, "is_primary": False},
        ]
        context = {"customer": customer}
        serializer = CustomerEmailSerializer(data=data, many=True, context=context)
        assert serializer.is_valid() is True
        emails = serializer.save()
        assert len(emails) == 2
        assert emails[0].customer == customer
        assert emails[0].email == "one@example.com"
        assert emails[0].is_primary is True
        assert emails[1].email == "two@example.com"
        assert emails[1].is_primary is False

    def test_email_list_serializer_update_not_allowed(self):
        """Verify update operation raises MethodNotAllowed on email ListSerializer."""
        email1 = CustomerEmailFactory()
        email2 = CustomerEmailFactory()
        list_serializer = CustomerEmailSerializer(instance=[email1, email2], data=[], many=True)
        with pytest.raises(MethodNotAllowed):
            list_serializer.update([email1, email2], [])


@pytest.mark.django_db
class TestCustomerPhoneSerializer:
    """Tests for CustomerPhoneSerializer and its ListSerializer."""

    def test_bulk_create_phones(self):
        """Test bulk creation of CustomerPhone instances."""
        customer = CustomerFactory()
        data = [
            {"phone": "1234567890", "type": PhoneTypeChoices.PRIMARY, "is_primary": True},
            {"phone": "9876543210", "type": PhoneTypeChoices.SECONDARY, "is_primary": False},
        ]
        context = {"customer": customer}
        serializer = CustomerPhoneSerializer(data=data, many=True, context=context)
        assert serializer.is_valid() is True
        phones = serializer.save()
        assert len(phones) == 2
        assert phones[0].customer == customer
        assert phones[0].phone == "1234567890"
        assert phones[0].is_primary is True
        assert phones[1].phone == "9876543210"
        assert phones[1].is_primary is False

    def test_phone_list_serializer_update_not_allowed(self):
        """Verify update operation raises MethodNotAllowed on phone ListSerializer."""
        phone1 = CustomerPhoneFactory()
        phone2 = CustomerPhoneFactory()
        list_serializer = CustomerPhoneSerializer(instance=[phone1, phone2], data=[], many=True)
        with pytest.raises(MethodNotAllowed):
            list_serializer.update([phone1, phone2], [])


@pytest.mark.django_db
class TestCustomerPreferenceSerializers:
    """Tests for CustomerPreferenceTypeSerializer and CustomerPreferenceSerializer."""

    def test_preference_type_serialization(self):
        """Verify CustomerPreferenceType fields serialization."""
        pref_type = CustomerPreferenceTypeFactory(
            preference_name="theme",
            data_type=PreferenceDataTypeChoices.STRING,
            additional_meta_data={"default_value": "dark"},
        )
        serializer = CustomerPreferenceTypeSerializer(instance=pref_type)
        data = serializer.data
        assert data["preference_name"] == "theme"
        assert data["data_type"] == PreferenceDataTypeChoices.STRING
        assert data["additional_meta_data"] == {"default_value": "dark"}

    def test_preference_serialization(self):
        """Verify CustomerPreference fields serialization."""
        pref = CustomerPreferenceFactory(value={"color": "red"})
        serializer = CustomerPreferenceSerializer(instance=pref)
        data = serializer.data
        assert data["value"] == {"color": "red"}
        assert "customer" in data
        assert "preference_type" in data


@pytest.mark.django_db
class TestCustomerSerializer:
    """Tests for CustomerSerializer."""

    def test_customer_serialization(self):
        """Test Customer serialization including nested emails, phones and preferences."""
        customer = CustomerFactory(
            first_name="Jane",
            last_name="Doe",
            customer_type=CustomerTypeChoices.CLIENT,
        )
        CustomerEmailFactory(customer=customer, email="jane@example.com")
        CustomerPhoneFactory(customer=customer, phone="5551234")
        CustomerPreferenceFactory(customer=customer, value={"notifications": "sms"})

        serializer = CustomerSerializer(instance=customer)
        data = serializer.data

        assert data["first_name"] == "Jane"
        assert data["last_name"] == "Doe"
        assert data["customer_type"] == CustomerTypeChoices.CLIENT

        # Check nested relationships
        assert len(data["emails"]) == 1
        assert data["emails"][0]["email"] == "jane@example.com"
        assert len(data["phones"]) == 1
        assert data["phones"][0]["phone"] == "5551234"
        assert len(data["preferences"]) == 1
        assert data["preferences"][0]["value"] == {"notifications": "sms"}

    def test_customer_validation_invalid_emails(self):
        """Verify ValidationError when 'emails' input is not a list."""
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "emails": "not-a-list",
        }
        serializer = CustomerSerializer(data=data)
        assert serializer.is_valid() is False
        assert "emails" in serializer.errors

    def test_customer_validation_invalid_phones(self):
        """Verify ValidationError when 'phones' input is not a list."""
        data = {
            "first_name": "Jane",
            "last_name": "Doe",
            "phones": "not-a-list",
        }
        serializer = CustomerSerializer(data=data)
        assert serializer.is_valid() is False
        assert "phones" in serializer.errors

    def test_customer_creation_with_nested_relations(self):
        """Test customer creation along with nested emails and phones."""
        data = {
            "first_name": "Bob",
            "last_name": "Vance",
            "party_type": PartyTypeChoices.INDIVIDUAL,
            "customer_type": CustomerTypeChoices.CLIENT,
            "emails": [{"email": "bob@vance.com", "type": EmailTypeChoices.PRIMARY, "is_primary": True}],
            "phones": [{"phone": "1112223333", "type": PhoneTypeChoices.PRIMARY, "is_primary": True}],
        }
        serializer = CustomerSerializer(data=data)
        assert serializer.is_valid() is True
        customer = serializer.save()

        assert customer.first_name == "Bob"
        assert customer.last_name == "Vance"
        assert customer.emails.count() == 1
        assert customer.emails.first().email == "bob@vance.com"
        assert customer.phones.count() == 1
        assert customer.phones.first().phone == "1112223333"

    def test_customer_update_pops_restricted_fields(self):
        """Verify updating a customer ignores nested emails/phones/user updates."""
        customer = CustomerFactory(first_name="InitialName")
        CustomerEmailFactory(customer=customer, email="old@example.com")

        new_user = UserFactory()
        data = {
            "first_name": "UpdatedName",
            "user": new_user.id,
            "emails": [{"email": "new@example.com"}],
        }
        serializer = CustomerSerializer(instance=customer, data=data, partial=True)
        assert serializer.is_valid() is True
        updated_customer = serializer.save()

        assert updated_customer.first_name == "UpdatedName"
        # User and emails should NOT be updated or changed
        assert updated_customer.user != new_user
        assert updated_customer.emails.count() == 1
        assert updated_customer.emails.first().email == "old@example.com"
