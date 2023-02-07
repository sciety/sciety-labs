from sciety_discovery.providers.twitter import (
    get_doi_from_url_or_none,
    iter_twitter_article_list_item_for_user_tweets_response
)


DOI_1 = '10.1101/doi1'

DOI_ORG_URL_PREFIX = 'https://doi.org/'
DOI_ORG_URL_1 = DOI_ORG_URL_PREFIX + DOI_1


class TestGetDoiFromUrlOrNone:
    def test_should_return_none_if_not_url_containing_doi(self):
        assert get_doi_from_url_or_none('https://example.org') is None

    def test_should_ignore_doi_not_starting_with_10_1101(self):
        assert get_doi_from_url_or_none(DOI_ORG_URL_PREFIX + '10.9999/doi1') is None

    def test_should_return_doi_from_doi_org_url(self):
        assert get_doi_from_url_or_none(DOI_ORG_URL_1) == DOI_1

    def test_should_strip_version_from_biorxiv_url(self):
        assert get_doi_from_url_or_none(
            f'https://www.biorxiv.org/content/{DOI_1}v1'
        ) == DOI_1


class TestIterTwitterArticleListItemForUserTweetsResponse:
    def test_return_empty_response_for_empty_timeline(self):
        result = list(iter_twitter_article_list_item_for_user_tweets_response({
            'data': []
        }))
        assert not result

    def test_return_empty_response_for_item_without_entities_timeline(self):
        result = list(iter_twitter_article_list_item_for_user_tweets_response({
            'data': [{}]
        }))
        assert not result

    def test_return_article_list_item_for_expanded_doi_org_url(self):
        result = list(iter_twitter_article_list_item_for_user_tweets_response({
            'data': [{
                'entities': {
                    'urls': [{
                        'expanded_url': DOI_ORG_URL_1
                    }]
                }
            }]
        }))
        assert [item.article_doi for item in result] == [DOI_1]
