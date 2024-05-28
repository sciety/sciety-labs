from sciety_labs.app.routers.api.categorisation.providers import (
    get_categorisation_response_dict_for_opensearch_document_dict
)


class TestGetCategorisationDictForOpensearchDocumentDict:
    def test_should_return_empty_dict_if_no_categories_are_available(self):
        categories_dict = get_categorisation_response_dict_for_opensearch_document_dict({})
        assert categories_dict == {}  # pylint: disable=use-implicit-booleaness-not-comparison

    def test_should_extract_crossref_group_title_as_categories(self):
        categories_response_dict = get_categorisation_response_dict_for_opensearch_document_dict({
            'crossref': {
                'group_title': 'Category 1'
            }
        })
        assert categories_response_dict == {
            'data': [{
                'display_name': 'Category 1',
                'type': 'category',
                'source_id': 'crossref_group_title'
            }]
        }
