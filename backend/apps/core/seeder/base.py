import typing

from django.db import models
from django_tenants.utils import get_public_schema_name

from apps.core.exceptions import InvalidTypeError, SeederException
from apps.core.seeder.registries import seeder_registry
from apps.core.seeder.utils import ObjectCreator, SeederMixin
from apps.core.utils import FileHandlingMixin, camel_to_snake_case


class SeederMetaProtocol(typing.Protocol):

    TENANT_TYPE_PUBLIC = "public"
    TENANT_TYPE_PRIVATE = "private"

    Model: type[models.Model]
    depends_on: list[type[models.Model]]
    load_data: bool

    unique_fields: list[str]
    unique_keys_map: dict[str, list]

    create_realtions: bool = False
    deep_creation: bool = False

    tenant_type: str = TENANT_TYPE_PUBLIC
    fixture_only: bool = False

    def __init_subclass__(cls):
        """Validate Each Seeder's Meta Configuration"""
        if not isinstance(cls.Model, models.Model):
            raise SeederException("Model must be a subclass of django.db.models.Model")

        if hasattr(cls, "depends_on") and cls.depends_on:
            if not all([isinstance(k, type) and issubclass(k, models.Model) for k in cls.depends_on]):
                raise SeederException("Dependencies should be Model classes only")

        if cls.deep_creation:
            cls.create_realtions = True

        if not isinstance(cls.unique_fields, list):
            raise InvalidTypeError(type=type(cls.unique_fields), expected="list")

    def run_validations(self):
        """
        Runtime Validations for seeder Meta class
        TODO:
        - Validate Fields passed in ``unique_keys_map`` belong to the models they are mentioned under
        """
        pass


class BaseSeeder(SeederMixin, FileHandlingMixin):
    _fixtures_file: str

    _meta: "SeederMetaProtocol"
    _data: typing.Union[dict, list]

    fixture_only: bool

    def __init_subclass__(cls):
        """Auto Register the seeders to registry"""
        meta = getattr(cls, "Meta", None)
        if meta:
            depends_on = getattr(meta, "depends_on", None)
            if isinstance(depends_on, (list, tuple)):
                if not all([isinstance(k, type) and issubclass(k, models.Model) for k in depends_on]):
                    raise SeederException("Dependencies should be Model classes only")
        try:
            seeder_registry.register(cls, key=camel_to_snake_case(cls.__name__))
        except Exception as e:
            raise SeederException(f"Error registering model: {cls.__name__},in registry") from e

    def __init__(self, data: typing.Union[dict, list] = None):
        """
        Runtime validations to ensure a valid seeder is set up.
        """
        self._meta = getattr(self, "Meta", None)
        if not self._meta:
            raise SeederException("Invalid Seeder Configuration, not Meta class Configured.")

        self.fixture_only = self._meta.fixture_only
        self._data = data

    def validate_data(self, data):
        """
        Validate the data to be passed to ``ObjectCreator``

        Raises:
            InvalidTypeError
        """
        if not isinstance(data, (list, dict)):
            raise InvalidTypeError(type=type(data), expected="list/dict")

        return data

    def seed(self) -> list[models.Model]:
        """
        Actual Seed implementaion, seeds the data in the database using ``ObjectCreator``
        """
        data = self.validate_data(self.load_data())
        objects: list[models.Model] = self.create_object(data)
        return objects

    def load_data(self) -> typing.Union[list, dict]:
        """
        Load data from the fixture file, if not provided in the constructor
        Returns:
            Data from the fixture file or from the constructor
        Raises:
            SeederException: If no data is found in the constructor or fixture file
        """
        if self._data:
            return self._data

        if self._meta.load_data:
            self.auto_discover_fixtures_directory()
            return self.load_from_file(self._fixtures_file)

        raise SeederException("Error loading seed data.")

    def get_object_metadata(self, data: dict) -> dict:
        """
        Getter to fetch object metadata from fixture file
        By deafault dumps enire metaclass attributes

        Args:
            data (dict): Data from fixture file per object

        Returns:
            Metadata from fixture file
        """
        if meta_from_file := data.pop("_meta", None):
            return meta_from_file

        return self._meta.__dict__

    def create_object(self, data: typing.Union[dict, list]) -> list[models.Model]:
        """
        Create Object:
        - Arrange Data
        - Fetch Metadata
        - Create Object
        """
        if isinstance(data, dict):
            data = (data,)

        objs = []
        for obj_data in data:
            object_metadata = self.get_object_metadata(obj_data)
            obj = ObjectCreator(
                model=self._meta.Model,
                data=obj_data,
                metadata=object_metadata,
                create_relations=self._meta.create_realtions,
                deep_creation=self._meta.deep_creation,
                seeder=self,
            )
            objs.append(obj)

        return objs

    def get_unique_fields(self, kls: type[models.Model]) -> list[str]:
        """
        Helper for ``ObjectCreator`` to fetch unique keys for the model

        Args:
            kls (type[Model]): Class to fetch the unique keys for.
        """
        if isinstance(kls, models.Model):
            kls = kls.__name__

        return self._meta.unique_keys_map.get(kls)

    def get_schema_to_run(self) -> str:
        """
        Get the schema name to run the seeder, based on the tenant type
        Returns:
            schema name to run the seeder
        """
        if self._meta.tenant_type == self._meta.TENANT_TYPE_PUBLIC:
            return get_public_schema_name()

        raise SeederException("No schema configured for the seeder to run in")
