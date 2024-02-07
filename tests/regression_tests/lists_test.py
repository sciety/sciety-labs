

from requests import Session

from tests.regression_tests.test_data import SCIETY_GROUP_LIST_ID_1, SCIETY_USER_LIST_ID_1


class TestListOfListPage:
    def test_should_load_user_lists_page(self, regression_test_session: Session):
        response = regression_test_session.get(
            '/lists/user-lists'
        )
        response.raise_for_status()

    def test_should_load_group_lists_page(self, regression_test_session: Session):
        response = regression_test_session.get(
            '/lists/group-lists'
        )
        response.raise_for_status()


class TestListPage:
    def test_should_load_user_list_page(self, regression_test_session: Session):
        response = regression_test_session.get(
            f'/lists/by-id/{SCIETY_USER_LIST_ID_1}'
        )
        response.raise_for_status()

    def test_should_load_group_list_page(self, regression_test_session: Session):
        response = regression_test_session.get(
            f'/lists/by-id/{SCIETY_GROUP_LIST_ID_1}'
        )
        response.raise_for_status()


class TestListRssPage:
    def test_should_load_user_list_rss_page(self, regression_test_session: Session):
        response = regression_test_session.get(
            f'/lists/by-id/{SCIETY_USER_LIST_ID_1}/atom.xml'
        )
        response.raise_for_status()

    def test_should_load_group_list_rss_page(self, regression_test_session: Session):
        response = regression_test_session.get(
            f'/lists/by-id/{SCIETY_GROUP_LIST_ID_1}/atom.xml'
        )
        response.raise_for_status()


class TestListRecommendationsPage:
    def test_should_load_user_list_page(self, regression_test_session: Session):
        response = regression_test_session.get(
            f'/lists/by-id/{SCIETY_USER_LIST_ID_1}/article-recommendations'
        )
        response.raise_for_status()

    def test_should_load_user_list_page_fragment(self, regression_test_session: Session):
        response = regression_test_session.get(
            f'/lists/by-id/{SCIETY_USER_LIST_ID_1}/article-recommendations',
            params={'fragment': True}
        )
        response.raise_for_status()

    def test_should_load_user_list_page_rss(self, regression_test_session: Session):
        response = regression_test_session.get(
            f'/lists/by-id/{SCIETY_USER_LIST_ID_1}/article-recommendations/atom.xml'
        )
        response.raise_for_status()

    def test_should_load_group_list_page(self, regression_test_session: Session):
        response = regression_test_session.get(
            f'/lists/by-id/{SCIETY_GROUP_LIST_ID_1}/article-recommendations'
        )
        response.raise_for_status()

    def test_should_load_group_list_page_fragment(self, regression_test_session: Session):
        response = regression_test_session.get(
            f'/lists/by-id/{SCIETY_GROUP_LIST_ID_1}/article-recommendations',
            params={'fragment': True}
        )
        response.raise_for_status()

    def test_should_load_group_list_page_rss(self, regression_test_session: Session):
        response = regression_test_session.get(
            f'/lists/by-id/{SCIETY_GROUP_LIST_ID_1}/article-recommendations/atom.xml'
        )
        response.raise_for_status()
