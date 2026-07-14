import typing

from apps.crm.abstacts import AbstractPreferenceTypeValidator
from apps.crm.constants import PreferenceDataTypeChoices


class PreferenceTypeValidator(AbstractPreferenceTypeValidator):
    """Default Validator used by preference-type, This can be overriden in app_settings, as per-need

    TODO: Name validator is misleading, it does much more, think of something better
    """

    key_multi_type: str = "is_multi_type"
    key_label: str = "label"
    key_default: str = "default_value"
    key_choices: str = "choices"

    _metadata_fields: tuple = (key_multi_type, key_label, key_default)

    # Model Fields
    preference_name: str
    data_type: str
    additional_meta_data: dict

    def get_fallback_default_value(self) -> typing.Any:
        """Get Default/Fallback value for default_value JSON key"""

        if self.data_type == PreferenceDataTypeChoices.BOOLEAN.value:
            return False
        elif self.data_type in [PreferenceDataTypeChoices.CHOICES.value, PreferenceDataTypeChoices.STRING.value]:
            return ""
        elif self.data_type == PreferenceDataTypeChoices.INTEGER.value:
            return 0

        return None

    # -----------------------------------------------
    # Simple Clean Hooks, making sure data consistency
    # Override these hook for any complex clean logic
    # -----------------------------------------------
    def clean_is_multi_type(self, val) -> bool:
        """Clean method of is_multi_type field on additional_meta_data JSON"""
        return bool(val)

    def clean_label(self, val) -> str:
        """Clean method of label field on additional_meta_data JSON"""
        return val if val and isinstance(val, str) else self.preference_name

    def clean_default_value(self, val) -> typing.Any:
        """Clean method of default_values field on additional_meta_data JSON"""
        return val if val else self.get_fallback_default_value()

    def clean_choices(self, val) -> list:
        """Clean method of choices field on additional_meta_data JSON"""
        return val if val and isinstance(val, list) else []

    def append_additional_meta_fields(self) -> list:
        """Append Condition based additional fields to metadata JSON

        Returns:
            list of updated metadata fields, return type kept to list
                so overriding is not too much verbose
        """

        original_metadata_fields = list(self._metadata_fields)

        if self.data_type == PreferenceDataTypeChoices.CHOICES.value:
            original_metadata_fields.append(self.key_choices)

        self._metadata_fields = tuple(original_metadata_fields)
        return original_metadata_fields

    def validate_metadata(self) -> dict:
        """Validate CustomerPreferenceType MetaData and raise appropriate errors.

        Validates:
            is_multi_type: Is present and of valid type.
            label: Is present and of valid_type(s).
            defaults: Is present and of valid_type(s).

        Returns:
            Cleaned MetaData dict
        """
        self.append_additional_meta_fields()

        inital_metadata = self.additional_meta_data or {}
        cleaned_metadata = {}

        for field_key in self._metadata_fields:
            clean_method_name = f"clean_{field_key}"
            if hasattr(self, clean_method_name):

                original_value = inital_metadata.get(field_key)
                cleaned_value = getattr(self, clean_method_name)(original_value)

                cleaned_metadata.update({field_key: cleaned_value})

        return cleaned_metadata

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
        metatdata = {self.key_multi_type: is_multi, self.key_label: label, self.key_default: default_value}
        if choices:
            metatdata.update({self.key_choices: choices})

        self.additional_meta_data = metatdata

        return metatdata

    def get_metadata(self) -> tuple:
        """Get all the meta data fields

        Returns:
            is_multi_type (bool): Is the Type a multi-select type.
            label (str): User friendly label for the type.
            default_values (Any): Default value for the preference.
        """
        fallback_default_value = self.get_fallback_default_value()
        ret = [
            self.additional_meta_data.get(self.key_multi_type, False),
            self.additional_meta_data.get(self.key_label, self.preference_name),
            self.additional_meta_data.get(self.key_default, fallback_default_value),
        ]

        if self.data_type == PreferenceDataTypeChoices.CHOICES.value:
            ret.append(self.additional_meta_data.get(self.key_choices, []))

        return tuple(ret)
