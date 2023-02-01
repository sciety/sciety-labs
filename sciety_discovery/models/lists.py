from collections import defaultdict
from datetime import datetime
from typing import Dict, Protocol, Sequence, Set


STATIC_USER_LISTS = [{
    'list_id': 'b8575203-b305-4ede-8b6f-5850a22b1d3b',
    'list_title': '@BiophysicsColab',
    'list_description': 'Articles that have been saved by @BiophysicsColab',
    'avatar_url': 'https://pbs.twimg.com/profile_images/1417582635040317442/jYHfOlh6_normal.jpg',
    'article_count': 82,
    'last_updated_date_isoformat': '2022-11-30',
    'last_updated_date_display_format': 'Nov 30, 2022'
}, {
    'list_id': 'e60ede07-a07e-41c4-9e29-9257c0c8bbf3',
    'list_title': '@AvasthiReading',
    'list_description': 'Articles that have been saved by @AvasthiReading',
    'avatar_url': 'https://pbs.twimg.com/profile_images/1417079202973638657/VrQKBTkw_normal.jpg',
    'article_count': 137,
    'last_updated_date_isoformat': '2022-10-19',
    'last_updated_date_display_format': 'Oct 19, 2022'
}, {
    'list_id': '3e0572d3-be24-4728-852a-8337feba0966',
    'list_title': '@maria_eichel',
    'list_description': 'Articles that have been saved by @maria_eichel',
    'avatar_url': 'https://pbs.twimg.com/profile_images/1584205611247583234/aN5oC7iZ_normal.jpg',
    'article_count': 18,
    'last_updated_date_isoformat': '2022-10-19',
    'last_updated_date_display_format': 'Oct 19, 2022'
}]


class ListsModel(Protocol):
    def get_most_active_user_lists(self) -> Sequence[dict]:
        pass


class StaticListsModel(ListsModel):
    def get_most_active_user_lists(self) -> Sequence[dict]:
        return STATIC_USER_LISTS


class ScietyEventListsModel(ListsModel):
    def __init__(self, sciety_events: Sequence[dict]):
        self._sciety_list_meta_by_list_id: Dict[str, dict] = {}
        self._sciety_user_meta_by_list_id: Dict[str, dict] = {}
        self._article_ids_by_list_id: Dict[str, Set[str]] = defaultdict(set)
        self._last_updated_by_list_id: Dict[str, datetime] = {}
        for event in sciety_events:
            event_timestamp = event['event_timestamp']
            sciety_list = event['sciety_list']
            sciety_user = event.get('sciety_user')
            list_id = sciety_list['list_id']
            article_id = event.get('article_id')
            if list_id and sciety_list:
                self._sciety_list_meta_by_list_id[list_id] = sciety_list
            if list_id and sciety_user:
                self._sciety_user_meta_by_list_id[list_id] = sciety_user
            if list_id and article_id:
                self._article_ids_by_list_id[list_id].add(article_id)
                self._last_updated_by_list_id[list_id] = event_timestamp

    def get_most_active_user_lists(self) -> Sequence[dict]:
        return [
            {
                'list_id': sciety_list_meta['list_id'],
                'list_title': sciety_list_meta['list_name'],
                'list_description': sciety_list_meta['list_description'],
                'avatar_url': self._sciety_user_meta_by_list_id[
                    sciety_list_meta['list_id']
                ]['avatar_url'],
                'article_count': len(self._article_ids_by_list_id[
                    sciety_list_meta['list_id']
                ]),
                'last_updated_date_isoformat': self._last_updated_by_list_id[
                    sciety_list_meta['list_id']
                ].strftime(r'%Y-%m-%d'),
                'last_updated_date_display_format': self._last_updated_by_list_id[
                    sciety_list_meta['list_id']
                ].strftime(r'%b %-d, %Y')
            }
            for sciety_list_meta in self._sciety_list_meta_by_list_id.values()
        ]
