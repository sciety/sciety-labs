from datetime import date

from sciety_labs.providers.europepmc.async_providers import get_first_published_date_within_dates


class TestGetFirstPublishedDateWithinDates:
    def test_should_return_query_for_date_range(self):
        assert get_first_published_date_within_dates(
            date(2021, 1, 2),
            date(2022, 1, 2)
        ) == '(FIRST_PDATE:[2021-01-02 TO 2022-01-02])'
