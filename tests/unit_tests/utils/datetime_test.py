from datetime import datetime, timezone
from sciety_labs.utils.datetime import (
    get_date_as_display_format,
    get_date_as_isoformat,
    parse_timestamp
)


class TestParseTimestamp:
    def test_should_parse_timestamp_with_z_suffix(self):
        result = parse_timestamp('2001-02-03T04:05:06.000Z')
        assert result == datetime(2001, 2, 3, 4, 5, 6, tzinfo=timezone.utc)


class TestGetDateAsIsoformat:
    def test_should_return_return_none_if_passed_in_date_is_none(self):
        assert get_date_as_isoformat(None) is None

    def test_should_return_formatted_date_string(self):
        assert get_date_as_isoformat(parse_timestamp('2001-02-03+00:00')) == '2001-02-03'


class TestGetDateAsDisplayformat:
    def test_should_return_return_none_if_passed_in_date_is_none(self):
        assert get_date_as_display_format(None) is None

    def test_should_return_formatted_date_string(self):
        assert get_date_as_display_format(parse_timestamp('2001-02-03+00:00')) == 'Feb 3, 2001'
