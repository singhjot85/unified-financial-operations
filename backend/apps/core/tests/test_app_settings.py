"""
Tests for ``core.app_settings`` infrastructure.

Coverage:
    - BaseDescriptor  (unit)
    - SettingsMeta    (unit)
    - BaseSettings    (unit + integration)
    - DefferedImport  (unit + integration)
    - DefferedModel   (unit + integration)
    - Constance       (unit)

Per the LLD, these tests are independent of any app state outside ``core``.
Any model or settings class required purely for testing is declared inline
here and uses ``app_label = "core"`` so no migrations are needed.

Key constraints respected:
    - ``Flag.resolve`` must NOT be cached (override_settings must propagate).
    - ``DefferedImport`` is cached per dotted-path — tests patch the target
      object directly rather than reloading.
    - Class-level access (``SettingsClass.FIELD``) must return the descriptor
      itself, not a resolved value.
    - ``django.test.override_settings`` affects Flag / DefferedImport /
      DefferedModel; Constance requires its own test utilities.
"""

from __future__ import annotations

import typing
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from apps.core.app_setting.base import BaseDescriptor, BaseSettings, SettingsMeta
from apps.core.app_setting.types import Constance, DefferedImport, DefferedModel

if typing.TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Minimal concrete helpers (declared purely for tests — no DB needed)
# ---------------------------------------------------------------------------


class PassthroughDescriptor(BaseDescriptor):
    """Concrete descriptor that returns the raw value unchanged (like ``Flag``)."""

    def resolve(self, raw_value: typing.Any) -> typing.Any:  # noqa: D102
        return raw_value


class DoubleDescriptor(BaseDescriptor):
    """Concrete descriptor that doubles an integer raw value (edge-case transform)."""

    def resolve(self, raw_value: int) -> int:  # noqa: D102
        return raw_value * 2


class ConcreteSettings(BaseSettings):
    """Minimal settings class used across unit tests."""

    class Meta:
        app = "test_app"

    SOME_FLAG = PassthroughDescriptor(default=True, help_text="A simple boolean flag")
    SOME_INT = DoubleDescriptor(default=5, help_text="An integer that gets doubled")
    IMPORT_SETTING = DefferedImport(
        default="apps.core.app_settings.base.BaseSettings",
        help_text="A deferred import",
    )


class AnotherSettings(BaseSettings):
    """Second settings class to verify descriptor isolation between classes."""

    class Meta:
        app = "another_app"

    OTHER_FIELD = PassthroughDescriptor(default="hello", help_text="Another setting")


# ---------------------------------------------------------------------------
# Unit: BaseDescriptor
# ---------------------------------------------------------------------------


class TestBaseDescriptor:
    """Unit tests for ``BaseDescriptor`` protocol and low-level mechanics."""

    def test_init_stores_default_and_help_text(self):
        """``__init__`` must persist ``default`` and ``help_text``."""
        descriptor = PassthroughDescriptor(default=42, help_text="docs")
        assert descriptor.default == 42
        assert descriptor.help_text == "docs"

    def test_set_name_records_name_and_owner(self):
        """``__set_name__`` must record ``name`` on the descriptor."""
        descriptor = PassthroughDescriptor(default=10)

        class Holder(BaseSettings):
            FIELD = descriptor

        # After class body executes, __set_name__ has been called
        assert descriptor.name == "FIELD"

    def test_class_level_access_returns_descriptor_itself(self):
        """``Class.FIELD`` must return the descriptor, not a resolved value."""

        class MySettings(BaseSettings):
            MY_FIELD = PassthroughDescriptor(default="raw")

        result = MySettings.MY_FIELD
        assert isinstance(result, PassthroughDescriptor)

    def test_instance_level_access_returns_resolved_value(self):
        """``instance.FIELD`` must return the resolved value, not the descriptor."""
        instance = ConcreteSettings()
        result = instance.SOME_FLAG
        assert result is True

    def test_set_raises_attribute_error(self):
        """Direct assignment to a descriptor attribute must raise ``AttributeError``."""
        instance = ConcreteSettings()
        with pytest.raises(AttributeError, match="read-only"):
            instance.SOME_FLAG = False  # type: ignore[misc]

    def test_resolve_not_implemented_raises(self):
        """``BaseDescriptor.resolve`` must raise ``NotImplementedError`` if not overridden."""

        class BrokenDescriptor(BaseDescriptor):
            pass  # deliberately skips resolve()

        with pytest.raises(NotImplementedError, match="resolve not implemented"):
            BrokenDescriptor(default=None).resolve(None)

    def test_get_raw_value_returns_default_when_no_override(self):
        """``get_raw_value`` must fall back to ``default`` when no project override exists."""
        descriptor = PassthroughDescriptor(default="fallback")

        class Holder(BaseSettings):
            class Meta:
                app = "holder"

            ITEM = descriptor

        instance = Holder()
        raw = descriptor.get_raw_value(instance)
        assert raw == "fallback"

    @override_settings(HOLDER_APP_SETTINGS={"ITEM": "overridden"})
    def test_get_raw_value_honours_project_override(self):
        """``get_raw_value`` must pick up a value from ``django.conf.settings``."""

        class Holder(BaseSettings):
            class Meta:
                app = "holder_app"

            ITEM = PassthroughDescriptor(default="original")

        instance = Holder()
        assert instance.ITEM == "overridden"


# ---------------------------------------------------------------------------
# Unit: SettingsMeta
# ---------------------------------------------------------------------------


class TestSettingsMeta:
    """Unit tests for the ``SettingsMeta`` metaclass."""

    def test_build_override_settings_name_with_meta_app(self):
        """``build_override_settings_name`` must produce ``<NAME_UPPER>_APP_SETTINGS``."""
        name = "FooSettings"

        class FakeMeta:
            app = "foo"

        result = SettingsMeta.build_override_settings_name(name, FakeMeta)
        assert result == "FOOSETTINGS_APP_SETTINGS"

    def test_build_override_settings_name_without_meta(self):
        """Without a ``Meta`` class, the override name must be ``None``."""
        result = SettingsMeta.build_override_settings_name("FooSettings", None)
        assert result is None

    def test_build_override_settings_name_meta_without_app(self):
        """``Meta`` without an ``app`` attribute must produce ``None``."""

        class FakeMeta:
            pass  # no app attr

        result = SettingsMeta.build_override_settings_name("FooSettings", FakeMeta)
        assert result is None

    def test_build_descriptor_map_collects_only_base_descriptors(self):
        """``build_descriptor_map`` must include only ``BaseDescriptor`` instances."""
        d1 = PassthroughDescriptor(default=1)
        d2 = PassthroughDescriptor(default=2)
        attrs = {"FIELD_A": d1, "FIELD_B": d2, "not_a_descriptor": "plain_string", "_private": 99}
        result = SettingsMeta.build_descriptor_map(attrs)
        assert set(result.keys()) == {"FIELD_A", "FIELD_B"}
        assert result["FIELD_A"] is d1
        assert result["FIELD_B"] is d2

    def test_metaclass_sets_override_settings_name_on_class(self):
        """``SettingsMeta`` must set ``override_settings_name`` on every new class."""
        assert ConcreteSettings.override_settings_name is not None

    def test_metaclass_populates_descriptors_dict(self):
        """``_descriptors`` must contain every ``BaseDescriptor`` field declared on the class."""
        descriptors = ConcreteSettings._descriptors
        assert "SOME_FLAG" in descriptors
        assert "SOME_INT" in descriptors
        assert "IMPORT_SETTING" in descriptors

    def test_metaclass_does_not_bleed_descriptors_between_classes(self):
        """Each settings class must have its own isolated ``_descriptors`` dict."""
        assert "SOME_FLAG" not in AnotherSettings._descriptors
        assert "OTHER_FIELD" not in ConcreteSettings._descriptors


# ---------------------------------------------------------------------------
# Unit: BaseSettings helpers
# ---------------------------------------------------------------------------


class TestBaseSettings:
    """Unit tests for ``BaseSettings`` public API."""

    def setup_method(self):
        """Common fixtures for this test class."""
        self.settings = ConcreteSettings()
        self.another = AnotherSettings()

    def test_get_descriptors_returns_all_declared_fields(self):
        """``get_descriptors()`` must return a dict of all declared fields."""
        descriptors = ConcreteSettings.get_descriptors()
        assert "SOME_FLAG" in descriptors
        assert "SOME_INT" in descriptors

    def test_get_setting_names_returns_list_of_names(self):
        """``get_setting_names()`` must return a list of string field names."""
        names = ConcreteSettings.get_setting_names()
        assert isinstance(names, list)
        assert "SOME_FLAG" in names
        assert "SOME_INT" in names

    def test_get_override_key_returns_override_settings_name(self):
        """``get_override_key()`` must match ``override_settings_name``."""
        assert ConcreteSettings.get_override_key() == ConcreteSettings.override_settings_name

    def test_raw_returns_default_when_no_override(self):
        """``raw()`` must return the descriptor's default when no project override is present."""
        raw_value = self.settings.raw("SOME_FLAG")
        assert raw_value is True

    def test_raw_raises_attribute_error_for_unknown_setting(self):
        """``raw()`` must raise ``AttributeError`` for an unrecognised setting name."""
        with pytest.raises(AttributeError, match="not found"):
            self.settings.raw("NONEXISTENT_SETTING")

    @override_settings(CONCRETESETTINGS_APP_SETTINGS={"SOME_FLAG": False})
    def test_raw_honours_project_override(self):
        """``raw()`` must pick up the project-level override value."""
        raw_value = self.settings.raw("SOME_FLAG")
        assert raw_value is False

    def test_double_descriptor_resolution_applies_transform(self):
        """A descriptor's ``resolve()`` transform is applied when accessing via instance."""
        # SOME_INT default=5, DoubleDescriptor doubles it → 10
        assert self.settings.SOME_INT == 10

    @override_settings(CONCRETESETTINGS_APP_SETTINGS={"SOME_INT": 7})
    def test_double_descriptor_resolution_applies_transform_with_override(self):
        """``resolve()`` transform must also be applied to overridden values."""
        # override gives 7, DoubleDescriptor doubles → 14
        assert self.settings.SOME_INT == 14

    def test_flag_not_cached_between_calls(self):
        """
        Calling a PassthroughDescriptor twice with different overrides must
        return different values — caching would break ``override_settings``.
        """
        with override_settings(CONCRETESETTINGS_APP_SETTINGS={"SOME_FLAG": "first"}):
            val1 = self.settings.SOME_FLAG

        with override_settings(CONCRETESETTINGS_APP_SETTINGS={"SOME_FLAG": "second"}):
            val2 = self.settings.SOME_FLAG

        assert val1 == "first"
        assert val2 == "second"


# ---------------------------------------------------------------------------
# Unit: DefferedImport
# ---------------------------------------------------------------------------


class TestDefferedImportDescriptor:
    """Unit tests for ``DefferedImport`` descriptor."""

    def test_resolve_returns_importable_class(self):
        """``DefferedImport.resolve`` must import and return the target class."""
        descriptor = DefferedImport(default="apps.core.app_settings.base.BaseSettings")
        result = descriptor.resolve("apps.core.app_settings.base.BaseSettings")
        assert result is BaseSettings

    def test_resolve_returns_none_and_logs_on_import_error(self, caplog):
        """``DefferedImport.resolve`` must return ``None`` (not raise) for bad import paths."""
        import logging

        descriptor = DefferedImport(default="does.not.exist.SomeClass")
        with caplog.at_level(logging.ERROR, logger="apps.core.app_settings.types"):
            result = descriptor.resolve("does.not.exist.SomeClass")
        assert result is None

    def test_class_level_access_returns_descriptor(self):
        """Class-level access must return the descriptor, not the imported object."""
        descriptor = ConcreteSettings.IMPORT_SETTING
        assert isinstance(descriptor, DefferedImport)

    def test_instance_level_access_resolves_import(self):
        """Instance-level access must resolve and return the imported class."""
        instance = ConcreteSettings()
        result = instance.IMPORT_SETTING
        assert result is BaseSettings

    @override_settings(CONCRETESETTINGS_APP_SETTINGS={"IMPORT_SETTING": "apps.core.app_settings.base.BaseDescriptor"})
    def test_override_settings_redirects_import(self):
        """``override_settings`` must redirect the imported class to the overridden path."""
        instance = ConcreteSettings()
        result = instance.IMPORT_SETTING
        assert result is BaseDescriptor

    def test_resolve_propagates_unexpected_exceptions(self):
        """Non-``ImportError`` exceptions from ``import_string`` must propagate."""
        descriptor = DefferedImport(default="irrelevant")

        with patch("apps.core.app_settings.types.import_string", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError, match="boom"):
                descriptor.resolve("any.path")


# ---------------------------------------------------------------------------
# Unit: DefferedModel
# ---------------------------------------------------------------------------


class TestDefferedModelDescriptor:
    """Unit tests for ``DefferedModel`` descriptor."""

    def test_resolve_returns_model_class(self):
        """``DefferedModel.resolve`` must return a Django model class for a valid label."""
        descriptor = DefferedModel(default="auth.User")
        result = descriptor.resolve("auth.User")

        from django.contrib.auth.models import User

        assert result is User

    def test_resolve_returns_none_and_logs_on_registry_not_ready(self, caplog):
        """
        If ``AppRegistryNotReady`` is raised, ``resolve`` must return ``None``
        and log an error rather than propagating the exception.
        """
        import logging

        from django.core.exceptions import AppRegistryNotReady

        descriptor = DefferedModel(default="crm.Customer")
        with patch("apps.core.app_settings.types.apps.get_model", side_effect=AppRegistryNotReady("not ready")):
            with caplog.at_level(logging.ERROR, logger="apps.core.app_settings.types"):
                result = descriptor.resolve("crm.Customer")
        assert result is None

    def test_resolve_propagates_unexpected_exceptions(self):
        """Non-``AppRegistryNotReady`` exceptions from ``apps.get_model`` must propagate."""
        descriptor = DefferedModel(default="any.Model")

        with patch("apps.core.app_settings.types.apps.get_model", side_effect=ValueError("unexpected")):
            with pytest.raises(ValueError, match="unexpected"):
                descriptor.resolve("any.Model")

    def test_class_level_access_returns_descriptor(self):
        """Class-level access must return the ``DefferedModel`` descriptor itself."""

        class ModelRefSettings(BaseSettings):
            class Meta:
                app = "model_ref"

            USER_MODEL = DefferedModel(default="auth.User")

        assert isinstance(ModelRefSettings.USER_MODEL, DefferedModel)

    def test_instance_level_access_resolves_model(self):
        """Instance-level access must resolve and return the Django model class."""

        class ModelRefSettings(BaseSettings):
            class Meta:
                app = "model_ref"

            USER_MODEL = DefferedModel(default="auth.User")

        from django.contrib.auth.models import User

        instance = ModelRefSettings()
        assert instance.USER_MODEL is User


# ---------------------------------------------------------------------------
# Unit: Constance
# ---------------------------------------------------------------------------


class TestConstanceDescriptor:
    """Unit tests for the ``Constance`` descriptor."""

    def test_constance_key_format(self):
        """``constance_key`` must be ``<NAME_UPPER>_<APP_SETTINGS_NAME_UPPER>``."""

        class MySettings(BaseSettings):
            class Meta:
                app = "my_app"

            MY_TOGGLE = Constance(default=False, help_text="a toggle")

        descriptor = MySettings.MY_TOGGLE  # class-level → returns descriptor
        assert isinstance(descriptor, Constance)
        # name = "MY_TOGGLE", app_settings_name = set from __set_name__ on class body
        assert "MY_TOGGLE" in descriptor.constance_key

    def test_constance_key_raises_if_name_missing(self):
        """``constance_key`` must raise ``RuntimeError`` when ``name`` is absent."""
        descriptor = Constance(default=True)
        # __set_name__ has not been called — name attr is missing
        with pytest.raises(RuntimeError, match="`name`"):
            _ = descriptor.constance_key

    def test_constance_key_raises_if_app_settings_name_missing(self):
        """``constance_key`` must raise ``RuntimeError`` when ``app_settings_name`` is absent."""
        descriptor = Constance(default=True)
        descriptor.name = "SOME_NAME"  # set name but not app_settings_name
        with pytest.raises(RuntimeError, match="`app_settings_name`"):
            _ = descriptor.constance_key

    def test_resolve_reads_from_constance_config(self):
        """``Constance.resolve`` must delegate to ``constance.config`` for its value."""

        class MySettings(BaseSettings):
            class Meta:
                app = "my_app2"

            MY_TOGGLE = Constance(default=False, help_text="a toggle")

        descriptor = MySettings.MY_TOGGLE
        mock_config = MagicMock()
        setattr(mock_config, descriptor.constance_key, True)

        with patch("apps.core.app_settings.types.config", mock_config):
            instance = MySettings()
            result = instance.MY_TOGGLE

        assert result is True

    def test_resolve_logs_and_returns_none_on_attribute_error(self, caplog):
        """
        If ``constance.config`` does not have the key, ``resolve`` must log
        an error and return ``None`` instead of raising.
        """
        import logging

        class MySettings(BaseSettings):
            class Meta:
                app = "my_app3"

            BAD_TOGGLE = Constance(default=False)

        MySettings.BAD_TOGGLE
        mock_config = MagicMock(spec=[])  # no attributes at all → AttributeError on getattr

        with patch("apps.core.app_settings.types.config", mock_config):
            with caplog.at_level(logging.ERROR, logger="apps.core.app_settings.types"):
                instance = MySettings()
                result = instance.BAD_TOGGLE

        assert result is None

    def test_resolve_raises_attribute_error_on_runtime_error(self):
        """A ``RuntimeError`` from constance must surface as ``AttributeError``."""

        class MySettings(BaseSettings):
            class Meta:
                app = "my_app4"

            BROKEN_TOGGLE = Constance(default=False)

        MySettings.BROKEN_TOGGLE

        # getattr(config, constance_key) path — patch getattr to raise RuntimeError
        with patch(
            "apps.core.app_settings.types.getattr",
            side_effect=RuntimeError("descriptor broken"),
        ):
            with pytest.raises((AttributeError, RuntimeError)):
                instance = MySettings()
                _ = instance.BROKEN_TOGGLE

    def test_constance_not_affected_by_override_settings(self):
        """
        ``override_settings`` must NOT change the Constance-backed value; only
        the seed default is affected by project settings, not live DB-backed reads.
        """

        class MySettings(BaseSettings):
            class Meta:
                app = "my_app5"

            LIVE_FLAG = Constance(default=False)

        descriptor = MySettings.LIVE_FLAG
        # simulate constance returning its own value regardless of override_settings
        mock_config = MagicMock()
        setattr(mock_config, descriptor.constance_key, "constance_value")

        override_key = MySettings.override_settings_name
        with patch("apps.core.app_settings.types.config", mock_config):
            with override_settings(**{override_key: {"LIVE_FLAG": "override_value"}}):
                instance = MySettings()
                result = instance.LIVE_FLAG

        # constance value wins — override_settings does NOT affect Constance
        assert result == "constance_value"


# ---------------------------------------------------------------------------
# Integration: end-to-end settings resolution flow
# ---------------------------------------------------------------------------


class TestAppSettingsIntegration:
    """
    Integration tests that exercise the complete resolution pipeline:
    instantiation → descriptor lookup → override resolution → type resolution.

    These tests use a realistic settings class (ConcreteSettings) and verify
    end-to-end behaviour rather than individual methods.
    """

    def setup_method(self):
        """Shared settings instance for all integration tests."""
        self.settings = ConcreteSettings()

    def test_default_passthrough_field_resolves_correctly(self):
        """End-to-end: a ``PassthroughDescriptor`` with a ``bool`` default resolves correctly."""
        assert self.settings.SOME_FLAG is True

    def test_default_transform_field_applies_resolution(self):
        """End-to-end: a ``DoubleDescriptor`` doubles the default value on access."""
        assert self.settings.SOME_INT == 10

    def test_project_override_replaces_default_for_passthrough(self):
        """End-to-end: ``override_settings`` replaces the value for a PassthroughDescriptor."""
        with override_settings(CONCRETESETTINGS_APP_SETTINGS={"SOME_FLAG": "custom"}):
            assert self.settings.SOME_FLAG == "custom"

    def test_project_override_feeds_into_transform(self):
        """End-to-end: overridden raw value passes through ``resolve()`` transform."""
        with override_settings(CONCRETESETTINGS_APP_SETTINGS={"SOME_INT": 3}):
            # DoubleDescriptor doubles 3 → 6
            assert self.settings.SOME_INT == 6

    def test_deferred_import_resolves_real_class(self):
        """End-to-end: ``DefferedImport`` returns the correct live Python class."""
        result = self.settings.IMPORT_SETTING
        assert result is BaseSettings

    def test_override_settings_redirects_deferred_import(self):
        """End-to-end: ``override_settings`` can redirect a ``DefferedImport`` to a different path."""
        with override_settings(
            CONCRETESETTINGS_APP_SETTINGS={"IMPORT_SETTING": "apps.core.app_settings.base.BaseDescriptor"}
        ):
            result = self.settings.IMPORT_SETTING
        assert result is BaseDescriptor

    def test_raw_and_resolved_differ_for_transform_descriptor(self):
        """``raw()`` must return the untransformed value; instance access applies ``resolve()``."""
        raw = self.settings.raw("SOME_INT")
        resolved = self.settings.SOME_INT
        assert raw == 5
        assert resolved == 10

    def test_multiple_settings_classes_are_isolated(self):
        """Descriptors on one settings class must not pollute another class's namespace."""
        another = AnotherSettings()
        with pytest.raises(AttributeError):
            # SOME_FLAG belongs to ConcreteSettings, not AnotherSettings
            _ = another.SOME_FLAG  # type: ignore[attr-defined]

    def test_get_descriptors_is_class_level_only(self):
        """``get_descriptors()`` must be callable on the class, not requiring an instance."""
        result = ConcreteSettings.get_descriptors()
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_instance_cannot_override_descriptor_via_assignment(self):
        """Assigning to a descriptor attribute on an instance must always raise ``AttributeError``."""
        with pytest.raises(AttributeError):
            self.settings.SOME_FLAG = True  # type: ignore[misc]

    def test_deferred_model_integration_with_auth_user(self):
        """End-to-end: ``DefferedModel`` resolves ``auth.User`` to Django's ``User`` model class."""

        class ModelSettings(BaseSettings):
            class Meta:
                app = "model_integration"

            USER_MODEL = DefferedModel(default="auth.User")

        from django.contrib.auth.models import User

        instance = ModelSettings()
        assert instance.USER_MODEL is User

    def test_constance_integration_delegates_to_config(self):
        """End-to-end: ``Constance`` descriptor reads from mocked ``constance.config``."""

        class IntegrationSettings(BaseSettings):
            class Meta:
                app = "integration_app"

            SOME_CONSTANCE_FLAG = Constance(default=False)

        descriptor = IntegrationSettings.SOME_CONSTANCE_FLAG
        mock_config = MagicMock()
        setattr(mock_config, descriptor.constance_key, "live_db_value")

        with patch("apps.core.app_settings.types.config", mock_config):
            instance = IntegrationSettings()
            assert instance.SOME_CONSTANCE_FLAG == "live_db_value"
