import factory
from django.contrib.auth import get_user_model

from apps.crm.constants import (
    CustomerTypeChoices,
    EmailTypeChoices,
    PartyTypeChoices,
    PhoneTypeChoices,
    PreferenceDataTypeChoices,
)
from apps.crm.models import (
    Customer,
    CustomerEmail,
    CustomerPhone,
    CustomerPreference,
    CustomerPreferenceType,
)

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user_{n}")
    is_active = True
    is_staff = False


class CustomerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Customer

    suffix = "Mr."
    first_name = factory.Faker("first_name")
    middle_name = ""
    last_name = factory.Faker("last_name")
    business_name = factory.Faker("company")
    party_type = PartyTypeChoices.INDIVIDUAL
    customer_type = CustomerTypeChoices.CLIENT
    dob = factory.Faker("date_of_birth", minimum_age=18, maximum_age=90)
    user = factory.SubFactory(UserFactory)


class CustomerEmailFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomerEmail

    is_primary = False
    email = factory.Sequence(lambda n: f"customer{n}@example.com")
    type = EmailTypeChoices.PRIMARY
    customer = factory.SubFactory(CustomerFactory)


class CustomerPhoneFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomerPhone

    is_primary = False
    phone = "1234567890"
    type = PhoneTypeChoices.PRIMARY
    customer = factory.SubFactory(CustomerFactory)


class CustomerPreferenceTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomerPreferenceType

    preference_name = factory.Sequence(lambda n: f"preference_{n}")
    data_type = PreferenceDataTypeChoices.STRING
    additional_meta_data = factory.LazyAttribute(
        lambda o: {
            "is_multi_type": False,
            "label": o.preference_name.replace("_", " ").title(),
            "default_value": "default",
        }
    )


class CustomerPreferenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomerPreference

    preference_type = factory.SubFactory(CustomerPreferenceTypeFactory)
    customer = factory.SubFactory(CustomerFactory)
    value = factory.LazyAttribute(lambda o: {"val": "my_preference_value"})
