from sciety_discovery.models.lists import (
    ScietyEventListsModel
)


LIST_ID_1 = 'list_1'
LIST_ID_2 = 'list_2'


SCIETY_LIST_1 = {
    'list_id': LIST_ID_1,
    'list_name': 'List Name 1',
    'list_description': 'List Description 1'
}

USER_ID_1 = 'user_1'

SCIETY_USER_1 = {
    'user_id': USER_ID_1,
    'avatar_url': 'https://user-avatar/1'
}


class TestScietyEventListsModel:
    def test_should_return_empty_list_for_no_events(self):
        model = ScietyEventListsModel([])
        assert not model.get_most_active_user_lists()

    def test_should_populate_list_id_and_list_meta_fields(self):
        model = ScietyEventListsModel([{
            'event_name': 'ArticleAddedToList',
            'sciety_list': SCIETY_LIST_1,
            'sciety_user': SCIETY_USER_1
        }, {
            'event_name': 'ArticleAddedToList',
            'sciety_list': SCIETY_LIST_1,
            'sciety_user': SCIETY_USER_1
        }])
        result = model.get_most_active_user_lists()
        assert [
            {
                'list_id': item['list_id'],
                'list_title': item['list_title'],
                'list_description': item['list_description']
            }
            for item in result
        ] == [{
            'list_id': LIST_ID_1,
            'list_title': SCIETY_LIST_1['list_name'],
            'list_description': SCIETY_LIST_1['list_description']
        }]

    def test_should_populate_avatar_url(self):
        model = ScietyEventListsModel([{
            'event_name': 'ArticleAddedToList',
            'sciety_list': SCIETY_LIST_1,
            'sciety_user': SCIETY_USER_1
        }, {
            'event_name': 'ArticleAddedToList',
            'sciety_list': SCIETY_LIST_1,
            'sciety_user': SCIETY_USER_1
        }])
        result = model.get_most_active_user_lists()
        assert [
            {
                'avatar_url': item['avatar_url'],
            }
            for item in result
        ] == [{
            'avatar_url': SCIETY_USER_1['avatar_url']
        }]
