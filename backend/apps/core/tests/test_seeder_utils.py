"""
Unit and functional tests for ``apps.core.seeder.utils`` (ObjectCreator, SeederMixin, FixtureMixin).
"""

from pathlib import Path
from unittest import mock

import pytest

from apps.core.exceptions import ObjectCreatorException, SeederException
from apps.core.seeder.base import BaseSeeder
from apps.core.seeder.utils import FixtureMixin, ObjectCreator, SeederMixin


def _create_mock_model_class(name="MockModel"):
    """Helper to generate a mock Django Model class."""
    mock_model = mock.MagicMock()
    mock_model.__name__ = name
    mock_model._meta = mock.MagicMock()
    mock_model._meta.get_fields = mock.MagicMock(return_value=[])
    mock_model._meta.related_objects = []
    mock_model.objects = mock.MagicMock()
    return mock_model


class TestObjectCreatorInitialization:
    """Tests for ObjectCreator instantiation and validation."""

    def test_init_raises_exception_when_model_or_data_missing(self):
        """ObjectCreator should raise SeederException when model or data is invalid/missing."""
        mock_model = _create_mock_model_class()

        with pytest.raises(SeederException, match="Invalid ObjectCreator configuration"):
            ObjectCreator(model=None, data={"a": 1})

        with pytest.raises(SeederException, match="Invalid ObjectCreator configuration"):
            ObjectCreator(model=mock_model, data=None)

    def test_init_raises_exception_when_invalid_seeder_passed(self):
        """ObjectCreator should raise SeederException when seeder parameter is not a BaseSeeder instance."""
        mock_model = _create_mock_model_class()

        with pytest.raises(SeederException, match="Invalid seeder provided"):
            ObjectCreator(model=mock_model, data={"a": 1}, seeder="not_a_seeder_instance")

    def test_init_populates_instance_attributes(self):
        """ObjectCreator should set model, data, database, and relation flags."""
        mock_model = _create_mock_model_class()
        data = {"field1": "val1"}

        creator = ObjectCreator(
            model=mock_model,
            data=data,
            database="test_db",
            create_relations=True,
            deep_creation=True,
        )

        assert creator._model is mock_model
        assert creator.seed_data == data
        assert creator._database == "test_db"
        assert creator._create_relations is True
        assert creator._deep_creation is True


class TestObjectCreatorPropertiesAndFields:
    """Tests for ObjectCreator property accessors and field attribute settings."""

    def setup_method(self):
        self.mock_model = _create_mock_model_class()

    def test_seed_data_property_returns_dict_or_empty_dict(self):
        """seed_data property should return dataset dict or empty dict when empty."""
        creator = ObjectCreator(model=self.mock_model, data={"x": 100})
        assert creator.seed_data == {"x": 100}

    def test_get_unique_fields_resolves_from_metadata(self):
        """get_unique_fields should retrieve unique fields from metadata dict."""
        metadata = {"unique_fields": ["code", "tenant"]}
        creator = ObjectCreator(model=self.mock_model, data={"code": "C1"}, metadata=metadata)

        assert creator.get_unique_fields(self.mock_model) == ["code", "tenant"]

    def test_get_unique_fields_resolves_from_seeder(self):
        """get_unique_fields should fall back to seeder.get_unique_fields when metadata is absent."""
        mock_seeder = mock.MagicMock(spec=BaseSeeder)
        mock_seeder.get_unique_fields.return_value = ["sku"]

        creator = ObjectCreator(model=self.mock_model, data={"sku": "S1"}, seeder=mock_seeder)
        assert creator.get_unique_fields(self.mock_model) == ["sku"]

    def test_get_unique_fields_raises_exception_when_unresolvable(self):
        """get_unique_fields should raise SeederException when unique fields cannot be found."""
        creator = ObjectCreator(model=self.mock_model, data={"x": 1})
        with pytest.raises(SeederException, match="unable to find unique fields"):
            creator.get_unique_fields(self.mock_model)

    def test_set_field_attribute_uses_custom_seeder_setter(self):
        """set_field_attribute should invoke set_<field_name> on seeder if method exists."""
        mock_seeder = mock.MagicMock(spec=BaseSeeder)
        mock_seeder.set_password = mock.MagicMock()

        creator = ObjectCreator(model=self.mock_model, data={"password": "raw"}, seeder=mock_seeder)
        mock_instance = mock.MagicMock()

        creator.set_field_attribute(mock_instance, "password", "raw_secret")
        mock_seeder.set_password.assert_called_once_with(mock_instance, "password", "raw_secret")

    def test_set_field_attribute_falls_back_to_setattr(self):
        """set_field_attribute should call setattr on model instance when no custom setter exists."""
        creator = ObjectCreator(model=self.mock_model, data={"name": "John"})
        mock_instance = mock.MagicMock()

        creator.set_field_attribute(mock_instance, "name", "John Doe")
        assert mock_instance.name == "John Doe"


class TestObjectCreatorRelations:
    """Tests for Foreign Key and Many-To-Many relation processing in ObjectCreator."""

    def setup_method(self):
        self.mock_model = _create_mock_model_class()

    def test_process_foreign_relation_handles_model_instance(self):
        """process_foreign_relation should attach Model instances directly."""
        from django.db import models

        creator = ObjectCreator(model=self.mock_model, data={"rel": "val"})
        creator._instance = mock.MagicMock()

        mock_field = mock.MagicMock()
        mock_field.name = "parent"

        related_model_inst = mock.MagicMock(spec=models.Model)
        creator.process_foreign_relation(mock_field, related_model_inst)

        assert creator._instance.parent is related_model_inst

    def test_process_foreign_relation_handles_primitive_values(self):
        """process_foreign_relation should set primitive values (int/str/None) directly."""
        creator = ObjectCreator(model=self.mock_model, data={"rel": "val"})
        creator._instance = mock.MagicMock()

        mock_field = mock.MagicMock()
        mock_field.name = "category_id"

        creator.process_foreign_relation(mock_field, 42)
        assert creator._instance.category_id == 42

    def test_process_foreign_relation_raises_for_invalid_type(self):
        """process_foreign_relation should raise ObjectCreatorException for unsupported raw values."""
        creator = ObjectCreator(model=self.mock_model, data={"rel": "val"})
        creator._instance = mock.MagicMock()

        mock_field = mock.MagicMock()
        mock_field.name = "invalid_rel"

        with pytest.raises(ObjectCreatorException, match="Invalid value for Relation"):
            creator.process_foreign_relation(mock_field, object())

    def test_process_m2m_fields_clears_and_adds_objects(self):
        """process_m2m_fields should clear existing items and add resolved objects to manager."""
        creator = ObjectCreator(model=self.mock_model, data={"m2m": "val"}, create_relations=True)
        creator._instance = mock.MagicMock()

        mock_manager = mock.MagicMock()
        creator._instance.tags = mock_manager

        mock_field = mock.MagicMock()
        mock_related_model = _create_mock_model_class("Tag")
        mock_field.related_model = mock_related_model
        creator._instance._meta.get_field.return_value = mock_field

        tag_obj1 = mock.MagicMock()
        tag_obj2 = mock.MagicMock()
        mock_related_model.objects.filter.return_value = [tag_obj1, tag_obj2]

        creator.process_m2m_fields({"tags": [1, 2]})

        mock_manager.clear.assert_called_once()
        mock_manager.add.assert_called_once_with(tag_obj1, tag_obj2)


class TestObjectCreatorCreationWorkflow:
    """Tests for ObjectCreator.create_object lifecycle and hook execution."""

    def test_create_object_triggers_pre_and_post_hooks(self):
        """create_object should invoke pre_object_creation_hook and post_object_creation_hook on seeder."""
        mock_model = _create_mock_model_class()

        class HookSeeder(BaseSeeder):
            Meta = mock.MagicMock(
                unique_keys_map={}, tenant_type="public", create_realtions=False, deep_creation=False, Model=mock_model
            )
            pre_hook_called = False
            post_hook_called = False

            def pre_object_creation_hook(self, data):
                self.pre_hook_called = True

            def post_object_creation_hook(self, instance):
                self.post_hook_called = True

        seeder = HookSeeder()
        creator = ObjectCreator(model=mock_model, data={"name": "test"}, seeder=seeder)

        with mock.patch.object(creator, "_create_object") as mock_internal_create:
            mock_inst = mock.MagicMock()
            creator._instance = mock_inst
            created = creator.create_object()

        assert seeder.pre_hook_called is True
        assert seeder.post_hook_called is True
        mock_internal_create.assert_called_once()
        assert created is mock_inst


class TestSeederAndFixtureMixins:
    """Tests for SeederMixin and FixtureMixin helper routines."""

    def test_auto_discover_fixtures_directory_locates_existing_fixture_path(self):
        """auto_discover_fixtures_directory should return fixture path when it exists."""

        class DummySeeder(SeederMixin):
            _fallback_path = "/global/fallback"

        with (
            mock.patch("apps.core.seeder.utils.inspect.getfile", return_value="/app/seeders/dummy.py"),
            mock.patch.object(Path, "exists", return_value=True),
        ):
            found_path = DummySeeder.auto_discover_fixtures_directory()
            assert found_path is not None

    def test_auto_discover_fixtures_directory_raises_when_path_not_found(self):
        """auto_discover_fixtures_directory should raise SeederException when no fixture folder exists."""

        class OrphanSeeder(SeederMixin):
            _fallback_path = "/nonexistent/fallback"

        with (
            mock.patch("apps.core.seeder.utils.inspect.getfile", return_value="/app/seeders/orphan.py"),
            mock.patch.object(Path, "exists", return_value=False),
        ):
            with pytest.raises(SeederException, match="Unable to find fixtures"):
                OrphanSeeder.auto_discover_fixtures_directory()

    def test_seeder_name_to_search_returns_expected_convention(self):
        """seeder_name_to_search should append Seeder suffix to class name."""
        with (
            mock.patch.object(FixtureMixin, "auto_discover_model_seeder", return_value=mock.MagicMock()),
            mock.patch.object(FixtureMixin, "auto_discover_fixtures_directory", return_value="/tmp/fixture"),
        ):

            class CustomFixture(FixtureMixin):
                pass

            assert CustomFixture.seeder_name_to_search() == "CustomFixtureSeeder"
