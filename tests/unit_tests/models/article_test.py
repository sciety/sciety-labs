from sciety_discovery.models.article import get_doi_from_article_id_or_none, is_doi_article_id


class TestIsDoiArticleId:
    def test_should_return_true_for_doi_colon_prefix(self):
        assert is_doi_article_id('doi:doi_1') is True

    def test_should_return_false_for_other_prefix(self):
        assert is_doi_article_id('other:value_1') is False

    def test_should_return_false_for_no_colon(self):
        assert is_doi_article_id('value_1') is False


class TestGetDoiFromArticleIdOrNone:
    def test_should_return_doi_for_article_id_with_doi_colon_prefix(self):
        assert get_doi_from_article_id_or_none('doi:doi_1') == 'doi_1'

    def test_should_return_none_for_other_prefix(self):
        assert get_doi_from_article_id_or_none('other:value_1') is None

    def test_should_return_none_for_no_colon(self):
        assert get_doi_from_article_id_or_none('value_1') is None
