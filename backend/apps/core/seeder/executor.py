import logging
import typing

from django.conf import settings
from django.db import transaction
from django_tenants.utils import schema_context

from apps.core.constants import SeederModes
from apps.core.datatypes import AbstractDAGBuilder
from apps.core.exceptions import SeederException
from apps.core.seeder import BaseSeeder, model_seeder_registry, seeder_registry
from apps.core.utils import FileHandlingMixin, camel_to_snake_case

LOGGER = logging.getLogger(__name__)


def is_local_env() -> bool:
    return settings.DEBUG and (settings.CURRENT_ENV in settings.LOCAL_ENVS)


class BaseRunner(AbstractDAGBuilder, FileHandlingMixin):
    """
    Avoid Inheriting this runner directly, use ``BaseSeedeRunner`` and ``BaseFixtureRunner`` defined below
    """

    is_seed_mode: bool
    seed_data: dict

    _mode: str = SeederModes.FIXTURE.value
    _first_seeder: type["BaseSeeder"]
    _seeders_to_run: list[type["BaseSeeder"]]

    _s2n_map: dict[str, int]
    _n2s_map: dict[int, type["BaseSeeder"]]

    def __init__(self):
        self._seeders_to_run = [seeder for _, seeder in self.registry.registry]

        if not self._seeders_to_run:
            raise SeederException("No seeders found to run")

    def is_local_env(self) -> bool:
        return settings.DEBUG and (settings.CURRENT_ENV in settings.LOCAL_ENVS)

    @property
    def seeders(self):
        return self._seeders_to_run

    @property
    def registry(self):
        if hasattr(self, "_registry"):
            return self._registry

        self._registry = self.get_registry()
        return self._registry

    def get_registry(self):
        """Get registry based on the mode of the registry"""
        if self._mode == SeederModes.SEEDER.value:
            return model_seeder_registry
        elif self._mode == SeederModes.FIXTURE.value:
            return seeder_registry

        return None

    def seeder_label(self, kls: type["BaseSeeder"]) -> str:
        """
        Get label for seeder, for telematry

        Args:
            kls (BaseSeeder): Seeder Class
        """
        if not self.registry:
            return camel_to_snake_case(kls.__name__)
        elif (possible_name := camel_to_snake_case(kls.__name__)) in self.registry.registry and self.registry[
            possible_name
        ] == kls:
            # Save's CPU cycle's in 99% of cases
            return possible_name

        for label, seeder in self.registry.registry:
            if seeder.__name__ == seeder.__name__:
                return label

    def seeder_to_number_map(self) -> dict:
        """
        Builds a Map where each seeder is given a number, to work with DAG Builder
        """
        self._s2n_map = {}
        for i, seeder in enumerate(self.seeders):
            self._s2n_map[self.seeder_label(seeder)] = i
            self._n2s_map[i] = seeder

    def resolve_dependencies(self):
        """
        Resolve Dependencies on given seeders to run and build adjaceny_list,
        Basically converts dependecies in graph,

        NOTE: All logic is abstacted behind DAGBuilder, here we only add nodes
        """
        for seeder in self.seeders:
            if hasattr(seeder, "depends_on") and seeder.depends_on:
                for dep in seeder.depends_on:
                    self.add_node(
                        from_index=self._s2n_map[self.seeder_label(dep)],
                        to_index=self._s2n_map[self.seeder_label(seeder)],
                    )
            elif seeder.initial:
                self._first_seeder = seeder

            raise SeederException("Invalid Seeder Setup")

    def get_sorted_seeders(self) -> list[type["BaseSeeder"]]:
        """
        Get sorted Seeders in the order of the dependencies
        """
        self.resolve_dependencies()
        sorted_graph: list[int] = self.bfs_topological_sort()

        sorted_seeders: list[type["BaseSeeder"]] = []
        for index in sorted_graph:
            sorted_seeders.append(self._n2s_map[index])

        return [self._first_seeder] + sorted_seeders

    def get_schema_name(self, Seeder: type["BaseSeeder"]) -> str:
        """
        Get the schema name to run the seeder, tries three locations:
        1. Seeder Data
        2. Seeder.get_schema_to_run
        """
        schema_name = None
        if hasattr(self, "seed_data"):
            data = self.seed_data.get(Seeder.__name__, {})
            if isinstance(data, (list)) and (meta := data[0].get("_meta")):
                schema_name = meta.get("schema_name")
            elif isinstance(data, (dict)) and (meta := data.get("_meta")):
                schema_name = meta.get("schema_name")

        if hasattr(Seeder, "get_schema_to_run"):
            schema_name = Seeder.get_schema_to_run()

        if schema_name:
            return schema_name

        raise SeederException(f"Invalid configuration for seeder >>> {self.seeder_label(Seeder)}")

    def loop_and_run_seeders(self, seeders: list[type["BaseSeeder"]], raise_excp) -> typing.Optional[bool]:
        """
        Loop over sorted seeders, and run them individually

        Args:
            seeders (BaseSeeder): Sorted seeders to run
            raise_excp (bool): Raise Exception on failure.

        Returns:
            boolean representing failure or success
        """

        for Seeder in seeders:
            if Seeder.fixture_only and not self.is_seed_mode:
                continue

            label = self.seeder_label(Seeder)
            schema_name = self.get_schema_name(Seeder)

            LOGGER.info(msg=f"[{schema_name}] Running Seeder >>> {label}")
            try:
                with schema_context(schema_name):
                    seeder_obj = Seeder(data=self.seed_data.get(Seeder.__name__))
                    seeder_obj.seed()

                LOGGER.info(msg=f"[{schema_name}] Succefully Executed Seeder >>> {label}")
            except Exception as e:

                LOGGER.error(msg=f"[{schema_name}] Failed Executing Seeder >>> {label}", exc_info=e)
                if raise_excp:
                    raise SeederException(f"[{schema_name}] Failed to run seeder >>> {label}") from e

                return False

        return True

    def run(self, raise_excp: bool = False):
        """
        Complete lifecycle for seeder execution.

        Args:
            seeders (BaseSeeder): Sorted seeders to run
            raise_excp (bool): Raise Exception on failure.
        """
        LOGGER.info(msg=f"[{self._mode}] Running Seeders...")
        seeders = self.get_sorted_seeders()

        with transaction.atomic():
            try:
                is_success = self.loop_and_run_seeders(seeders, raise_excp)
            except Exception as e:
                raise e

            if is_success:
                LOGGER.info(msg=f"[{self._mode}] All Seeders executed sucessfully...")


class BaseSeederRunner(BaseRunner):
    """
    BaseSeederRunner is the base class for all seeder runners

    Attributes:
        is_seed_mode (bool): Flag to indicate if the runner is running in seed mode or fixture mode
        seed_data (dict): Data to be seeded, if not provided, will be loaded from the deafult file in the seeder class
    """

    def __init__(self):

        self._mode = SeederModes.SEEDER.value
        self.is_seed_mode = True

        if not self.is_local_env():
            raise SeederException("Invalid Seeder Configuration")

        super().__init__()


class SelectiveSeederRunner(BaseSeederRunner):
    """
    SelectiveSeederRunner is the base class for all selective seeder runners,
        it allows to run specific seeders instead of all seeders.

    Args:
        seeders (BaseSeeder | list): Seeders to be run independently
    """

    def __init__(self, seeders: typing.Union["BaseSeeder", list["BaseSeeder"]] = None):
        super().__init__()

        if seeders:
            self._seeders_to_run = self.set_input_seeders(seeders)

    def set_input_seeders(self, seeders):
        """
        Setup seeder's for manual execution
        """
        if not isinstance(seeders, list):
            seeders = [seeders]

        if not all([isinstance(seeder, BaseSeeder) for seeder in seeders]):
            raise SeederException("Invalid Seeder Configuration")

        self._seeders_to_run = seeders


class FixtureRunner(BaseRunner):

    def __init__(self):
        self._mode = SeederModes.FIXTURE.value
        self.is_seed_mode = False

        super().__init__()
