from sciety_labs.providers.crossref import (
    get_article_metadata_from_crossref_metadata
)


DOI_1 = '10.1101/doi1'


CROSSREF_RESPONSE_MESSAGE_1: dict = {
    'title': [],
    'author': []
}


class TestGetArticleMetadataFromCrossrefMetadata:
    def test_should_extract_single_line_title(self):
        result = get_article_metadata_from_crossref_metadata(
            DOI_1,
            {**CROSSREF_RESPONSE_MESSAGE_1, 'title': ['Title 1']}
        )
        assert result.article_title == 'Title 1'

    def test_should_extract_author_names_from_given_and_family_name(self):
        result = get_article_metadata_from_crossref_metadata(
            DOI_1,
            {
                **CROSSREF_RESPONSE_MESSAGE_1,
                'author': [{
                    'given': 'John',
                    'family': 'Smith'
                }]
            }
        )
        assert result.author_name_list == [
            'John Smith'
        ]

    def test_should_extract_author_names_from_name_field(self):
        result = get_article_metadata_from_crossref_metadata(
            DOI_1,
            {
                **CROSSREF_RESPONSE_MESSAGE_1,
                'author': [{
                    'name': 'John Smith Group'
                }]
            }
        )
        assert result.author_name_list == [
            'John Smith Group'
        ]
