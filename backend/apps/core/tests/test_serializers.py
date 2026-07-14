import pytest
from django.db import models
from rest_framework.exceptions import MethodNotAllowed

from apps.core.serializers import (
    ConditionalReadOnlySerializer,
    DynamicReadOnlyModelSerializer,
    ReadOnlyModelSerializer,
)


class TestModel(models.Model):
    name = models.CharField(null=True, blank=True, default="Some Name")
    integer = models.IntegerField(null=True, blank=True, default=101)
    boolean = models.BooleanField(default=True, null=True, blank=True)

    class Meta:
        app_label = "core"


class TestReadOnlySerializer(ReadOnlyModelSerializer):
    class Meta:
        model = TestModel
        fields = ["name", "integer", "boolean"]


class TestDynamicReadOnlySerializer(DynamicReadOnlyModelSerializer):
    class Meta:
        model = TestModel
        fields = ["name", "integer", "boolean"]
        read_only_fields = ["integer"]


class TestDynamicReadOnlyAllSerializer(DynamicReadOnlyModelSerializer):
    class Meta:
        model = TestModel
        fields = ["name", "integer", "boolean"]


class TestConditionalReadOnlySerializer(ConditionalReadOnlySerializer):
    class Meta:
        model = TestModel
        fields = ["name", "integer", "boolean"]
        read_only_fields = ["integer"]
        conditional_read_only = ["name"]


class MockUser:
    def __init__(self, is_staff=False):
        self.is_staff = is_staff


class MockRequest:
    def __init__(self, user=None):
        self.user = user


@pytest.mark.django_db
class TestReadOnlyModelSerializer:

    def test_readonly_marks_all_fields_readonly(self):
        data = {"name": "Some other name", "integer": 202, "boolean": False}
        ser = TestReadOnlySerializer(data=data)
        ser.is_valid(raise_exception=True)

        for field_name, field in ser.fields.items():
            assert field.read_only is True, f"{field_name} is not marked readonly."

    def test_readonly_prevents_create(self):
        data = {"name": "Some other name", "integer": 202, "boolean": False}

        ser = TestReadOnlySerializer(data=data)
        ser.is_valid(raise_exception=True)

        with pytest.raises(MethodNotAllowed):
            ser.save()

    def test_readonly_prevents_update(self):
        instance = TestModel.objects.create(name="Original Name", integer=101, boolean=True)

        data = {"name": "Some other name", "integer": 202, "boolean": False}

        ser = TestReadOnlySerializer(instance=instance, data=data)
        ser.is_valid(raise_exception=True)

        with pytest.raises(MethodNotAllowed):
            ser.save()

    def test_readonly_serializer_returns_data_correctly(self):
        instance = TestModel.objects.create(name="Test Name", integer=303, boolean=False)

        ser = TestReadOnlySerializer(instance=instance)

        assert ser.data["name"] == "Test Name"
        assert ser.data["integer"] == 303
        assert ser.data["boolean"] is False


@pytest.mark.django_db
class TestDynamicReadOnlyModelSerializer:

    def test_dynamic_readonly_marks_specified_fields_readonly(self):
        data = {"name": "Some other name", "integer": 202, "boolean": False}
        ser = TestDynamicReadOnlySerializer(data=data)
        ser.is_valid(raise_exception=True)

        assert ser.fields["integer"].read_only is True
        assert ser.fields["name"].read_only is False
        assert ser.fields["boolean"].read_only is False

    def test_dynamic_readonly_falls_back_to_all_readonly_if_no_fields_specified(self):
        data = {"name": "Some other name", "integer": 202, "boolean": False}
        ser = TestDynamicReadOnlyAllSerializer(data=data)
        ser.is_valid(raise_exception=True)

        for field_name, field in ser.fields.items():
            assert field.read_only is True, f"{field_name} is not marked readonly."

    def test_dynamic_readonly_prevents_create(self):
        data = {"name": "Some other name", "integer": 202, "boolean": False}
        ser = TestDynamicReadOnlySerializer(data=data)
        ser.is_valid(raise_exception=True)

        with pytest.raises(MethodNotAllowed):
            ser.save()

    def test_dynamic_readonly_prevents_update(self):
        instance = TestModel.objects.create(name="Original Name", integer=101, boolean=True)
        data = {"name": "Some other name", "integer": 202, "boolean": False}
        ser = TestDynamicReadOnlySerializer(instance=instance, data=data)
        ser.is_valid(raise_exception=True)

        with pytest.raises(MethodNotAllowed):
            ser.save()


@pytest.mark.django_db
class TestConditionalReadOnlySerializerClass:

    def test_conditional_readonly_non_staff_makes_conditional_fields_readonly(self):
        request = MockRequest(user=MockUser(is_staff=False))
        data = {"name": "Some other name", "integer": 202, "boolean": False}
        ser = TestConditionalReadOnlySerializer(data=data, context={"request": request})
        ser.is_valid(raise_exception=True)

        # "integer" is in read_only_fields, so always read-only
        assert ser.fields["integer"].read_only is True
        # "name" is in conditional_read_only, should be read-only for non-staff
        assert ser.fields["name"].read_only is True
        # "boolean" is not read-only or conditional read-only, so should be editable
        assert ser.fields["boolean"].read_only is False

    def test_conditional_readonly_staff_makes_conditional_fields_editable(self):
        request = MockRequest(user=MockUser(is_staff=True))
        data = {"name": "Some other name", "integer": 202, "boolean": False}
        ser = TestConditionalReadOnlySerializer(data=data, context={"request": request})
        ser.is_valid(raise_exception=True)

        # "integer" is in read_only_fields, so always read-only
        assert ser.fields["integer"].read_only is True
        # "name" is in conditional_read_only, should be editable (not read-only) for staff
        assert ser.fields["name"].read_only is False
        # "boolean" is editable
        assert ser.fields["boolean"].read_only is False

    def test_conditional_readonly_no_request_makes_conditional_fields_readonly(self):
        data = {"name": "Some other name", "integer": 202, "boolean": False}
        # No request in context
        ser = TestConditionalReadOnlySerializer(data=data, context={})
        ser.is_valid(raise_exception=True)

        assert ser.fields["integer"].read_only is True
        assert ser.fields["name"].read_only is True
        assert ser.fields["boolean"].read_only is False

    def test_conditional_readonly_prevents_create(self):
        data = {"name": "Some other name", "integer": 202, "boolean": False}
        ser = TestConditionalReadOnlySerializer(data=data)
        ser.is_valid(raise_exception=True)

        with pytest.raises(MethodNotAllowed):
            ser.save()

    def test_conditional_readonly_prevents_update(self):
        instance = TestModel.objects.create(name="Original Name", integer=101, boolean=True)
        data = {"name": "Some other name", "integer": 202, "boolean": False}
        ser = TestConditionalReadOnlySerializer(instance=instance, data=data)
        ser.is_valid(raise_exception=True)

        with pytest.raises(MethodNotAllowed):
            ser.save()
