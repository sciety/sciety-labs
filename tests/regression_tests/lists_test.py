

from requests import Session


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
