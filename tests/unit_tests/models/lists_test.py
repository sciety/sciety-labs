from sciety_discovery.models.lists import (
    ScietyEventListsModel
)


LIST_ID_1 = 'list_1'
LIST_ID_2 = 'list_2'

SCIETY_LIST_1 = {
    'list_id': LIST_ID_1
}


class TestScietyEventListsModel:
    def test_should_return_empty_list_for_no_events(self):
        model = ScietyEventListsModel([])
        assert not model.get_most_active_user_lists()

    def test_should_populate_list_id(self):
        model = ScietyEventListsModel([{
            'event_name': 'ArticleAddedToList',
            'sciety_list': SCIETY_LIST_1
        }, {
            'event_name': 'ArticleAddedToList',
            'sciety_list': SCIETY_LIST_1
        }])
        result = model.get_most_active_user_lists()
        assert [
            item['list_id']
            for item in result
        ] == [LIST_ID_1]
