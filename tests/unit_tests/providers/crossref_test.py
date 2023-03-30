from datetime import date
from sciety_labs.providers.crossref import (
    get_article_metadata_from_crossref_metadata,
    get_cleaned_abstract_html
)


DOI_1 = '10.1101/doi1'


CROSSREF_RESPONSE_MESSAGE_1: dict = {
    'title': [],
    'author': []
}


class TestGetCleanedAbstractHtml:
    def test_should_return_none_if_input_is_none(self):
        assert get_cleaned_abstract_html(None) is None

    def test_should_return_unchanged_input_without_html(self):
        assert get_cleaned_abstract_html('This is the abstract') == 'This is the abstract'

    def test_should_replace_single_jats_sec_element_with_section(self):
        assert (
            get_cleaned_abstract_html('<jats:sec>This is the abstract</jats:sec>')
         ) == '<section>This is the abstract</section>'

    def test_should_replace_multiple_jats_sec_elements_with_section(self):
        assert (
            get_cleaned_abstract_html(
                '<jats:sec>This is the section 1</jats:sec>'
                '<jats:sec>This is the section 2</jats:sec>'
            )
         ) == (
                '<section>This is the section 1</section>'
                '<section>This is the section 2</section>'
         )

    def test_should_remove_leading_title(self):
        assert (
            get_cleaned_abstract_html(
                '<jats:title>Abstract</jats:title>'
                '<jats:sec>This is the section 1</jats:sec>'
            )
         ) == (
                '<section>This is the section 1</section>'
         )


class TestGetArticleMetadataFromCrossrefMetadata:
    def test_should_extract_single_line_title(self):
        result = get_article_metadata_from_crossref_metadata(
            DOI_1,
            {**CROSSREF_RESPONSE_MESSAGE_1, 'title': ['Title 1']}
        )
        assert result.article_title == 'Title 1'

    def test_should_extract_abstract(self):
        result = get_article_metadata_from_crossref_metadata(
            DOI_1,
            {**CROSSREF_RESPONSE_MESSAGE_1, 'abstract': 'Abstract 1'}
        )
        assert result.abstract == 'Abstract 1'

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

    def test_should_extract_author_names_from_family_field_without_given_name(self):
        result = get_article_metadata_from_crossref_metadata(
            DOI_1,
            {
                **CROSSREF_RESPONSE_MESSAGE_1,
                'author': [{
                    'family': 'Smith'
                }]
            }
        )
        assert result.author_name_list == [
            'Smith'
        ]

    def test_should_extract_author_name_as_question_mark_without_valid_name_field(self):
        result = get_article_metadata_from_crossref_metadata(
            DOI_1,
            {
                **CROSSREF_RESPONSE_MESSAGE_1,
                'author': [{}]
            }
        )
        assert result.author_name_list == [
            '?'
        ]

    def test_should_extract_published_date(self):
        result = get_article_metadata_from_crossref_metadata(
            DOI_1,
            {
                **CROSSREF_RESPONSE_MESSAGE_1,
                'published': {'date-parts': [[2001, 2, 3]]}
            }
        )
        assert result.published_date == date(2001, 2, 3)
