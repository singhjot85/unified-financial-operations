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

    default: typing.Any  # Default value of the setting
    help_text: str  # Doc string explaining the setting, later will be used in django-admin
    type_cast: typing.Any  # Default class/protocol to type cast the setting
    name: str  # Name of the settings class

    def __init__(self, default: typing.Any, help_text: str = "", type_cast=None):
        """Set Descriptor Attributes, each attribute has a different role going forward."""

        self.default = default
        self.help_text = help_text
        self.default = default

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

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
        if self.type_cast:
            value = self.type_cast(value)
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


class BaseSettings:
    pass
