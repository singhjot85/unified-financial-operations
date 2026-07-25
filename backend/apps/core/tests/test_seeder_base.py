"""
Unit and functional tests for ``apps.core.seeder.base`` (BaseSeeder & SeederMetaProtocol).
"""

from unittest import mock

import pytest

from apps.core.exceptions import InvalidTypeError, SeederException
from apps.core.seeder.base import BaseSeeder
from apps.core.seeder.registries import seeder_registry


def _create_mock_meta(**attrs):
    """Utility to build a valid Seeder Meta stub for testing."""

    class Meta:
        Model = mock.MagicMock(name="MockModel")
        load_data = attrs.get("load_data", False)
        unique_fields = attrs.get("unique_fields", ["id"])
        unique_keys_map = attrs.get("unique_keys_map", {})
        create_realtions = attrs.get("create_realtions", False)
        deep_creation = attrs.get("deep_creation", False)
        tenant_type = attrs.get("tenant_type", "public")
        fixture_only = attrs.get("fixture_only", False)
        TENANT_TYPE_PUBLIC = "public"
        TENANT_TYPE_PRIVATE = "private"

    return Meta


class TestSeederSubclassRegistration:
    """Tests for BaseSeeder subclass registration behavior."""

    def setup_method(self):
        self._initial_keys = set(seeder_registry.registry.keys())

    def teardown_method(self):
        current_keys = set(seeder_registry.registry.keys())
        for key in current_keys - self._initial_keys:
            seeder_registry.unregister(key)

    def test_subclass_automatically_registers_in_registry(self):
        """Subclassing BaseSeeder should automatically register the class with a snake_case key."""

        class CustomSeederTestClass(BaseSeeder):
            Meta = _create_mock_meta()

        registry_key = "custom_seeder_test_class"
        assert registry_key in seeder_registry.registry
        assert seeder_registry.registry[registry_key] is CustomSeederTestClass

    def test_subclass_raises_exception_when_depends_on_contains_non_model_class(self):
        """Subclassing BaseSeeder should raise SeederException when Meta.depends_on contains non-Model items."""
        invalid_meta = _create_mock_meta()
        invalid_meta.depends_on = ["not_a_model_class"]

        with pytest.raises(SeederException, match="Dependencies should be Model classes only"):

            class InvalidDependsSeeder(BaseSeeder):
                Meta = invalid_meta


class TestBaseSeederInitialization:
    """Tests for BaseSeeder constructor and configuration validation."""

    def test_init_raises_exception_when_meta_missing(self):
        """Instantiating BaseSeeder without a Meta attribute must raise SeederException."""

        class InvalidSeeder(BaseSeeder):
            Meta = None

        # Override Meta attribute after class creation to test missing Meta exception
        delattr(InvalidSeeder, "Meta")

        with pytest.raises(SeederException, match="not Meta class Configured"):
            InvalidSeeder()

    def test_init_sets_attributes_from_meta_and_args(self):
        """Constructor should properly populate _meta, fixture_only, and _data."""
        mock_meta = _create_mock_meta(fixture_only=True)

        class ValidSeeder(BaseSeeder):
            Meta = mock_meta

        test_data = [{"name": "item1"}]
        seeder = ValidSeeder(data=test_data)

        assert seeder._meta is mock_meta
        assert seeder.fixture_only is True
        assert seeder._data == test_data


class TestBaseSeederValidation:
    """Tests for data validation logic in BaseSeeder."""

    @classmethod
    def setup_class(cls):
        class DummySeeder(BaseSeeder):
            Meta = _create_mock_meta()

        cls.seeder = DummySeeder()

    def test_validate_data_accepts_list_and_dict(self):
        """validate_data should succeed when passed a list or dict."""
        self.seeder.validate_data([{"key": "val"}])
        self.seeder.validate_data({"key": "val"})

    def test_validate_data_raises_invalid_type_error_for_other_types(self):
        """validate_data should raise InvalidTypeError for invalid data structures."""
        with pytest.raises(InvalidTypeError):
            self.seeder.validate_data("string_data")

        with pytest.raises(InvalidTypeError):
            self.seeder.validate_data(12345)

        with pytest.raises(InvalidTypeError):
            self.seeder.validate_data(None)


class TestBaseSeederDataLoading:
    """Tests for data loading dispatch in BaseSeeder."""

    def test_load_data_returns_provided_data(self):
        """load_data should return constructor data when supplied."""

        class DataSeeder(BaseSeeder):
            Meta = _create_mock_meta(load_data=False)

        expected = [{"code": "ABC"}]
        seeder = DataSeeder(data=expected)
        assert seeder.load_data() == expected

    def test_load_data_from_fixture_when_load_data_true(self):
        """load_data should auto-discover and load from fixture file when load_data=True and no constructor data."""

        class FixtureSeeder(BaseSeeder):
            Meta = _create_mock_meta(load_data=True)

        seeder = FixtureSeeder()
        fixture_content = [{"code": "XYZ"}]

        with (
            mock.patch.object(seeder, "auto_discover_fixtures_directory") as mock_discover,
            mock.patch.object(seeder, "load_from_file", return_value=fixture_content) as mock_load,
        ):
            seeder._fixtures_file = "/path/to/fixture.json"
            result = seeder.load_data()

        mock_discover.assert_called_once()
        mock_load.assert_called_once_with("/path/to/fixture.json")
        assert result == fixture_content

    def test_load_data_raises_exception_when_no_data_source(self):
        """load_data should raise SeederException when neither data nor fixture config is present."""

        class EmptySeeder(BaseSeeder):
            Meta = _create_mock_meta(load_data=False)

        seeder = EmptySeeder()
        with pytest.raises(SeederException, match="Error loading seed data"):
            seeder.load_data()


class TestBaseSeederObjectCreation:
    """Tests for ObjectCreator delegation and metadata handling."""

    @classmethod
    def setup_class(cls):
        cls.mock_meta = _create_mock_meta(
            unique_keys_map={"RelatedModel": ["code"]},
            tenant_type="public",
        )

        class SampleSeeder(BaseSeeder):
            Meta = cls.mock_meta

        cls.seeder = SampleSeeder()

    def test_get_object_metadata_extracts_inline_meta(self):
        """get_object_metadata should pop inline _meta dict when present in obj data."""
        inline_meta = {"unique_fields": ["code"]}
        data = {"code": "123", "_meta": inline_meta}

        extracted = self.seeder.get_object_metadata(data)
        assert extracted == {"unique_fields": ["code"]}
        assert "_meta" not in data

    def test_get_object_metadata_falls_back_to_class_meta(self):
        """get_object_metadata should return class _meta __dict__ when no inline _meta exists."""
        data = {"code": "123"}
        extracted = self.seeder.get_object_metadata(data)
        assert extracted == self.mock_meta.__dict__

    @mock.patch("apps.core.seeder.base.ObjectCreator")
    def test_create_object_instantiates_creator_for_each_data_dict(self, mock_creator):
        """create_object should create an ObjectCreator for each dictionary in data."""
        mock_creator.return_value = "CreatedObj"
        data_list = [{"name": "A"}, {"name": "B"}]

        objs = self.seeder.create_object(data_list)
        assert objs == ["CreatedObj", "CreatedObj"]
        assert mock_creator.call_count == 2

    def test_get_unique_fields_looks_up_keys_map(self):
        """get_unique_fields should return configured unique keys for a model class or string."""
        assert self.seeder.get_unique_fields("RelatedModel") == ["code"]
        assert self.seeder.get_unique_fields("UnmappedModel") is None

    @mock.patch("apps.core.seeder.base.get_public_schema_name", return_value="public")
    def test_get_schema_to_run_returns_public_for_public_tenant(self, mock_public_schema):
        """get_schema_to_run should return public schema name for TENANT_TYPE_PUBLIC."""
        assert self.seeder.get_schema_to_run() == "public"
        mock_public_schema.assert_called_once()

    def test_get_schema_to_run_raises_for_unsupported_tenant_type(self):
        """get_schema_to_run should raise SeederException for non-public tenant_type."""

        class PrivateSeeder(BaseSeeder):
            Meta = _create_mock_meta(tenant_type="private")

        seeder = PrivateSeeder()
        with pytest.raises(SeederException, match="No schema configured"):
            seeder.get_schema_to_run()

    @mock.patch.object(BaseSeeder, "create_object")
    def test_seed_workflow_executes_load_validate_create(self, mock_create):
        """seed() should orchestrate load_data -> validate_data -> create_object."""
        mock_create.return_value = ["obj1"]

        class SeedWorkflowSeeder(BaseSeeder):
            Meta = _create_mock_meta()

        seeder = SeedWorkflowSeeder(data=[{"a": 1}])
        result = seeder.seed()

        assert result == ["obj1"]
        mock_create.assert_called_once_with([{"a": 1}])
