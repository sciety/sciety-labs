from typing import Any, Callable, TypeVar

T = TypeVar('T')


def get_recursively_filtered_dict_items_where_value(
    record: T,
    condition: Callable[[Any], bool]
) -> T:
    if isinstance(record, dict):
        first_pass_result = {
            key: get_recursively_filtered_dict_items_where_value(
                value,
                condition=condition
            )
            for key, value in record.items()
            if condition(value)
        }
        # second pass to remove anything that may not pass the condition after calling
        # the filter function
        return {  # type: ignore
            key: value
            for key, value in first_pass_result.items()
            if condition(value)
        }
    if isinstance(record, list):
        first_pass_result = [  # type: ignore
            get_recursively_filtered_dict_items_where_value(
                value,
                condition=condition
            )
            for value in record
            if condition(value)
        ]
        return [  # type: ignore
            value
            for value in first_pass_result
            if condition(value)
        ]
    return record


def get_recursively_filtered_dict_without_null_values(record: T) -> T:
    return get_recursively_filtered_dict_items_where_value(
        record,
        lambda value: value is not None
    )
