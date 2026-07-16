import logging
import typing

from constance import config
from django.apps import apps
from django.core.exceptions import AppRegistryNotReady
from django.utils.module_loading import import_string

from apps.core.app_settings.base import BaseDescriptor

LOGGER = logging.getLogger(__name__)


class Constance(BaseDescriptor):

    @property
    def constance_key(self):
        if not hasattr(self, "name"):
            raise RuntimeError("Attribte `name` not found on descriptor")

        if not hasattr(self, "app_settings_name"):
            raise RuntimeError("Attribte `app_settings_name` not found on descriptor")

        return f"{self.name.upper()}_{self.app_settings_name.upper()}"

    def resolve(self, raw_value: typing.Any) -> typing.Any:
        """Resolve Constance, i.e. __get__ for constace returns what
        For constance it try getting the constance value from DB
        """
        constance_value = None  # default; set inside try, returned after except block

        try:
            constance_value = getattr(config, self.constance_key)
        except RuntimeError as tempExp:
            raise AttributeError(f"Invalid Descriptor: {str(tempExp)}")
        except AttributeError as attrError:
            LOGGER.error(msg=f"Constance Not found for {self.constance_key}", exc_info=attrError)
            # raise AttributeError(f"Constance Not found for {self.constance_key}")
        except Exception as e:
            raise e

        return constance_value


class DefferedModel(BaseDescriptor):

    def resolve(self, raw_value: str) -> type:
        """
        Resolve for a DjangoModel Imports, uses django's built-in helper to load models
        """
        _model = None

        try:
            _model = apps.get_model(raw_value)
        except AppRegistryNotReady as exc:
            LOGGER.error(msg=f"App not found >>> {raw_value}", exc_info=exc)
        except Exception as e:
            raise e

        return _model


class DefferedImport(BaseDescriptor):

    def resolve(self, raw_value: str) -> type:
        """
        Resolve for a DjangoModel Imports, uses django's built-in helper to load models
        """
        _kls = None
        try:
            _kls = import_string(raw_value)
        except ImportError as exc:
            LOGGER.error(msg=f"Class not found >>> {raw_value}", exc_info=exc)
        except Exception as e:
            raise e

        return _kls
