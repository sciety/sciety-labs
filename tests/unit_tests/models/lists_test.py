from datetime import datetime
from sciety_labs.models.lists import (
    ListMetaData,
    ListSummaryData,
    OwnerMetaData,
    OwnerTypes,
    ScietyEventListsModel,
    get_sorted_list_summary_list_by_most_active
)


DOI_1 = '10.12345/doi_1'
DOI_2 = '10.12345/doi_2'

ARTICLE_ID_1 = f'doi:{DOI_1}'
ARTICLE_ID_2 = f'doi:{DOI_2}'

LIST_ID_1 = 'list_1'
LIST_ID_2 = 'list_2'


SCIETY_LIST_1 = {
    'list_id': LIST_ID_1,
    'list_name': 'List Name 1',
    'list_description': 'List Description 1'
}

USER_ID_1 = 'user_1'
USER_DISPLAY_NAME_1 = 'User 1'

SCIETY_USER_1 = {
    'user_id': USER_ID_1,
    'user_display_name': USER_DISPLAY_NAME_1,
    'avatar_url': 'https://user-avatar/1',
    'twitter_handle': 'handle_1'
}

GROUP_ID_1 = 'group_id_1'
GROUP_SLUG_1 = 'group_slug_1'
GROUP_DISPLAY_NAME_1 = 'Group 1'

SCIETY_GROUP_1 = {
    'group_id': GROUP_ID_1,
    'slug': GROUP_SLUG_1,
    'group_name': GROUP_DISPLAY_NAME_1
}

TIMESTAMP_1 = datetime.fromisoformat('2001-01-01+00:00')
TIMESTAMP_2 = datetime.fromisoformat('2001-01-02+00:00')

USER_ARTICLE_ADDED_TO_LIST_EVENT_1: dict = {
    'event_timestamp': TIMESTAMP_1,
    'event_name': 'ArticleAddedToList',
    'sciety_list': SCIETY_LIST_1,
    'sciety_user': SCIETY_USER_1,
    'article_id': ARTICLE_ID_1
}

USER_ARTICLE_REMOVED_FROM_LIST_EVENT_1 = {
    **USER_ARTICLE_ADDED_TO_LIST_EVENT_1,
    'event_name': 'ArticleRemovedFromList'
}

GROUP_ARTICLE_ADDED_TO_LIST_EVENT_1: dict = {
    'event_timestamp': TIMESTAMP_1,
    'event_name': 'ArticleAddedToList',
    'sciety_list': SCIETY_LIST_1,
    'sciety_group': SCIETY_GROUP_1,
    'article_id': ARTICLE_ID_1
}


ANNOTATION_CREATED_EVENT_1 = {
    **USER_ARTICLE_ADDED_TO_LIST_EVENT_1,
    'content': 'Comment 1',
    'event_name': 'AnnotationCreated'
}


LIST_META_DATA_1 = ListMetaData(
    list_id=LIST_ID_1,
    list_name='List Title 1',
    list_description='List Description 1'
)

OWNER_META_DATA_1 = OwnerMetaData(
    owner_type=OwnerTypes.USER,
    display_name=SCIETY_USER_1['user_display_name'],
    avatar_url=SCIETY_USER_1['avatar_url']
)

LIST_SUMMARY_DATA_1 = ListSummaryData(
    list_meta=LIST_META_DATA_1,
    owner=OWNER_META_DATA_1,
    article_count=10,
    last_updated_datetime=TIMESTAMP_1
)


class TestGetSortedListSummaryListByMostActive:
    def test_should_sort_by_article_count_descending(self):
        expected_list_summary_data = [
            LIST_SUMMARY_DATA_1._replace(article_count=100),
            LIST_SUMMARY_DATA_1._replace(article_count=10),
            LIST_SUMMARY_DATA_1._replace(article_count=1)
        ]
        unsorted_list_summary_data = [
            expected_list_summary_data[1],
            expected_list_summary_data[0],
            expected_list_summary_data[2]
        ]
        result = get_sorted_list_summary_list_by_most_active(
            unsorted_list_summary_data
        )
        assert result == expected_list_summary_data

    def test_should_sort_by_last_updated_datetime_descending(self):
        expected_list_summary_data = [
            LIST_SUMMARY_DATA_1._replace(
                last_updated_datetime=datetime.fromisoformat('2001-01-03')
            ),
            LIST_SUMMARY_DATA_1._replace(
                last_updated_datetime=datetime.fromisoformat('2001-01-02')
            ),
            LIST_SUMMARY_DATA_1._replace(
                last_updated_datetime=datetime.fromisoformat('2001-01-01')
            )
        ]
        unsorted_list_summary_data = [
            expected_list_summary_data[1],
            expected_list_summary_data[0],
            expected_list_summary_data[2]
        ]
        result = get_sorted_list_summary_list_by_most_active(
            unsorted_list_summary_data
        )
        assert result == expected_list_summary_data


class TestScietyEventListsModel:
    def test_should_return_empty_list_for_no_events(self):
        model = ScietyEventListsModel([])
        assert not model.get_most_active_user_lists()

    def test_should_populate_list_id_and_list_meta_fields(self):
        model = ScietyEventListsModel([
            USER_ARTICLE_ADDED_TO_LIST_EVENT_1,
            USER_ARTICLE_ADDED_TO_LIST_EVENT_1
        ])
        result = model.get_most_active_user_lists()
        assert [
            {
                'list_id': item.list_meta.list_id,
                'list_title': item.list_meta.list_name,
                'list_description': item.list_meta.list_description
            }
            for item in result
        ] == [{
            'list_id': LIST_ID_1,
            'list_title': SCIETY_LIST_1['list_name'],
            'list_description': SCIETY_LIST_1['list_description']
        }]

    def test_should_populate_user_display_name_avatar_url_and_twitter_handle(self):
        model = ScietyEventListsModel([
            USER_ARTICLE_ADDED_TO_LIST_EVENT_1,
            USER_ARTICLE_ADDED_TO_LIST_EVENT_1
        ])
        result = model.get_most_active_user_lists()
        assert [item.owner.avatar_url for item in result] == [SCIETY_USER_1['avatar_url']]
        assert [item.owner.display_name for item in result] == [SCIETY_USER_1['user_display_name']]
        assert [item.owner.twitter_handle for item in result] == [SCIETY_USER_1['twitter_handle']]

    def test_should_populate_group_display_name_and_slug(self):
        model = ScietyEventListsModel([
            GROUP_ARTICLE_ADDED_TO_LIST_EVENT_1
        ])
        result = model.get_list_summary_data_by_list_id(SCIETY_LIST_1['list_id'])
        assert result.owner.display_name == SCIETY_GROUP_1['group_name']
        assert result.owner.slug == SCIETY_GROUP_1['slug']

    def test_should_set_group_avatar_url_to_none_if_not_available(self):
        model = ScietyEventListsModel([{
            **GROUP_ARTICLE_ADDED_TO_LIST_EVENT_1,
            'sciety_group': {
                **SCIETY_GROUP_1,
                'avatar_path': None
            }
        }])
        result = model.get_list_summary_data_by_list_id(SCIETY_LIST_1['list_id'])
        assert result.owner.avatar_url is None

    def test_should_resolve_group_avatar_url_from_path(self):
        model = ScietyEventListsModel([{
            **GROUP_ARTICLE_ADDED_TO_LIST_EVENT_1,
            'sciety_group': {
                **SCIETY_GROUP_1,
                'avatar_path': '/static/group/avatar.png'
            }
        }])
        result = model.get_list_summary_data_by_list_id(SCIETY_LIST_1['list_id'])
        assert result.owner.avatar_url == 'https://sciety.org/static/group/avatar.png'

    def test_should_not_include_group_lists_in_user_lists(self):
        model = ScietyEventListsModel([
            GROUP_ARTICLE_ADDED_TO_LIST_EVENT_1
        ])
        result = model.get_most_active_user_lists()
        assert not result

    def test_should_not_include_group_lists_in_group_lists(self):
        model = ScietyEventListsModel([
            GROUP_ARTICLE_ADDED_TO_LIST_EVENT_1
        ])
        result = model.get_most_active_group_lists()
        assert result

    def test_should_not_include_user_lists_in_group_lists(self):
        model = ScietyEventListsModel([
            USER_ARTICLE_ADDED_TO_LIST_EVENT_1
        ])
        result = model.get_most_active_group_lists()
        assert not result

    def test_should_calculate_article_count_for_added_only_events(self):
        model = ScietyEventListsModel([{
            **USER_ARTICLE_ADDED_TO_LIST_EVENT_1,
            'article_id': ARTICLE_ID_1
        }, {
            **USER_ARTICLE_ADDED_TO_LIST_EVENT_1,
            'article_id': ARTICLE_ID_2
        }])
        result = model.get_most_active_user_lists()
        assert [item.article_count for item in result] == [2]

    def test_should_calculate_article_count_for_added_and_removed_events(self):
        model = ScietyEventListsModel([{
            **USER_ARTICLE_ADDED_TO_LIST_EVENT_1,
            'article_id': ARTICLE_ID_1
        }, {
            **USER_ARTICLE_REMOVED_FROM_LIST_EVENT_1,
            'article_id': ARTICLE_ID_1
        }, {
            **USER_ARTICLE_ADDED_TO_LIST_EVENT_1,
            'article_id': ARTICLE_ID_2
        }])
        result = model.get_most_active_user_lists()
        assert [item.article_count for item in result] == [1]

    def test_should_ignore_remove_event_for_not_added_article(self):
        model = ScietyEventListsModel([{
            **USER_ARTICLE_REMOVED_FROM_LIST_EVENT_1,
            'article_id': ARTICLE_ID_1
        }, {
            **USER_ARTICLE_ADDED_TO_LIST_EVENT_1,
            'article_id': ARTICLE_ID_2
        }])
        result = model.get_most_active_user_lists()
        assert [item.article_count for item in result] == [1]

    def test_should_calculate_last_updated_date(self):
        model = ScietyEventListsModel([{
            **USER_ARTICLE_ADDED_TO_LIST_EVENT_1,
            'event_timestamp': datetime.fromisoformat('2001-01-01+00:00'),
            'article_id': ARTICLE_ID_1
        }, {
            **USER_ARTICLE_ADDED_TO_LIST_EVENT_1,
            'event_timestamp': datetime.fromisoformat('2001-01-02+00:00'),
            'article_id': ARTICLE_ID_2
        }])
        result = model.get_most_active_user_lists()
        assert [item.last_updated_datetime for item in result] == [
            datetime.fromisoformat('2001-01-02+00:00')
        ]

    def test_should_ignore_other_events(self):
        model = ScietyEventListsModel([{
            **USER_ARTICLE_ADDED_TO_LIST_EVENT_1,
            'article_id': ARTICLE_ID_1
        }, {
            'event_timestamp': TIMESTAMP_1,
            'event_name': 'other'
        }])
        result = model.get_most_active_user_lists()
        assert [item.article_count for item in result] == [1]

    def test_should_find_list_meta_data_by_id(self):
        model = ScietyEventListsModel([USER_ARTICLE_ADDED_TO_LIST_EVENT_1])
        list_summary_data = model.get_list_meta_data_by_list_id(LIST_ID_1)
        assert isinstance(list_summary_data, ListMetaData)

    def test_should_find_list_summary_data_by_id(self):
        model = ScietyEventListsModel([USER_ARTICLE_ADDED_TO_LIST_EVENT_1])
        list_summary_data = model.get_list_summary_data_by_list_id(LIST_ID_1)
        assert isinstance(list_summary_data, ListSummaryData)

    def test_should_find_article_mention_without_comment(self):
        model = ScietyEventListsModel([USER_ARTICLE_ADDED_TO_LIST_EVENT_1])
        article_mentions = list(model.iter_article_mentions_by_list_id(LIST_ID_1))
        assert article_mentions

    def test_should_find_article_mention_with_comment(self):
        model = ScietyEventListsModel([
            USER_ARTICLE_ADDED_TO_LIST_EVENT_1,
            ANNOTATION_CREATED_EVENT_1
        ])
        article_mentions = list(model.iter_article_mentions_by_list_id(LIST_ID_1))
        assert article_mentions
        assert article_mentions[0].comment.text == ANNOTATION_CREATED_EVENT_1['content']

    def test_should_reverse_sort_article_list(self):
        model = ScietyEventListsModel([
            {
                **USER_ARTICLE_ADDED_TO_LIST_EVENT_1,
                'article_id': ARTICLE_ID_1,
                'event_timestamp': TIMESTAMP_1
            }, {
                **USER_ARTICLE_ADDED_TO_LIST_EVENT_1,
                'article_id': ARTICLE_ID_2,
                'event_timestamp': TIMESTAMP_2
            }
        ])
        article_mentions = list(model.iter_article_mentions_by_list_id(LIST_ID_1))
        assert article_mentions
        assert [
            article_mention.article_doi
            for article_mention in article_mentions
        ] == [DOI_2, DOI_1]
