import typing

from django.db import models
from django_tenants.utils import get_public_schema_name

from apps.core.constants import SeederMethod
from apps.core.exceptions import SeederException
from apps.core.seeder.registries import seeder_registry
from apps.core.seeder.utils import ObjectCreator, SeederAutoDiscovery
from apps.core.utils import FileHandlingMixin, camel_to_snake_case


class BaseSeeder(SeederAutoDiscovery, FileHandlingMixin):

    TENANT_TYPE_PUBLIC = "public"
    TENANT_TYPE_PRIVATE = "private"

    # Override's set by user
    initial: bool = False
    dev_only: bool = True

    model: models.Model
    depends_on: list["BaseSeeder"]
    unique_fields_map: dict[str, list]
    tenant_type: str = TENANT_TYPE_PUBLIC

    # Internal class variables
    _file_name: str
    _atomic: bool = False
    _objects_method: str = SeederMethod.GET_OR_CREATE.value
    _fixtures_file: str

    @classmethod
    def get_seeder_name(cls):
        """Seeder name is the class name here"""
        return cls.__name__

    def __init_subclass__(cls):
        """
        Auto Discover and register seeder to registry
        Auto Discover and seed data files to class attribute
        """
        try:
            seeder = cls.auto_discover_model_seeder()
            seeder_registry.register(seeder, key=camel_to_snake_case(cls.__name__))
        except Exception as e:
            raise SeederException(f"Error registering model: {cls.__name__},in registry") from e

        try:
            cls._fixtures_file = cls.auto_discover_fixtures_directory()
        except Exception as e:
            raise SeederException(f"Error in fixture auto-discovery for class: {cls.__name__}") from e

    def __init__(self, is_dev: bool = True):
        """
        Runtime validations to ensure a valid seeder is set up.
        """
        if not is_dev and not self.dev_only:
            raise SeederException("Invalid Seeder Configuration")

        if not self.model:
            raise SeederException(f"Model not registered for >>> {self.__class__.__name__}")

        if not self.unique_fields_map:
            raise SeederException(f"Please define unique keys for >>> {self.__class__.__name__}")

    def get_schema_name(self):
        """
        Get schema name to run the seeder in
        """
        if self.tenant_type == self.TENANT_TYPE_PUBLIC:
            return get_public_schema_name()
        elif self.tenant_type == self.TENANT_TYPE_PRIVATE:
            self.get_data.get("_meta", {})

        # TODO
        return get_public_schema_name()

    def seed(self):
        """
        Seed data in model istance
        """
        file = self.get_file()
        data = self.get_data(file)
        self.create_object(data)

    def get_file(self):
        """
        Get fixture file absolute path containing fixture data
        """
        return self._fixtures_file

    def get_data(self, file: str) -> typing.Union[dict, typing.Any]:
        """
        Get data from fixture file
        """
        data = self.load_from_file(file)
        return data

    def create_object(self, data: dict) -> models.Model:
        """
        Common Logic to create object under this seeder

        Args:
            data (dict): Data for object creation

        Returns:
            model instance created and persisted in database.
        """
        return ObjectCreator(
            self.model,
            data=data,
            unique_fields=self.unique_fields_map,
            objects_method=self._objects_method,
            atomic=self._atomic,
            seeder=self,
        )

    def pre_object_creation_hook(self):
        """
        Common hook executed before ``ObjectCreator``
        """

    def post_object_creation_hook(self):
        """
        Common hook executed after ``ObjectCreator``
        """

    # set_<field_name>
    def set_field_name(self, model_instance: "models.Model", field_name: str, field_value: typing.Any) -> None:
        """
        This is just a template method, Change field_name to you'r actuals field's name.
        """
