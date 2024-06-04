import logging
from datetime import date

from sciety_labs.providers.article_recommendation import (
    ArticleRecommendationFields,
    ArticleRecommendationFilterParameters
)
from sciety_labs.providers.opensearch.opensearch_article_recommendation import (
    ARTICLE_TITLE_OPENSEARCH_FIELDS,
    AUTHOR_LIST_OPENSEARCH_FIELDS,
    EVALUATION_COUNT_OPENSEARCH_FIELDS,
    PUBLISHED_DATE_OPENSEARCH_FIELDS,
    SUPPORTED_OPENSEARCH_FIELD_NAMES,
    get_article_meta_from_document,
    get_article_recommendation_from_document,
    get_from_publication_date_query_filter,
    get_source_includes,
    get_vector_search_query,
    iter_article_recommendation_from_opensearch_hits
)


LOGGER = logging.getLogger(__name__)

DOI_1 = "10.00000/doi_1"

VECTOR_1 = [1, 1, 1]


MINIMAL_DOCUMENT_DICT_1 = {
    'doi': DOI_1,
    's2': {
        'title': 'Title 1'
    }
}

DATE_1 = date.fromisoformat('2001-02-03')


class TestGetArticleMetaFromDocument:
    def test_should_create_article_meta_with_minimal_fields_from_s2(self):
        article_meta = get_article_meta_from_document(MINIMAL_DOCUMENT_DICT_1)
        assert article_meta.article_doi == MINIMAL_DOCUMENT_DICT_1['doi']
        assert article_meta.article_title == MINIMAL_DOCUMENT_DICT_1['s2']['title']

    def test_should_create_article_meta_with_minimal_fields_from_europepmc(self):
        article_meta = get_article_meta_from_document({
            'doi': DOI_1,
            'europepmc': {
                'title_with_markup': 'Title 1'
            }
        })
        assert article_meta.article_doi == DOI_1
        assert article_meta.article_title == 'Title 1'

    def test_should_create_article_meta_with_s2_authors(self):
        article_meta = get_article_meta_from_document({
            **MINIMAL_DOCUMENT_DICT_1,
            's2': {
                **MINIMAL_DOCUMENT_DICT_1['s2'],
                'author_list': [
                    {'name': 'Author 1'},
                    {'name': 'Author 2'}
                ]
            }
        })
        assert article_meta.author_name_list == ['Author 1', 'Author 2']

    def test_should_create_article_meta_with_europepmc_individual_and_collective_authors(self):
        article_meta = get_article_meta_from_document({
            'doi': DOI_1,
            'europepmc': {
                'title_with_markup': 'Title 1',
                'author_list': [{
                    'full_name': 'Author 1'
                }, {
                    'collective_name': 'Collective 1'
                }]
            }
        })
        assert article_meta.author_name_list == ['Author 1', 'Collective 1']

    def test_should_create_article_meta_with_publication_date(self):
        article_meta = get_article_meta_from_document({
            **MINIMAL_DOCUMENT_DICT_1,
            'europepmc': {
                'first_publication_date': '2001-02-03'
            }
        })
        assert article_meta.published_date == date(2001, 2, 3)

    def test_should_create_article_meta_with_crossref_metadata(self):
        article_meta = get_article_meta_from_document({
            'doi': DOI_1,
            'crossref': {
                'title_with_markup': 'Title 1',
                'publication_date': '2001-02-03',
                'author_list': [{
                    'family_name': 'Family1',
                    'given_name': 'Given1'
                }]
            }
        })
        assert article_meta.article_title == 'Title 1'
        assert article_meta.published_date == date(2001, 2, 3)
        assert article_meta.author_name_list == ['Given1 Family1']


class TestGetArticleRecommendationFromDocument:
    def test_should_not_include_stats_without_evaluation_count(self):
        recommendation = get_article_recommendation_from_document({
            **MINIMAL_DOCUMENT_DICT_1
        })
        assert recommendation.article_stats is None

    def test_should_include_evaluation_count_as_stats(self):
        recommendation = get_article_recommendation_from_document({
            **MINIMAL_DOCUMENT_DICT_1,
            'sciety': {
                'evaluation_count': 123
            }
        })
        assert recommendation.article_stats
        assert recommendation.article_stats.evaluation_count == 123

    def test_should_include_score_for_exactly_matching_vector(self):
        recommendation = get_article_recommendation_from_document({
            **MINIMAL_DOCUMENT_DICT_1,
            's2': {
                **MINIMAL_DOCUMENT_DICT_1['s2'],
                'embedding': [1, 1, 1]
            }
        }, embedding_vector_mapping_name='s2.embedding', query_vector=[1, 1, 1])
        assert round(recommendation.score, 2) == 1.0

    def test_should_include_score_for_not_exactly_matching_vector(self):
        recommendation = get_article_recommendation_from_document({
            **MINIMAL_DOCUMENT_DICT_1,
            's2': {
                **MINIMAL_DOCUMENT_DICT_1['s2'],
                'embedding': [0, 0, 1]
            }
        }, embedding_vector_mapping_name='s2.embedding', query_vector=[1, 1, 1])
        assert recommendation.score < 1.0


class TestIterArticleRecommendationFromOpenSearchHits:
    def test_should_yield_items_with_article_meta(self):
        recommendations = list(iter_article_recommendation_from_opensearch_hits([{
            '_source': {
                'doi': 'doi1',
                's2': {
                    'title': 'Title 1'
                }
            }
        }]))
        assert len(recommendations) == 1
        assert recommendations[0].article_doi == 'doi1'
        assert recommendations[0].article_meta.article_doi == 'doi1'

    def test_should_include_score_for_exactly_matching_nested_vector(self):
        recommendations = list(iter_article_recommendation_from_opensearch_hits([{
            '_source': {
                **MINIMAL_DOCUMENT_DICT_1,
                'parent': {
                    'embedding': [1, 1, 1]
                }
            }
        }], embedding_vector_mapping_name='parent.embedding', query_vector=[1, 1, 1]))
        assert len(recommendations) == 1
        recommendation = recommendations[0]
        assert round(recommendation.score, 2) == 1.0

    def test_should_not_include_score_if_nested_embedding_vector_is_not_available(self):
        recommendations = list(iter_article_recommendation_from_opensearch_hits([{
            '_source': {
                **MINIMAL_DOCUMENT_DICT_1
            }
        }], embedding_vector_mapping_name='parent.embedding', query_vector=[1, 1, 1]))
        assert len(recommendations) == 1
        recommendation = recommendations[0]
        assert recommendation.score is None


class TestGetFromPublicationDateQueryFilter:
    def test_should_return_filter_for_crossref_or_europepmc_publication_date(self):
        assert get_from_publication_date_query_filter(
             date.fromisoformat('2001-02-03')
        ) == {
            'bool': {
                'should': [{
                    'range': {
                        'crossref.publication_date': {'gte': '2001-02-03'}
                    }
                }, {
                    'range': {
                        'europepmc.first_publication_date': {'gte': '2001-02-03'}
                    }
                }]
            }
        }


class TestGetVectorSearchQuery:
    def test_should_include_query_vector(self):
        search_query = get_vector_search_query(
            query_vector=VECTOR_1,
            embedding_vector_mapping_name='embedding1',
            max_results=3,
            filter_parameters=ArticleRecommendationFilterParameters(
                evaluated_only=False
            )
        )
        assert search_query == {
            'size': 3,
            'query': {
                'knn': {
                    'embedding1': {
                        'vector': VECTOR_1,
                        'k': 3
                    }
                }
            }
        }

    def test_should_add_doi_filter(self):
        search_query = get_vector_search_query(
            query_vector=VECTOR_1,
            embedding_vector_mapping_name='embedding1',
            max_results=3,
            filter_parameters=ArticleRecommendationFilterParameters(
                exclude_article_dois={DOI_1},
                evaluated_only=False
            )
        )
        LOGGER.debug('search_query: %r', search_query)
        assert search_query == {
            'size': 3,
            'query': {
                'knn': {
                    'embedding1': {
                        'vector': VECTOR_1,
                        'k': 3,
                        'filter': {
                            'bool': {
                                'must_not': [{
                                    'ids': {'values': [DOI_1]}
                                }]
                            }
                        }
                    }
                }
            }
        }

    def test_should_add_from_publication_date_filter(self):
        search_query = get_vector_search_query(
            query_vector=VECTOR_1,
            embedding_vector_mapping_name='embedding1',
            max_results=3,
            filter_parameters=ArticleRecommendationFilterParameters(
                from_publication_date=DATE_1,
                evaluated_only=False
            )
        )
        assert search_query == {
            'size': 3,
            'query': {
                'knn': {
                    'embedding1': {
                        'vector': VECTOR_1,
                        'k': 3,
                        'filter': {
                            'bool': {
                                'must': [
                                    get_from_publication_date_query_filter(DATE_1)
                                ]
                            }
                        }
                    }
                }
            }
        }

    def test_should_add_evaluated_only_filter(self):
        search_query = get_vector_search_query(
            query_vector=VECTOR_1,
            embedding_vector_mapping_name='embedding1',
            max_results=3,
            filter_parameters=ArticleRecommendationFilterParameters(
                evaluated_only=True
            )
        )
        assert search_query == {
            'size': 3,
            'query': {
                'knn': {
                    'embedding1': {
                        'vector': VECTOR_1,
                        'k': 3,
                        'filter': {
                            'bool': {
                                'must': [{
                                    'range': {'sciety.evaluation_count': {'gte': 1}}
                                }]
                            }
                        }
                    }
                }
            }
        }

    def test_should_add_from_publication_date_and_evaluated_only_filter(self):
        search_query = get_vector_search_query(
            query_vector=VECTOR_1,
            embedding_vector_mapping_name='embedding1',
            max_results=3,
            filter_parameters=ArticleRecommendationFilterParameters(
                from_publication_date=DATE_1,
                evaluated_only=True
            )
        )
        assert search_query == {
            'size': 3,
            'query': {
                'knn': {
                    'embedding1': {
                        'vector': VECTOR_1,
                        'k': 3,
                        'filter': {
                            'bool': {
                                'must': [
                                    get_from_publication_date_query_filter(DATE_1),
                                    {'range': {'sciety.evaluation_count': {'gte': 1}}}
                                ]
                            }
                        }
                    }
                }
            }
        }


class TestGetSourceIncludes:
    def test_should_return_all_supported_fields_if_no_fields_specified(self):
        assert get_source_includes('embedding_vector_1') == (
            SUPPORTED_OPENSEARCH_FIELD_NAMES
            + ['embedding_vector_1']
        )

    def test_should_return_doi_only_if_only_doi_was_requested(self):
        assert get_source_includes(
            'embedding_vector_1',
            fields=[ArticleRecommendationFields.ARTICLE_DOI]
        ) == ['doi']

    def test_should_return_title_fields_only(self):
        assert get_source_includes(
            'embedding_vector_1',
            fields=[ArticleRecommendationFields.ARTICLE_TITLE]
        ) == ARTICLE_TITLE_OPENSEARCH_FIELDS

    def test_should_return_author_name_list_fields_only(self):
        assert get_source_includes(
            'embedding_vector_1',
            fields=[ArticleRecommendationFields.AUTHOR_NAME_LIST]
        ) == AUTHOR_LIST_OPENSEARCH_FIELDS

    def test_should_return_published_date_fields_only(self):
        assert get_source_includes(
            'embedding_vector_1',
            fields=[ArticleRecommendationFields.PUBLISHED_DATE]
        ) == PUBLISHED_DATE_OPENSEARCH_FIELDS

    def test_should_return_evaluation_count_fields_only(self):
        assert get_source_includes(
            'embedding_vector_1',
            fields=[ArticleRecommendationFields.EVALUATION_COUNT]
        ) == EVALUATION_COUNT_OPENSEARCH_FIELDS

    def test_should_return_score_fields_only(self):
        assert get_source_includes(
            'embedding_vector_1',
            fields=[ArticleRecommendationFields.SCORE]
        ) == ['embedding_vector_1']
