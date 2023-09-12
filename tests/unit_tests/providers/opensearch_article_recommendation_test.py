from sciety_labs.providers.opensearch_article_recommendation import (
    get_article_meta_from_document,
    iter_article_recommendation_from_opensearch_hits
)


class TestGetArticleMetaFromDocument:
    def test_should_create_article_meta_with_minimal_fields(self):
        article_meta = get_article_meta_from_document({
            'doi': 'doi1',
            'title': 'Title 1'
        })
        assert article_meta.article_doi == 'doi1'
        assert article_meta.article_title == 'Title 1'


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
