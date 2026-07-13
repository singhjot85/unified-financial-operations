import typing

from django.db import models
from rest_framework import serializers
from rest_framework.exceptions import MethodNotAllowed


class ReadOnlyModelSerializer(serializers.ModelSerializer):
    """
    A truly read-only model serializer.

    Features:
    - All fields are automatically read-only
    - Create/Update operations are disabled with clear error messages
    - Works with any model

    Usage:

        >>> class UserSerializer(ReadOnlyModelSerializer):
        >>>     class Meta:
        >>>         model = User
        >>>         fields = ['id', 'username', 'email']  # Or "__all__"
    """

    def __init__(self, *args, **kwargs):
        """Initialize and make all fields read-only."""
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field: serializers.Field
            field.read_only = True

    def create(self, validated_data: dict) -> typing.Any:
        """Disable creation with clear error message."""
        raise MethodNotAllowed(method="POST", detail="Create operations are not permitted.")

    def update(self, instance: models.Model, validated_data: dict) -> typing.Any:
        """Disable updates with clear error message."""
        raise MethodNotAllowed(method="PUT/PATCH", detail="Update operations are not permitted.")


class DynamicReadOnlyModelSerializer(ReadOnlyModelSerializer):
    """
    Read-only serializer with ability to specify which fields are read-only.

    Features:
    - Read only fields are dynamically declare-able.
    - Create/Update operations are disabled with clear error messages
    - Works with any model

    Usage:

        >>> class UserSerializer(DynamicReadOnlyModelSerializer):
        >>>     class Meta:
        >>>         model = User
        >>>         fields = ['id', 'username', 'email', 'password']
        >>>         read_only_fields = ['password'] # Password stays read-only
    """

    @property
    def read_only_fields(self):
        meta = getattr(self, "Meta", None)
        read_only_fields = getattr(meta, "read_only_fields", [])
        return read_only_fields

    def __init__(self, *args, **kwargs):

        if self.read_only_fields:
            for field_name in self.read_only_fields:
                if field_name in self.fields:
                    self.fields[field_name].read_only = True
        else:
            super().__init__(*args, **kwargs)


class ConditionalReadOnlySerializer(DynamicReadOnlyModelSerializer):
    """
    Read-only serializer with ability to specify which fields are read-only.

    TODO: Implement this properly, make it permission based not raw ``user.is_staff``.

    Features:
    - Permission Based Readonly
    - Create/Update operations are disabled with clear error messages
    - Works with any model

    Usage:

        >>> class UserSerializer(DynamicReadOnlyModelSerializer):
        >>>     class Meta:
        >>>         model = User
        >>>         fields = ['id', 'username', 'email', 'password']
        >>>         read_only_fields = ['password'] # Password stays always read-only
        >>>         conditional_read_only = ["email"] # email only visible to admin.
    """

    @property
    def conditional_read_only_fields(self):
        meta = getattr(self, "Meta", None)
        read_only_fields = getattr(meta, "conditional_read_only", [])
        return read_only_fields

    def __init__(self, *args, **kwargs):
        request = self.context.get("request")
        _meta = getattr(self, "Meta", None)

        if request and request.user.is_staff:
            fields = getattr(_meta, "conditional_read_only", [])
            for field in fields:
                field.read_only = False
        else:
            original_readonly = self.read_only_fields
            original_readonly.extend(self.conditional_read_only_fields)
            setattr(_meta, "read_only_fields", original_readonly)

        super().__init__(*args, **kwargs)
