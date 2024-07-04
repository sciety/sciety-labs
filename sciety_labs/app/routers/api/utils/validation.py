from typing import Iterable, Set


class InvalidApiFieldsError(ValueError):
    def __init__(
        self,
        invalid_field_names: Set[str],
        query_parameter_name: str
    ):
        self.invalid_field_names = invalid_field_names
        self.query_parameter_name = query_parameter_name


def validate_api_fields(
    fields_set: Set[str],
    valid_values: Iterable[str],
    query_parameter_name: str
):
    invalid_field_names = fields_set - set(valid_values)
    if invalid_field_names:
        raise InvalidApiFieldsError(
            invalid_field_names=invalid_field_names,
            query_parameter_name=query_parameter_name
        )
