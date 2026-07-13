import abc
import typing


class AbstractPreferenceTypeValidator(abc.ABC):

    _metadata_fields: tuple

    # Model Fields
    preference_name: str
    data_type: str
    additional_meta_data: dict

    @abc.abstractmethod
    def validate_metadata(self, exclude=None) -> dict:
        """Validate CustomerPreferenceType MetaData and raise appropriate errors.

        Internally calls ``append_additional_meta_fields`` to append runtime
        additional fields to metadata JSON

        Returns:
            Cleaned MetaData dict
        """
        ...

    @abc.abstractmethod
    def set_metadata(self, is_multi: bool, label: str, default_value: typing.Any, choices: list = None) -> dict:
        """Setter for ``additional_meta_data`` JSON, Extend this setter if you add more fields

        Args:
            is_multi (bool): Is the Type a multi-select type.
            label (str): User friendly label for the type.
            default_values (Any): Default value for the preference.
            choices (list, optional): List of choices for the preference type. Defaults to None.

        Returns:
            metadata (dict): Metadata Constructed and updated to ``additional_meta_data``
        """
        ...

    def get_metadata(self) -> tuple:
        """Get all the meta data fields

        Returns:
            Tuple of all the value(s) extracted from ``additional_meta_data``
        """
        ...
