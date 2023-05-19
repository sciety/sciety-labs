from datetime import date
from sciety_labs.providers.semantic_scholar import (
    SEMANTIC_SCHOLAR_PAPER_ID_EXT_REF_ID,
    _get_recommendation_request_payload_for_article_dois,
    _iter_article_recommendation_from_recommendation_response_json
)


DOI_1 = '10.1101/doi1'

TITLE_1 = 'Title 1'

AUTHOR_NAME_1 = 'Author 1'
AUTHOR_NAME_2 = 'Author 2'

PAPER_ID_1 = 'paper1'


class TestGetRecommendationRequestPayloadForArticleDois:
    def test_should_return_request_with_prefixed_article_ids(self):
        assert _get_recommendation_request_payload_for_article_dois(
            [DOI_1]
        ) == {
            'positivePaperIds': [f'DOI:{DOI_1}'],
            'negativePaperIds': []
        }

    def test_should_truncate_article_doi_list_to_100(self):
        long_list_of_article_dois = [f'{DOI_1}_{_}' for _ in range(200)]
        assert len(_get_recommendation_request_payload_for_article_dois(
            long_list_of_article_dois
        )['positivePaperIds']) == 100


class TestIterArticleRecommendationFromRecommendationResponseJson:
    def test_should_extract_article_meta(self):
        article_recommendation_list = list(
            _iter_article_recommendation_from_recommendation_response_json({
                'recommendedPapers': [{
                    'externalIds': {
                        'DOI': DOI_1
                    },
                    'title': TITLE_1,
                    'publicationDate': '2001-02-03'
                }]
            })
        )
        assert [
            article_recommendation.article_meta.article_doi
            for article_recommendation in article_recommendation_list
        ] == [DOI_1]
        assert [
            article_recommendation.article_meta.article_title
            for article_recommendation in article_recommendation_list
        ] == [TITLE_1]
        assert [
            article_recommendation.article_meta.published_date
            for article_recommendation in article_recommendation_list
        ] == [date(2001, 2, 3)]

    def test_should_extract_authors(self):
        article_recommendation_list = list(
            _iter_article_recommendation_from_recommendation_response_json({
                'recommendedPapers': [{
                    'externalIds': {
                        'DOI': DOI_1
                    },
                    'title': TITLE_1,
                    'authors': [{
                        'name': AUTHOR_NAME_1
                    }, {
                        'name': AUTHOR_NAME_2
                    }]
                }]
            })
        )
        assert [
            article_recommendation.article_meta.author_name_list
            for article_recommendation in article_recommendation_list
        ] == [[AUTHOR_NAME_1, AUTHOR_NAME_2]]

    def test_should_ignore_recommendation_without_doi(self):
        article_recommendation_list = list(
            _iter_article_recommendation_from_recommendation_response_json({
                'recommendedPapers': [{
                    'externalIds': {
                        'Other': 'Other'
                    },
                    'title': TITLE_1
                }]
            })
        )
        assert not article_recommendation_list

    def test_should_ignore_recommendation_without_external_ids(self):
        article_recommendation_list = list(
            _iter_article_recommendation_from_recommendation_response_json({
                'recommendedPapers': [{
                    'title': TITLE_1
                }]
            })
        )
        assert not article_recommendation_list

    def test_should_extract_paper_id(self):
        article_recommendation_list = list(
            _iter_article_recommendation_from_recommendation_response_json({
                'recommendedPapers': [{
                    'externalIds': {'DOI': DOI_1},
                    'title': TITLE_1,
                    'paperId': PAPER_ID_1
                }]
            })
        )
        assert [
            article_recommendation.external_reference_by_name
            for article_recommendation in article_recommendation_list
        ] == [{SEMANTIC_SCHOLAR_PAPER_ID_EXT_REF_ID: PAPER_ID_1}]
