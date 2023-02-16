def get_page_count_for_item_count_and_items_per_page(
    item_count: int,
    items_per_page: int
) -> int:
    return max(1, (item_count + items_per_page - 1) // items_per_page)
