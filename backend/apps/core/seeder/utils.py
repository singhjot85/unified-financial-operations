import inspect
import logging
import typing
from pathlib import Path

from django.db import models, transaction

from apps.core import app_settings
from apps.core.constants import SeederMethod
from apps.core.exceptions import (
    InvalidTypeError,
    ObjectCreatorException,
    SeederException,
)
from apps.core.seeder.registries import model_seeder_registry
from apps.core.utils import camel_to_snake_case

if typing.TYPE_CHECKING:
    from django.db.models.fields.reverse_related import ManyToOneRel

    from .base import BaseSeeder

LOGGER = logging.getLogger(__name__)


class ObjectCreator:
    _unique_fields_map: dict[str, list]
    _objects_method: str

    _database: str
    _model: type[models.Model]
    _model_obj: models.Model
    _seed_data: typing.Union[dict, dict]

    pre_creation_hook_name: str = "pre_object_creation_hook"
    post_creation_hook_name: str = "post_object_creation_hook"
    object_metadata: dict

    def __init__(
        self,
        model: type[models.Model],
        data: typing.Union[dict, list],
        unique_fields_map: list[dict] = None,
        objects_method: str = SeederMethod.GET_OR_CREATE.value,
        database: str = "default",
        atomic: bool = False,
        seeder: "BaseSeeder" = None,
    ):

        if not model:
            raise ObjectCreatorException("Model is required field to create an object")
        if not data:
            raise ObjectCreatorException("Data is required to create an object")

        data = self.validate_data(data)

        self._unique_fields_map = unique_fields_map
        # if not self._unique_fields:
        #     raise ImproperlyConfigured("BaseObjectCreation instance doesn't have unique fields defined.")

        self._objects_method = objects_method
        self._database = database
        self.seeder = seeder

        for _data in data:
            self._seed_data = _data
            self.create_object(atomic)

    def validate_data(self, data) -> list:
        """
        Validate structure of provided data, and convert it to list at last
        """

        if isinstance(data, dict):
            data = [data]

        if not isinstance(data, list):
            raise InvalidTypeError(type=type(data), expected="dict/list")

        return data

    @property
    def seed_data(self) -> dict:
        if not self._seed_data:
            return {}

        return self._seed_data

    @property
    def instance(self) -> models.Model:
        """Model Object cached on ObjectCreator instace, for easier and object wide access"""
        if not self._model_obj:
            return self._init_obj()

        return self._model_obj

    def get_unique_fields(self, kls: type[models.Model]) -> list[str]:
        """
        Get unique fields required for ``get_or_create``, ``update_or_create``

        Args:
            kls (type[models.Model]): Name of the class for which
        """
        unique_fields = self.get_unique_fields_map().get(kls, [])

        if not unique_fields:
            raise SeederException("unable to find unique fields")

        return unique_fields

    def _init_obj(self) -> models.Model:
        """Initialize an in-memory object

        Returns:
            instance (Model): In-memory object of given model class.
        """
        filters = None
        if pk := self.seed_data.get("pk", self.seed_data.get("id", None)):
            filters = {"pk": pk}
        else:
            filters = self.get_unique_fields(self._model)

        if not filters:
            return self._model()

        try:
            method = getattr(self._model.objects.using(self._database), self._objects_method)
            obj, created = method(**filters)
            if not created:
                LOGGER.info(
                    msg=f"using existing object for model {self._model} instead of creating new, obj: {str(obj)}"
                )
        except Exception as e:
            LOGGER.error(msg=f"Error filtering object, because of exception: {str(e)}", exc_info=e)

    def set_field_attribute(self, model_instance: models.Model, field_name: str, field_value: typing.Any) -> None:
        """
        Some fields like User.password, file_fields shouldn't be set directly using setattr
        They need their own seperate logic, this method gives us freedom for that

        Args:
            model_instance (models.Model): Current object under execution.
            field_name (str): Name of the field.
            value (Any): Data for that field from entire data object.
        """
        from .utils import BaseSeeder

        setter_method_name = f"set_{field_name}"
        if self.seeder and isinstance(self.seeder, BaseSeeder) and hasattr(self.seeder, setter_method_name):
            return getattr(self.seeder, setter_method_name)(model_instance, field_name, field_value)

        return setattr(model_instance, field_name, field_value)

    def _create_object(self):
        """Create Object in database"""
        m2m_fields = {}

        model_fields: list[models.Field] = self._model._meta.get_fields(include_hidden=True)
        for field in model_fields:
            # If field not in data continue to next field
            attname = getattr(field, "attname", None)
            if field.name not in self.seed_data and (attname is None or attname not in self.seed_data):
                continue

            # Non-relation fields are set diectly
            if not field.is_relation:
                self.set_field_attribute()

            # forawrd relation's i.e. whose .id lives in model's table, is also saved directly
            if field.many_to_one or field.one_to_one:
                raw_value = self.seed_data.get(field.name, self.seed_data.get(attname) if attname else None)
                self.process_foreign_relation(self.instance, (field.name or field.attname), raw_value)

            # m2m fields are saved in a dict to be used later
            if field.many_to_many:
                m2m_fields[field.name] = self.seed_data.get(field.name)
                continue

            # m2m fields are saved in a dict to be used later
            if field.many_to_many:
                m2m_fields[field.name] = self.seed_data.get(field.name)
                continue

        self.instance.save(using=self._database)
        self.process_m2m_fields(self.instance, m2m_fields)
        self.process_reverse_relations(self.instance)
        return self.instance

    def process_foreign_relation(self, instance: models.Model, field_name: str, raw_value: typing.Any):
        """
        Common method to process data for all relation's
        May it be forward, reverese, one-one, many-many
        """
        if isinstance(raw_value, models.Model):
            return self.set_field_attribute(instance, field_name, raw_value)

        elif isinstance(raw_value, (dict, list)):
            obj = ObjectCreator(model=instance.__class__, data=raw_value, unique_fields=self.get_unique_fields())
            return self.set_field_attribute(instance, field_name, obj)

        elif isinstance(raw_value, (int, str, type(None))):
            return self.set_field_attribute(instance, field_name, raw_value)

        raise ObjectCreatorException(f"Invalid value for Relation '{field_name}': {raw_value!r}")

    def process_reverse_relations(self, instance: models.Model):

        for rel in instance._meta.related_objects:
            rel: ManyToOneRel

            accessor = rel.get_accessor_name()
            if accessor not in self.seed_data:
                continue

            reverse_data = self.validate_data(self.seed_data.get(accessor))

            related_model = rel.related_model
            related_field_name = rel.field.name

            for item in reverse_data:
                if isinstance(item, models.Model):
                    # setattr(item, fk_field_name, instance)
                    self.set_field_attribute(item, related_field_name, instance)
                    instance.save(using=self._database)

                elif isinstance(item, dict):
                    item[related_field_name] = instance
                    ObjectCreator(related_model, data=item, unique_fields=self.get_unique_fields(related_model))

                    self._create_object(kls=related_model, data=item)

                elif isinstance(item, (int, str)):
                    obj = related_model.objects.using(self._database).get(pk=item)
                    # setattr(obj, fk_field_name, instance)
                    self.set_field_attribute(obj, related_field_name, instance)
                    obj.save(using=self._database)

    def process_m2m_fields(self, instance: models.Model, m2m_data: dict):
        """Process many-to-many fields, fetch a related manager for m2m field and attach all objects to the instance using `manager.add`
        Attach object to instace means u create a (obj_id, instance_id) in the m2m table.

        Args:
            instance: (models.Model): Model object on which the m2m fields are to be attached.
            m2m_data (dict): Data for the m2m fields.

        Raises:
            ObjectCreationException
        """

        def _process_single_item(field: models.Field, data: typing.Any):
            """Process a single m2m item at once."""
            if isinstance(data, (models.Model, str, int)):
                return data
            elif isinstance(data, dict):
                # return self._create_object(kls=field.related_model, data=data)
                return ObjectCreator(
                    model=field.related_model, data=data, unique_fields=self.get_unique_fields(field.related_model)
                )

            raise ObjectCreatorException(f"Invalid M2M item: {item!r}")

        for field_name, raw_value in m2m_data.items():
            field: models.ManyToManyField = instance._meta.get_field(field_name)
            manager = getattr(instance, field_name)

            manager.clear()
            if not isinstance(raw_value, (list, tuple)):
                raw_value = (raw_value,)

            related_objs = []
            related_objs_to_fetch = []
            for item in raw_value:
                obj = _process_single_item(field, item)
                if isinstance(obj, (str, int)):
                    related_objs_to_fetch.append(obj)
                else:
                    related_objs.append(obj)

            if related_objs_to_fetch:
                objs = field.related_model.objects.filter(pk__in=related_objs_to_fetch)
                for obj in objs:
                    related_objs.append(obj)

            manager.add(*related_objs)

    def get_unique_fields_map(self) -> dict:
        """
        Get map of unique fields for ``get_or_create``, ``update_or_create``
        The map should contain unique fields for both model and its foreign relation
        unique fields for foreign relation can be avoided if its not being created/seeded.

        Example:

        >>> {
                "Users": ["username", "email"],
                "Customer": ["email"]
            }
        """
        if self._unique_fields_map:
            return self._unique_fields_map

        return self.object_metadata.get("unique_fields_map", {})

    def pre_object_creation_hook(self):
        """Execute any pre_hooks on seeder and then execute current logic."""
        if self.seeder and hasattr(self.seeder, self.pre_creation_hook_name):
            getattr(self.seeder, self.pre_creation_hook_name)()

        # pop the _meta from object metadata
        self.object_metadata = self.seed_data.pop("_meta", {})

    def create_object(self, atomic: bool):
        """Wrapper to execute creation lifecycle"""
        LOGGER.debug("Starting object creation for >>> %s", self._model.__name__)

        if atomic:
            with transaction.atomic():
                self.pre_object_creation_hook()
                LOGGER.debug("[Atomic] pre-hook successfull for >>> %s", self._model.__name__)

                self._create_object()
                LOGGER.debug("[Atomic] object creation successfull for >>> %s", self._model.__name__)

                self.post_object_creation_hook()
                LOGGER.debug("[Atomic] post-hook successfull for >>> %s", self._model.__name__)
        else:
            self.pre_object_creation_hook()
            LOGGER.debug("[Non-Atomic] pre-hook successfull for >>> %s", self._model.__name__)

            self._create_object()
            LOGGER.debug("[Non-Atomic] object creation successfull for >>> %s", self._model.__name__)

            self.post_object_creation_hook()
            LOGGER.debug("[Non-Atomic] post-hook successfull for >>> %s", self._model.__name__)

    def post_object_creation_hook(self):
        """Execute any post_seeder on seeder and then execute current logic."""

        if self.seeder and hasattr(self.seeder, self.post_creation_hook_name):
            getattr(self.seeder, self.post_creation_hook_name)()


class SeederAutoDiscovery:
    _global_fixture_directory: str = app_settings.GLOBAL_FIXTURE_PATH

    @classmethod
    def get_seeder_name(cls):
        """Getter to generate seeder's name, override in base class for custom seeder names."""
        raise NotImplementedError("No implementation to auto-discover seeder name")

    @classmethod
    def auto_discover_model_seeder(cls):
        """
        This auto-discovery routine discover's the model's fixture file path.

        Expected Directory Structure:

        ```
        app_name/
            |- models.py
            |- fixtures/
            |   |- seeders.py
        ```
        """
        file_path = Path(inspect.getfile(cls))
        directory = file_path.parent  # Directory containing the subclass
        fixtures_path = directory / "fixtures"

        seeder = None
        try:
            seeder_path = fixtures_path.glob("seeders.py")
            seeder = seeder_path.__getattribute__(cls.get_seeder_name())
        except AttributeError:
            global_seeders = Path(cls._global_fixture_directory)
            if not global_seeders.exists():
                raise SeederException("Unable to find fixtures")

            seeder_path = global_seeders.glob("seeders.py")
            seeder = seeder_path.__getattribute__(cls.get_seeder_name())

        if not seeder:
            raise SeederException(f"No seeder found for name:{cls.get_seeder_name()}, please create one")

        return seeder

    @classmethod
    def auto_discover_fixtures_directory(cls):
        """
        This auto-discovery routine discover's the model's fixture file path.

        Expected Directory Structure:

        ```
        app_name/
            |- models.py
            |- fixtures/
            |   |- model_name.json
        ```
        """
        file_path = Path(inspect.getfile(cls))
        directory = file_path.parent  # Directory containing the subclass
        fixtures_path = directory / "fixtures" / f"{camel_to_snake_case(cls.__name__)}"

        if fixtures_path.exists():
            return file_path.absolute()

        global_fixtures = Path(cls._global_fixture_directory)
        if not global_fixtures.exists():
            raise SeederException("Unable to find fixtures")

        fixtures_path = global_fixtures / f"{camel_to_snake_case(cls.__name__)}"

        if fixtures_path.exists():
            return file_path.absolute()

        raise SeederException("Unable to find fixtures")


class FixtureMixin(SeederAutoDiscovery):
    _fixtures_file: str

    @classmethod
    def get_seeder_name(cls):
        """Getter to generate seeder's name, override in base class for custom seeder names."""
        return f"{cls.__name__}Seeder"

    def __init_subclass__(cls):
        try:
            seeder = cls.auto_discover_model_seeder()
            model_seeder_registry.register(seeder, key=camel_to_snake_case(cls.__name__))
        except Exception as e:
            raise SeederException(f"Error registering model: {cls.__name__},in registry") from e

        try:
            cls._fixtures_file = cls.auto_discover_fixtures_directory()
        except Exception as e:
            raise SeederException(f"Error in fixture auto-discovery for class: {cls.__name__}") from e
