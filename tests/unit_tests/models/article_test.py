from datetime import datetime

from sciety_labs.models.article import (
    ArticleMention,
    get_doi_from_article_id_or_none,
    is_doi_article_id,
    is_preprint_doi
)


DOI_1 = '10.12345/doi_1'
DOI_2 = '10.12345/doi_2'

TIMESTAMP_1 = datetime.fromisoformat('2001-01-01+00:00')
TIMESTAMP_2 = datetime.fromisoformat('2001-01-02+00:00')


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


class TestIsPreprintDoi:
    def test_should_return_true_for_biorxiv_prefix(self):
        assert is_preprint_doi('10.1101/doi1') is True

    def test_should_return_false_for_elife_prefix(self):
        assert is_preprint_doi('10.7554/doi1') is False

    def test_should_return_true_for_scielo_preprints(self):
        assert is_preprint_doi('10.1590/SciELOPreprints.1234') is True

    def test_should_return_true_for_scielo_preprints_lowecase(self):
        assert is_preprint_doi('10.1590/scielopreprints.1234') is True

    def test_should_return_false_for_scielo_but_not_preprints(self):
        assert is_preprint_doi('10.1590/SciELO.1234') is False

    def test_should_return_true_for_osf_preprints_with_unknown_doi_prefix(self):
        assert is_preprint_doi('10.12345/osf.io/12345') is True

    def test_should_return_false_for_doi_prefix_not_supported_by_sciety(self):
        assert is_preprint_doi('10.20944/doi_1') is False


class TestArticleMention:
    def test_should_sort_by_created_timestamp(self):
        unsorted_list = [
            ArticleMention(
                article_doi=DOI_1,
                created_at_timestamp=TIMESTAMP_2
            ),
            ArticleMention(
                article_doi=DOI_2,
                created_at_timestamp=TIMESTAMP_1
            )
        ]
        sorted_list = sorted(unsorted_list, key=ArticleMention.get_created_at_sort_key)
        assert sorted_list == [unsorted_list[1], unsorted_list[0]]
