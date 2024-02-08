

import pytest
from requests import Session

from tests.regression_tests.test_data import SCIETY_GROUP_LIST_ID_1, SCIETY_USER_LIST_ID_1


@pytest.fixture(name='sciety_list_id', params=[
    SCIETY_GROUP_LIST_ID_1,
    SCIETY_USER_LIST_ID_1
])
def _sciety_list_id(request: pytest.FixtureRequest) -> str:
    return request.param


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
    def test_should_load_list_page(
        self,
        regression_test_session: Session,
        sciety_list_id: str
    ):
        response = regression_test_session.get(
            f'/lists/by-id/{sciety_list_id}'
        )
        response.raise_for_status()


class TestListRssPage:
    def test_should_load_list_rss_page(
        self,
        regression_test_session: Session,
        sciety_list_id: str
    ):
        response = regression_test_session.get(
            f'/lists/by-id/{sciety_list_id}/atom.xml'
        )
        response.raise_for_status()


class TestListRecommendationsPage:
    def test_should_load_user_list_page(
        self,
        regression_test_session: Session,
        sciety_list_id: str
    ):
        response = regression_test_session.get(
            f'/lists/by-id/{sciety_list_id}/article-recommendations'
        )
        response.raise_for_status()

    def test_should_load_list_page_fragment(
        self,
        regression_test_session: Session,
        sciety_list_id: str
    ):
        response = regression_test_session.get(
            f'/lists/by-id/{sciety_list_id}/article-recommendations',
            params={'fragment': True}
        )
        response.raise_for_status()

    def test_should_load_user_list_page_rss(
        self,
        regression_test_session: Session,
        sciety_list_id: str
    ):
        response = regression_test_session.get(
            f'/lists/by-id/{sciety_list_id}/article-recommendations/atom.xml'
        )
        response.raise_for_status()
