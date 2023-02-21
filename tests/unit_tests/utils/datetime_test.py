from datetime import datetime, timezone
from sciety_labs.utils.datetime import parse_timestamp


class TestParseTimestamp:
    def test_should_parse_timestamp_with_z_suffix(self):
        result = parse_timestamp('2001-02-03T04:05:06.000Z')
        assert result == datetime(2001, 2, 3, 4, 5, 6, tzinfo=timezone.utc)
