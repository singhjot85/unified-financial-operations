import inspect
import logging
import typing
from pathlib import Path

from django.db import models

from apps.core import app_settings
from apps.core.exceptions import ObjectCreatorException, SeederException
from apps.core.seeder.registries import model_seeder_registry
from apps.core.utils import camel_to_snake_case

if typing.TYPE_CHECKING:
    from django.db.models.fields.reverse_related import ManyToOneRel

    from .base import BaseSeeder

LOGGER = logging.getLogger(__name__)


class ObjectCreator:
    """
    Object Crating Helper, to create object's without needing a helper Create's one object at a time
    TODO: Re-implement _method, options:
    - delete_or_create (Delete previoius object and create a new one)
    - get_or_create (Works as ``update_or_create`` here)
    - plain create (Make duplicate's)

    Attributes:
        _model (type[Model]): Class for which the object is being created.
        _seeder (BaseSeeder): Seeder used to create the object.
        _data (dict): Seed data for curent instance under creation.
        _database (str): Database to create the object.
        _create_relations (bool): Create Foreign realtions or not.
        _model_meta (dict): Metadata (unique_fields,) for current object creation.
        _instance (Model): Created object, presisted as ObjecrCreator's attribute during entire lifecycle.
        _deep_creation (bool): Create Foreign relations recursively or not.

    ModelMeta Example:
        >>> {
            "unique_fields": ["username", "email"]
        }
    """

    _data: dict
    # _method: str
    _database: str = "default"
    _model: type["models.Model"]
    _seeder: type["BaseSeeder"]
    _create_relations: bool
    _model_meta: dict[str, typing.Any]
    _deep_creation: bool

    def __init__(
        self,
        model: type[models.Model],
        data: dict,
        # objects_method: str = SeederMethod.GET_OR_CREATE.value,
        database: str = None,
        metadata: dict = None,
        # atomic: bool = False,
        create_relations: bool = False,
        deep_creation: bool = False,
        seeder: "BaseSeeder" = None,
    ):
        """
        Object init method, valiates the input data, and sets defaults

        Args:
            model (Model): Model Class to be created.
            data (dict): Data for the model class to be created.
            database (str): Database to be used for object creation,
                default is ``default``.
            metadata (dict): Metadata for the model class to be created,
                default is ``None``
            create_relations (bool): Create Foreign relations or not,
                default is ``False``.
            seeder (BaseSeeder): Seeder used to create the object,
                default is ``None``.
        """
        self._model = model
        self._data = data
        # self._method = objects_method

        if not all(self._model, self._data):
            raise SeederException("Invalid ObjectCreator configuration")

        if database:
            self._database = database

        if metadata:
            self._model_meta = metadata

        self._create_relations = create_relations
        self._deep_creation = deep_creation

        from .utils import BaseSeeder

        self._seeder = seeder
        if self._seeder and not isinstance(self._seeder, BaseSeeder):
            raise SeederException("Invalid seeder provided")

    _instance: models.Model

    @property
    def seed_data(self) -> dict:
        if not self._data:
            return {}

        return self._data

    @property
    def instance(self) -> models.Model:
        """Model Object cached on ObjectCreator instace, for easier and object wide access"""
        if not self._instance:
            return self._init_instance()

        return self._instance

    def get_unique_fields(self, kls: type[models.Model]) -> list[str]:
        """
        Get unique fields required for ``get_or_create``, ``update_or_create``

        Args:
            kls (type[models.Model]): Name of the class for which
        """
        unique_fields = None
        if self._model_meta and (unique_fields := self._model_meta.get("unique_fields")):
            return unique_fields

        if (
            self._seeder
            and hasattr(self._seeder, "get_unique_fields")
            and (unique_fields := getattr("get_unique_fields")(kls))
        ):
            return unique_fields

        raise SeederException("unable to find unique fields")

    def _init_instance(self) -> models.Model:
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
            obj, created = self._model.objects.using(self._database).get_or_create(**filters)
            # NOTE: We cannot use ``update_or_create``, as we the entire lifecycle of ObjectCreator itself is update or create
            # ``get_or_create`` Get's a new/existing instance and we update each attribute individually.
            # method = getattr(self._model.objects.using(self._database), self._objects_method)
            # obj, created = method(**filters)
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

        setter_method_name = f"set_{field_name}"
        if self._seeder and hasattr(self._seeder, setter_method_name):
            return getattr(self._seeder, setter_method_name)(model_instance, field_name, field_value)

        return setattr(model_instance, field_name, field_value)

    def _create_object(self):
        """Create Object in database"""
        m2m_fields = {}

        model_fields: list[models.Field] = self._model._meta.get_fields(include_hidden=True)
        for field in model_fields:
            # If field not in data continue to next field
            field_name = field.name or getattr(field, "attname", None)
            if field_name not in self.seed_data:
                continue

            raw_value = self.seed_data.get(field_name, None)

            # Non-relation fields are set diectly
            if not field.is_relation:
                self.set_field_attribute(self.instance, field_name, self.seed_data.get(field_name))

            if not self._create_relations:
                continue

            # forawrd relation's i.e. whose .id lives in model's table, is also saved directly
            if field.many_to_one or field.one_to_one:
                self.process_foreign_relation(field, raw_value)

            # m2m fields are saved in a dict to be used later
            if field.many_to_many:
                m2m_fields[field.name] = self.seed_data.get(field.name)
                continue

            # m2m fields are saved in a dict to be used later
            if field.many_to_many:
                m2m_fields[field.name] = self.seed_data.get(field.name)
                continue

        if self._create_relations:
            self.instance.save(using=self._database)
            self.process_m2m_fields(m2m_fields)
            self.process_reverse_relations()
            return self.instance

    def process_foreign_relation(self, field: models.Field, raw_value: typing.Any):
        """
        Process Foreign keys, and save their data to a new instance.

        Args:
            field (Field): Model ForiegnKey Field to be created
            raw_value (Any): Value to be inserted in ForiegnKey Field.
        """
        field_name = field.name or getattr(field, "attname", None)
        if isinstance(raw_value, models.Model):
            return self.set_field_attribute(self.instance, field_name, raw_value)

        elif isinstance(raw_value, (dict, list)):
            # obj = ObjectCreator(model=instance.__class__, data=raw_value, unique_fields=self.get_unique_fields())
            obj = ObjectCreator(
                model=field.related_model,
                data=raw_value,
                create_relations=self._deep_creation,
                deep_creation=self._deep_creation,
                seeder=self._seeder,
            )
            return self.set_field_attribute(self.instance, field_name, obj)

        elif isinstance(raw_value, (int, str, type(None))):
            return self.set_field_attribute(self.instance, field_name, raw_value)

        raise ObjectCreatorException(f"Invalid value for Relation '{field_name}': {raw_value!r}")

    def process_reverse_relations(self):
        """
        Process reverse relations, and save their data to a new instance.
        Link the reverse relation to the current instance by setting the foreign key field in the related model.

        Raises:
            ObjectCreatorException: If the reverse relation data is invalid.
        """
        for rel in self.instance._meta.related_objects:
            rel: ManyToOneRel

            reverse_accessor_name = rel.get_accessor_name()
            if reverse_accessor_name not in self.seed_data:
                continue

            reverse_data = self.seed_data.get(reverse_accessor_name)
            ReverseModel = rel.related_model
            reverse_field_name = rel.field.name

            for item in reverse_data:
                if isinstance(item, models.Model):
                    # NOTE: in this case we have to update the item.reverse_field_name = self.instance
                    self.set_field_attribute(item, reverse_field_name, self.instance)
                    self.instance.save(using=self._database)
                elif isinstance(item, dict):
                    item[reverse_field_name] = self.instance
                    ObjectCreator(
                        model=ReverseModel,
                        data=item,
                        create_relations=self._deep_creation,
                        deep_creation=self._deep_creation,
                        seeder=self._seeder,
                    )
                elif isinstance(item, (int, str)):
                    obj = ReverseModel.objects.using(self._database).get(pk=item)
                    self.set_field_attribute(obj, reverse_field_name, self.instance)
                    obj.save(using=self._database)
                else:
                    raise SeederException(f"Invalid value for Reverese Relation '{reverse_accessor_name}': {item!r}")

    def process_m2m_fields(self, m2m_data: dict):
        """Process many-to-many fields,
        Fetch a related manager for m2m field and attach all objects to the instance using `manager.add`
        Attach object to instace means you create a (obj_id, instance_id) in the m2m table.

        Args:
            m2m_data (dict): Data for the m2m fields.

        Raises:
            ObjectCreationException
        """

        def _process_single_item(field: models.Field, data: typing.Any):
            """Process a single m2m item at once."""
            if isinstance(data, (models.Model, str, int)):
                return data
            elif isinstance(data, dict):
                return ObjectCreator(
                    model=field.related_model,
                    data=data,
                    create_relations=self._deep_creation,
                    deep_creation=self._deep_creation,
                    seeder=self._seeder,
                )

            raise ObjectCreatorException(f"Invalid M2M item: {item!r}")

        for field_name, raw_value in m2m_data.items():
            field: models.ManyToManyField = self.instance._meta.get_field(field_name)
            ManyManager = getattr(self.instance, field_name)

            ManyManager.clear()
            if not isinstance(raw_value, (list, tuple)):
                raw_value = (raw_value,)

            related_objs = []
            # Fetch all the related many objects in a single query, rather than one at a time
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

            ManyManager.add(*related_objs)

    def create_object(self):
        """Create Object in database"""
        LOGGER.info(msg=f"Creating object for model {self._model} with data: {self.seed_data}")

        if hasattr(self._seeder, "pre_object_creation_hook"):
            getattr(self._seeder, "pre_object_creation_hook")(self.seed_data)

        self._create_object()

        if hasattr(self._seeder, "post_object_creation_hook"):
            getattr(self._seeder, "post_object_creation_hook")(self.instance)

        LOGGER.info(msg=f"Created object for model {self._model} with data: {self.seed_data}")

        return self.instance


class SeederMixin:
    """
    Mixin class for Seeder, provides common methods to be used by all seeders.
    Ex: auto-discovery of fixture file path

    Attributes:
        _fallback_path (str): Fallback path for fixtures, if not found in the app
    """

    _fallback_path: str
    _fixtures_file: str

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

        global_fixtures = Path(cls._fallback_path)
        if not global_fixtures.exists():
            raise SeederException("Unable to find fixtures")

        fixtures_path = global_fixtures / f"{camel_to_snake_case(cls.__name__)}"

        if fixtures_path.exists():
            return file_path.absolute()

        raise SeederException("Unable to find fixtures")


class FixtureMixin(SeederMixin):
    """
    Fixtures are extension of SeederMixin, they provide common methods to be used by all seeders that are fixture as well
    Attributes:
        _fallback_path (str): Fallback path for fixtures, if not found in the app
        _fixtures_file (str): Path to the fixture file
    """

    _fallback_path: str = app_settings.GLOBAL_FIXTURE_DATA_PATH
    _fixtures_file: str

    @classmethod
    def seeder_name_to_search(cls):
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
            seeder = seeder_path.__getattribute__(cls.seeder_name_to_search())
        except AttributeError:
            global_seeders = Path(cls._fallback_path)
            if not global_seeders.exists():
                raise SeederException("Unable to find fixtures")

            seeder_path = global_seeders.glob("seeders.py")
            seeder = seeder_path.__getattribute__(cls.seeder_name_to_search())

        if not seeder:
            raise SeederException(f"No seeder found for name:{cls.seeder_name_to_search()}, please create one")

        return seeder
