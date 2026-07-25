"""
Unit and functional tests for ``apps.core.seeder.executor`` (BaseRunner, BaseSeederRunner, SelectiveSeederRunner, FixtureRunner).
"""

from unittest import mock

import pytest

from apps.core.constants import SeederModes
from apps.core.exceptions import SeederException
from apps.core.seeder.base import BaseSeeder
from apps.core.seeder.executor import (
    BaseRunner,
    BaseSeederRunner,
    FixtureRunner,
    SelectiveSeederRunner,
    is_local_env,
)
from apps.core.seeder.registries import model_seeder_registry, seeder_registry


class TestIsLocalEnvHelper:
    """Tests for environment check function."""

    @mock.patch("apps.core.seeder.executor.settings")
    def test_is_local_env_returns_true_when_debug_and_local(self, mock_settings):
        """is_local_env should return True when DEBUG=True and CURRENT_ENV is in LOCAL_ENVS."""
        mock_settings.DEBUG = True
        mock_settings.CURRENT_ENV = "local"
        mock_settings.LOCAL_ENVS = ["local", "dev"]

        assert is_local_env() is True

    @mock.patch("apps.core.seeder.executor.settings")
    def test_is_local_env_returns_false_when_not_debug(self, mock_settings):
        """is_local_env should return False when DEBUG=False."""
        mock_settings.DEBUG = False
        mock_settings.CURRENT_ENV = "local"
        mock_settings.LOCAL_ENVS = ["local"]

        assert is_local_env() is False

    @mock.patch("apps.core.seeder.executor.settings")
    def test_is_local_env_returns_false_when_env_not_in_local_envs(self, mock_settings):
        """is_local_env should return False when CURRENT_ENV is production."""
        mock_settings.DEBUG = True
        mock_settings.CURRENT_ENV = "prod"
        mock_settings.LOCAL_ENVS = ["local", "dev"]

        assert is_local_env() is False


class ConcreteTestRunner(BaseRunner):
    """Test concrete implementation of BaseRunner."""

    def __init__(self, registry_mock=None, auto_init=False):
        self._mode = SeederModes.FIXTURE.value
        if registry_mock:
            self._registry = registry_mock
        if auto_init:
            super().__init__()
        else:
            self._seeders_to_run = []
            self._adjanceny_list = {}


class TestBaseRunner:
    """Tests for BaseRunner core functionality."""

    def test_init_raises_exception_when_no_seeders_in_registry(self):
        """BaseRunner.__init__ should raise SeederException when registry has no seeders."""
        mock_reg = mock.MagicMock()
        mock_reg.registry = {}

        class EmptyRunner(BaseRunner):
            def __init__(self):
                self._mode = SeederModes.FIXTURE.value
                self._registry = mock_reg
                super().__init__()

        with pytest.raises(SeederException, match="No seeders found to run"):
            EmptyRunner()

    def test_get_registry_dispatches_by_mode(self):
        """get_registry should return model_seeder_registry for SEEDER mode and seeder_registry for FIXTURE mode."""
        runner = ConcreteTestRunner()

        runner._mode = SeederModes.SEEDER.value
        assert runner.get_registry() is model_seeder_registry

        runner._mode = SeederModes.FIXTURE.value
        assert runner.get_registry() is seeder_registry

        runner._mode = "INVALID"
        assert runner.get_registry() is None

    def test_seeder_label_returns_key_or_snake_case(self):
        """seeder_label should return registry key or fallback to snake_case class name."""

        class DummySeederClass(BaseSeeder):
            pass

        mock_reg = mock.MagicMock()
        mock_reg.registry = {"dummy_seeder_class": DummySeederClass}
        mock_reg.__getitem__ = lambda s, k: mock_reg.registry.get(k)

        runner = ConcreteTestRunner(registry_mock=mock_reg)
        label = runner.seeder_label(DummySeederClass)
        assert label == "dummy_seeder_class"

    def test_get_schema_name_extracts_from_seeder_or_data(self):
        """get_schema_name should check seeder get_schema_to_run() or seed_data _meta."""

        class SchemaSeeder:
            @classmethod
            def get_schema_to_run(cls):
                return "tenant_schema_1"

        runner = ConcreteTestRunner()
        assert runner.get_schema_name(SchemaSeeder) == "tenant_schema_1"

    def test_get_schema_name_raises_exception_when_unconfigured(self):
        """get_schema_name should raise SeederException when schema cannot be resolved."""

        class UnconfiguredSeeder:
            pass

        runner = ConcreteTestRunner()
        with pytest.raises(SeederException, match="Invalid configuration for seeder"):
            runner.get_schema_name(UnconfiguredSeeder)

    @mock.patch("apps.core.seeder.executor.schema_context")
    def test_loop_and_run_seeders_executes_seeders(self, mock_schema_context):
        """loop_and_run_seeders should execute sorted seeders in schema context."""
        mock_seeder_instance = mock.MagicMock()

        class RunnableSeeder:
            fixture_only = False

            @classmethod
            def get_schema_to_run(cls):
                return "public"

            def __init__(self, data=None):
                pass

            def seed(self):
                mock_seeder_instance.seed()

        runner = ConcreteTestRunner()
        runner.is_seed_mode = True
        runner.seed_data = {}

        result = runner.loop_and_run_seeders([RunnableSeeder], raise_excp=True)
        assert result is True
        mock_seeder_instance.seed.assert_called_once()

    @mock.patch("apps.core.seeder.executor.schema_context")
    def test_loop_and_run_seeders_skips_fixture_only_when_not_seed_mode(self, mock_schema_context):
        """loop_and_run_seeders should skip fixture_only seeders when is_seed_mode=False."""

        class FixtureOnlySeeder:
            fixture_only = True

            @classmethod
            def get_schema_to_run(cls):
                return "public"

        runner = ConcreteTestRunner()
        runner.is_seed_mode = False
        runner.seed_data = {}

        result = runner.loop_and_run_seeders([FixtureOnlySeeder], raise_excp=True)
        assert result is True
        mock_schema_context.assert_not_called()


class TestDAGTopologicalSorting:
    """Tests for DAG dependency resolution and topological ordering of seeders."""

    def test_get_sorted_seeders_orders_dependencies_correctly(self):
        """get_sorted_seeders should return seeders ordered according to depends_on declarations."""

        class SeederA(BaseSeeder):
            initial = True
            Meta = mock.MagicMock(
                unique_keys_map={},
                tenant_type="public",
                create_realtions=False,
                deep_creation=False,
                Model=mock.MagicMock(),
            )

        class SeederB(BaseSeeder):
            depends_on = [SeederA]
            initial = False
            Meta = mock.MagicMock(
                unique_keys_map={},
                tenant_type="public",
                create_realtions=False,
                deep_creation=False,
                Model=mock.MagicMock(),
            )

        class SeederC(BaseSeeder):
            depends_on = [SeederB]
            initial = False
            Meta = mock.MagicMock(
                unique_keys_map={},
                tenant_type="public",
                create_realtions=False,
                deep_creation=False,
                Model=mock.MagicMock(),
            )

        mock_reg = mock.MagicMock()
        mock_reg.registry = {
            "seeder_a": SeederA,
            "seeder_b": SeederB,
            "seeder_c": SeederC,
        }
        mock_reg.__getitem__ = lambda s, k: mock_reg.registry.get(k)

        runner = ConcreteTestRunner(registry_mock=mock_reg, auto_init=True)
        runner._seeders_to_run = [SeederC, SeederB, SeederA]

        sorted_seeders = runner.get_sorted_seeders()
        assert sorted_seeders == [SeederA, SeederB, SeederC]


class TestBaseSeederRunner:
    """Tests for BaseSeederRunner environment checks and setup."""

    @mock.patch.object(BaseRunner, "is_local_env", return_value=False)
    def test_init_raises_in_non_local_environment(self, mock_env):
        """BaseSeederRunner should raise SeederException when initiated outside local environments."""
        with pytest.raises(SeederException, match="Invalid Seeder Configuration"):
            BaseSeederRunner()

    @mock.patch.object(BaseRunner, "is_local_env", return_value=True)
    def test_init_succeeds_in_local_environment(self, mock_env):
        """BaseSeederRunner should set mode to SEEDER and is_seed_mode to True in local env."""
        mock_reg = mock.MagicMock()
        mock_reg.registry = {"some_seeder": mock.MagicMock()}

        with mock.patch("apps.core.seeder.executor.model_seeder_registry", mock_reg):
            runner = BaseSeederRunner()
            assert runner._mode == SeederModes.SEEDER.value
            assert runner.is_seed_mode is True


class TestSelectiveSeederRunner:
    """Tests for SelectiveSeederRunner custom seeder inputs."""

    @mock.patch.object(BaseRunner, "is_local_env", return_value=True)
    def test_set_input_seeders_validates_and_stores_seeders(self, mock_env):
        """SelectiveSeederRunner should validate that input seeders inherit from BaseSeeder."""

        class CustomSeeder(BaseSeeder):
            Meta = mock.MagicMock(
                unique_keys_map={},
                tenant_type="public",
                create_realtions=False,
                deep_creation=False,
                Model=mock.MagicMock(),
            )

        seeder_inst = CustomSeeder()

        mock_reg = mock.MagicMock()
        mock_reg.registry = {"custom_seeder": CustomSeeder}

        with mock.patch("apps.core.seeder.executor.model_seeder_registry", mock_reg):
            runner = SelectiveSeederRunner(seeders=seeder_inst)
            assert runner.seeders == [seeder_inst]

    @mock.patch.object(BaseRunner, "is_local_env", return_value=True)
    def test_set_input_seeders_raises_for_invalid_seeder(self, mock_env):
        """set_input_seeders should raise SeederException when passed non-BaseSeeder objects."""
        mock_reg = mock.MagicMock()
        mock_reg.registry = {"dummy": mock.MagicMock()}

        with mock.patch("apps.core.seeder.executor.model_seeder_registry", mock_reg):
            with pytest.raises(SeederException, match="Invalid Seeder Configuration"):
                SelectiveSeederRunner(seeders=["not_a_seeder"])


class TestFixtureRunner:
    """Tests for FixtureRunner setup."""

    def test_init_sets_fixture_mode(self):
        """FixtureRunner should initialize with mode FIXTURE and is_seed_mode=False."""
        mock_reg = mock.MagicMock()
        mock_reg.registry = {"fixture": mock.MagicMock()}

        with mock.patch("apps.core.seeder.executor.seeder_registry", mock_reg):
            runner = FixtureRunner()
            assert runner._mode == SeederModes.FIXTURE.value
            assert runner.is_seed_mode is False
