from sciety_labs.utils.mapping import (
    get_flat_all_values_for_mapping,
    get_flat_mapped_values_for_mapping
)


class TestGetFlatMappedValuesForMapping:
    def test_should_return_flat_mapped_values(self):
        assert get_flat_mapped_values_for_mapping(
            {
                'key1': ['value1.1', 'value1.2'],
                'key2': ['value2.1', 'value2.2'],
                'key3': ['value3.1', 'value3.2']
            },
            keys=['key1', 'key2']
        ) == [
            'value1.1', 'value1.2', 'value2.1', 'value2.2'
        ]


class TestGetFlatAllValuesForMapping:
    def test_should_return_flat_mapped_values(self):
        assert get_flat_all_values_for_mapping(
            {
                'key1': ['value1.1', 'value1.2'],
                'key2': ['value2.1', 'value2.2'],
                'key3': ['value3.1', 'value3.2']
            }
        ) == [
            'value1.1', 'value1.2', 'value2.1', 'value2.2', 'value3.1', 'value3.2'
        ]
