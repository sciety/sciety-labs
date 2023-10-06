import logging
from datetime import date
from sciety_labs.providers.opensearch_article_recommendation import (
    get_article_meta_from_document,
    get_vector_search_query,
    iter_article_recommendation_from_opensearch_hits
)


LOGGER = logging.getLogger(__name__)

DOI_1 = "10.00000/doi_1"

VECTOR_1 = [1, 1, 1]


MINIMAL_DOCUMENT_DICT_1 = {
    'doi': 'doi1',
    'title': 'Title 1'
}


class TestGetArticleMetaFromDocument:
    def test_should_create_article_meta_with_minimal_fields(self):
        article_meta = get_article_meta_from_document(MINIMAL_DOCUMENT_DICT_1)
        assert article_meta.article_doi == MINIMAL_DOCUMENT_DICT_1['doi']
        assert article_meta.article_title == MINIMAL_DOCUMENT_DICT_1['title']

    def test_should_create_article_meta_with_authors(self):
        article_meta = get_article_meta_from_document({
            **MINIMAL_DOCUMENT_DICT_1,
            'authors': [
                {'name': 'Author 1'},
                {'name': 'Author 2'}
            ]
        })
        assert article_meta.author_name_list == ['Author 1', 'Author 2']

    def test_should_create_article_meta_with_publication_date(self):
        article_meta = get_article_meta_from_document({
            **MINIMAL_DOCUMENT_DICT_1,
            'publication_date': '2001-02-03'
        })
        assert article_meta.published_date == date(2001, 2, 3)


class TestIterArticleRecommendationFromOpenSearchHits:
    def test_should_yield_items_with_article_meta(self):
        recommendations = list(iter_article_recommendation_from_opensearch_hits([{
            '_source': {
                'doi': 'doi1',
                'title': 'Title 1'
            }
        }]))
        assert len(recommendations) == 1
        assert recommendations[0].article_doi == 'doi1'
        assert recommendations[0].article_meta.article_doi == 'doi1'


class TestGetVectorSearchQuery:
    def test_should_include_query_vector(self):
        search_query = get_vector_search_query(
            query_vector=VECTOR_1,
            embedding_vector_mapping_name='embedding1',
            max_results=3
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
            exclude_article_dois={DOI_1}
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
            from_publication_date=date.fromisoformat('2001-02-03')
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
                                    'range': {'publication_date': {'gte': '2001-02-03'}}
                                }]
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
            evaluated_only=True
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
                                    'range': {'evaluation_count': {'gte': 1}}
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
            from_publication_date=date.fromisoformat('2001-02-03'),
            evaluated_only=True
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
                                    'range': {'publication_date': {'gte': '2001-02-03'}}
                                }, {
                                    'range': {'evaluation_count': {'gte': 1}}
                                }]
                            }
                        }
                    }
                }
            }
        }
