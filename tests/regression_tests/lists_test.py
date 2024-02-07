

from requests import Session

from tests.regression_tests.test_data import GROUP_LIST_ID, USER_LIST_ID


class TestListsPage:
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
            f'/lists/by-id/{USER_LIST_ID}'
        )
        response.raise_for_status()

    def test_should_load_group_list_page(self, regression_test_session: Session):
        response = regression_test_session.get(
            f'/lists/by-id/{GROUP_LIST_ID}'
        )
        response.raise_for_status()
