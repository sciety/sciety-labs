from sciety_discovery.utils.pagination import get_page_count_for_item_count_and_items_per_page


class TestGetPageCountForItemCountAndItemsPerPage:
    def test_should_return_one_if_item_count_is_zero(self):
        assert get_page_count_for_item_count_and_items_per_page(
            item_count=0, items_per_page=10
        ) == 1

    def test_should_return_one_if_item_count_equals_items_per_page(self):
        assert get_page_count_for_item_count_and_items_per_page(
            item_count=10, items_per_page=10
        ) == 1

    def test_should_return_two_if_item_count_equals_items_per_page_plus_one(self):
        assert get_page_count_for_item_count_and_items_per_page(
            item_count=11, items_per_page=10
        ) == 2
