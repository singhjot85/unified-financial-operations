from __future__ import annotations

import typing

from django.conf import settings

T = typing.TypeVar("T")


class BaseDescriptor:
    """
    Abstract template-pattern descriptor

    Subclass implements `resolve(raw_value)`, this is a template that each descriptor is going to use.
    Override resolution (project_settings.<APP>_APP_SETTINGS -> default) is shared and lives
    here so every subclass gets it for free and consistently.
    """

    default: typing.Any
    help_text: str
    type_cast: typing.Any
    name: str  # Name of the settings attribute, Ex: MAX_RETRY_COUNT
    app_settings_name: str  # Name of the settings, Ex: CRMSettings
    data_type: type  # Data type for configured setting

    def __init__(
        self,
        default: typing.Any,
        help_text: str = "",
        data_type: typing.Union[type, list[type]] = None,
        *args,
        **kwargs,
    ):
        """
        Set Descriptor Attributes, each attribute has a different role going forward.

        Args:
           default (typing.Any): Default value of the setting
           help_text (str): Doc string explaining the setting, later will be used in django-admin
           data_type(type): Default class/protocol to type cast the setting

        """

        self.default = default
        self.data_type = data_type
        self.help_text = help_text
        self.default = default

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name
        self.app_settings_name = owner.__class__.__name__

    def __set__(self, instance: BaseSettings, value: typing.Any):
        """Settings are supposed to be changed at runtime,
        The only settings that suppotr this must, override this method.
        """
        raise AttributeError(
            f"{self.name!r} is read-only. Use project_settings."
            f"{instance.override_settings_name} or django.test.override_settings "
            f"to vary it, rather than assigning to it directly."
        )

    def __get__(self, instance: BaseSettings, owner: type):
        """
        NOTE: On Class.ATTRIBUTE, instance is none,
            and on object.ATTRIBUTE, instance is object/self.
        """
        if instance is None:
            # Class-level access returns the descriptor itself.
            # Required for introspection: the registry and validation walk descriptors, not resolved values.
            return self

        value = self.resolve(self.get_raw_value(instance))
        if self.data_type and not isinstance(value, self.data_type):
            raise TypeError(f"Invalid resolved data-type: {type(value)}, expected: {self.data_type}")

        return value

    def get_raw_value(self, instance: BaseSettings) -> typing.Any:
        """Get the resolved raw value of a setting, It gives priority to ``django.conf.settings``
        If ``django.conf.settings`` doesn't have this then the default value passed is used.

        This is where ``self.name`` saves us, as it was set using the ``__set_name__``,
        it's always present even before object creation.

        Args:
            instance (BaseSettings): Instance of the Settings class implementing the setting

        Returns:
            resolved raw setting value
        """
        overrides = getattr(settings, instance.override_settings_name, {})
        return overrides.get(self.name, self.default)

    def resolve(self, raw_value: typing.Any) -> typing.Any:
        """Per-type resolution hook. Must be implemented by subclasses.

        Args:
            raw_value (Any): Raw value that comes from project or app settings.

        Returns:
            resolved setting that ``app_settings.SETTING_NAME`` should return.
        """

        raise NotImplementedError(f"resolve not implemented for setting descriptor: {self.__class__.__name__}")


class SettingsMeta(type):
    """
    Metaclass for BaseSettings and all subclasses.

    This metaclass runs at class definition time to:
    1. Process the inner Meta class to determine the app_label/override key
    2. Collect all SettingType descriptors for later enumeration
    """

    @staticmethod
    def build_override_settings_name(name: str, metaclass: type):
        """
        Common method to build Override Settings Name.
        This name can be used in project_settings, to override app_settings.
        """
        override_settings_name = None

        if metaclass:
            app_label: str = getattr(metaclass, "app", None)
            if app_label and isinstance(app_label, str):
                override_settings_name = f"{app_label.upper()}_APP_SETTINGS"

        if override_settings_name:
            override_settings_name = f"{name.upper()}_APP_SETTINGS"

        return override_settings_name

    @staticmethod
    def build_descriptor_map(kls_attrs: dict) -> dict:
        """Build Decriptors map

        Returns:

            >>> { descriptor_name: descriptor }
        """
        _descriptor_map = {}

        for attr_name, attr_val in kls_attrs.items():
            if isinstance(attr_val, BaseDescriptor):
                _descriptor_map[attr_name] = attr_val

        return _descriptor_map

    def __new__(mcs, name, bases, attrs):
        """
        Oerriding ``__new__`` to return modified instance of class

        This new instance has a compiletime built atrribute on class ``override_settings_name``
        This will be the value that'll be used in ``project_settings`` to override given settings

        Example Usage:

        >>> {
            "OVERRIDE_SETTING_NAME": {
                "SETTING_NAME": Value
            }
        }
        """

        # Create the class
        cls = super().__new__(mcs, name, bases, attrs)

        cls.override_settings_name = SettingsMeta.build_override_settings_name(name, attrs.get("Meta", None))
        print("Registering App settings >>> ", cls.override_settings_name)  # noqa: T201

        cls._descriptors = SettingsMeta.build_descriptor_map(attrs)
        return cls


class BaseSettings(metaclass=SettingsMeta):
    """
    Base class for all app settings classes.

    Subclasses will automatically get:
    1. An override_settings_name based on their Meta.app
    2. A _descriptors dict containing all SettingType descriptors
    """

    # This will be set by the metaclass
    override_settings_name: str = ""
    _descriptors: dict = {}

    def __init__(self):
        """Initialize the settings instance."""
        # Any initialization needed for the settings instance

        pass

    def raw(self, setting_name: str) -> typing.Any:
        """Get raw value instead of the resolved one for given ``setting_name``<br/>

        Args:
            setting_name (str): Setting Name i.e. the atrribute name.

        Returns:
            raw value set in ``project_settings`` or the default value
        """
        descriptor: BaseDescriptor = self._descriptors.get(setting_name)
        if not descriptor:
            raise AttributeError(f"Setting '{setting_name}' not found")

        return descriptor.get_raw_value(self)

    @classmethod
    def get_descriptors(cls) -> dict:
        """
        Get all SettingType descriptors defined on this settings class.

        Returns:
            dict: Mapping of setting names to their descriptor instances
        """
        return cls._descriptors

    @classmethod
    def get_setting_names(cls) -> list:
        """
        Get the names of all settings defined on this class.

        Returns:
            list: Names of all settings
        """
        return list(cls._descriptors.keys())

    @classmethod
    def get_override_key(cls) -> str:
        """
        Get the key used to look up overrides in django.conf.settings.

        Returns:
            str: The override key (e.g., 'CRM_APP_SETTINGS')
        """
        return cls.override_settings_name
