import typing

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import MethodNotAllowed

from apps.core.serializers import ReadOnlyModelSerializer
from apps.crm.models import (
    Customer,
    CustomerEmail,
    CustomerPhone,
    CustomerPreference,
    CustomerPreferenceType,
)

User = get_user_model()


class UserSerializer(ReadOnlyModelSerializer):
    """
    TODO: Move to dedicated auth app once built.
    """

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "username", "is_active", "is_staff")


class CustomerEmailListSerializer(serializers.ListSerializer):

    def validate(self, attrs):
        if not isinstance(attrs, list):
            raise serializers.ValidationError(f"Emails must be of type list not {type(attrs)}")

        return super().validate(attrs)

    def create(self, validated_data) -> typing.Optional[list]:
        """Bulk Create CustomerEmail's"""
        customer = self.context.get("customer", None)
        if not customer:
            return None

        email_objs = []
        for email in validated_data:
            email_objs.append(CustomerEmail(customer=customer, **email))

        if email_objs:
            CustomerEmail.objects.bulk_create(email_objs)

        return email_objs

    def update(self, instance, validated_data):
        raise MethodNotAllowed(method="PUT/PATCH", detail="Update operations are not permitted as of now.")


class CustomerEmailSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomerEmail
        fields = "__all__"

        list_serializer_class = CustomerEmailListSerializer


class CustomerPhoneListSerializer(serializers.ListSerializer):

    def validate(self, attrs):
        if not isinstance(attrs, list):
            raise serializers.ValidationError(f"Phones must be of type list not {type(attrs)}")

        return super().validate(attrs)

    def create(self, validated_data) -> typing.Optional[list]:
        """Bulk Create CustomerEmail's"""
        customer = self.context.get("customer", None)
        if not customer:
            return None

        phone_objs = []
        for email in validated_data:
            phone_objs.append(CustomerPhone(customer=customer, **email))

        if phone_objs:
            CustomerPhone.objects.bulk_create(phone_objs)

        return phone_objs

    def update(self, instance, validated_data):
        raise MethodNotAllowed(method="PUT/PATCH", detail="Update operations are not permitted as of now.")


class CustomerPhoneSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomerPhone
        fields = "__all__"

        list_serializer_class = CustomerPhoneListSerializer


class CustomerPreferenceTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomerPreferenceType


class CustomerPreferenceSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomerPreference


class CustomerSerializer(serializers.ModelSerializer):

    user = UserSerializer(read_only=True)
    emails = CustomerEmailSerializer(source="books", many=True)
    phones = CustomerPhoneSerializer(source="phones", many=True)
    preferences = CustomerPreferenceSerializer(source="preferences")

    class Meta:
        model = Customer
        fields = (
            "suffix",
            "first_name",
            "middle_name",
            "last_name",
            "business_name",
            "party_type",
            "customer_type",
            "dob",
            "user",
            "emails",
            "phones",
            "preferences",
        )

    def validate_emails(self, value):
        """
        Args:
            value: The raw input data for 'emails' passed into the serializer.

        Raises:
            serializers.ValidationError: If the value fails validation.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError({"emails": f"Emails must be of type list not {type(value)}"})

    def validate_phones(self, value):
        """
        Args:
            value: The raw input data for 'emails' passed into the serializer.

        Raises:
            serializers.ValidationError: If the value fails validation.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError({"phones": f"Phones must be of type list not {type(value)}"})

    def create(self, validated_data):
        """
        Create a Customer Object from given data, bulk create emails, phones
        But we are not allowing user creation through this serializer.
        User creation for a customer, is purely business decision, so doesn't beliong here
        """
        validated_data.pop("users", [])
        emails = validated_data.pop("emails", [])
        phones = validated_data.pop("phones", [])

        customer = super().create(validated_data)

        bulk_context = {"customer": customer, **self.context}

        email_ser = CustomerEmailSerializer(data=emails, many=True, context=bulk_context)
        if email_ser.is_valid(raise_exception=True):
            email_ser.save()

        phone_ser = CustomerEmailSerializer(data=phones, many=True, context=bulk_context)
        if phone_ser.is_valid(raise_exception=True):
            phone_ser.save()

        return customer

    def update(self, instance, validated_data):
        """
        We are not allowing fk update as of now on this ser. only create is allowed
        TODO: This will be intruduced soon, as-part of a smart WriteSerailzerMixin
        """
        validated_data.pop("users", [])
        validated_data.pop("emails", [])
        validated_data.pop("phones", [])

        return super().update(instance, validated_data)
