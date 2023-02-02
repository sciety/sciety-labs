from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Dict, Iterable, NamedTuple, Optional, Protocol, Sequence, Sized


class ListMetaData(NamedTuple):
    list_id: str
    list_name: str
    list_description: str

    @staticmethod
    def from_sciety_event_list_meta(sciety_event_list_meta: dict) -> 'ListMetaData':
        return ListMetaData(
            list_id=sciety_event_list_meta['list_id'],
            list_name=sciety_event_list_meta['list_name'],
            list_description=sciety_event_list_meta['list_description']
        )


class OwnerMetaData(NamedTuple):
    avatar_url: str

    @staticmethod
    def from_sciety_event_user_meta(sciety_event_user_meta: dict) -> 'OwnerMetaData':
        return OwnerMetaData(
            avatar_url=sciety_event_user_meta['avatar_url']
        )


class ArticleListItem(NamedTuple):
    article_id: str
    added_datetime: datetime


@dataclass
class ArticleList(Sized):
    _article_list_item_by_article_id: Dict[str, ArticleListItem] = field(default_factory=dict)
    last_updated_datetime: Optional[datetime] = None

    def __len__(self) -> int:
        return len(self._article_list_item_by_article_id)

    def add(self, item: ArticleListItem):
        self._article_list_item_by_article_id[item.article_id] = item
        self.last_updated_datetime = item.added_datetime

    def remove_by_article_id(self, article_id: str, when: datetime):
        del self._article_list_item_by_article_id[article_id]
        self.last_updated_datetime = when


class ListSummaryData(NamedTuple):
    list_meta: ListMetaData
    owner: OwnerMetaData
    article_count: int
    last_updated_datetime: Optional[datetime]

    @property
    def last_updated_date_isoformat(self) -> str:
        if not self.last_updated_datetime:
            return ''
        return self.last_updated_datetime.strftime(r'%Y-%m-%d')

    @property
    def last_updated_date_display_format(self) -> str:
        if not self.last_updated_datetime:
            return ''
        return self.last_updated_datetime.strftime(r'%b %-d, %Y')

    def get_activity_sort_key(self) -> int:
        return -self.article_count


class ScietyEventNames:
    ARTICLE_ADDED_TO_LIST = 'ArticleAddedToList'
    ARTICLE_REMOVED_FROM_LIST = 'ArticleRemovedFromList'


class ListsModel(Protocol):
    def get_most_active_user_lists(self) -> Sequence[ListSummaryData]:
        pass


def get_sorted_list_summary_list_by_most_active(
    list_summary_iterable: Iterable[ListSummaryData],
) -> Sequence[ListSummaryData]:
    return sorted(
        list_summary_iterable,
        key=ListSummaryData.get_activity_sort_key
    )


class ScietyEventListsModel(ListsModel):
    def __init__(self, sciety_events: Sequence[dict]):
        self._list_meta_by_list_id: Dict[str, ListMetaData] = {}
        self._owner_meta_by_list_id: Dict[str, OwnerMetaData] = {}
        self._article_list_by_list_id: Dict[str, ArticleList] = defaultdict(ArticleList)
        self._lock = Lock()
        self.apply_events(sciety_events)

    def _do_apply_events(self, sciety_events: Sequence[dict]):
        for event in sciety_events:
            event_timestamp = event['event_timestamp']
            event_name = event['event_name']
            sciety_list = event['sciety_list']
            sciety_user = event.get('sciety_user')
            list_id = sciety_list['list_id']
            article_id = event.get('article_id')
            if not sciety_list:
                continue
            list_meta = ListMetaData.from_sciety_event_list_meta(sciety_list)
            list_id = list_meta.list_id
            self._list_meta_by_list_id[list_id] = list_meta
            if list_id and sciety_user:
                self._owner_meta_by_list_id[list_id] = (
                    OwnerMetaData.from_sciety_event_user_meta(sciety_user)
                )
            if list_id and article_id:
                if event_name == ScietyEventNames.ARTICLE_ADDED_TO_LIST:
                    self._article_list_by_list_id[list_id].add(
                        ArticleListItem(article_id=article_id, added_datetime=event_timestamp)
                    )
                if event_name == ScietyEventNames.ARTICLE_REMOVED_FROM_LIST:
                    try:
                        self._article_list_by_list_id[list_id].remove_by_article_id(
                            article_id,
                            when=event_timestamp
                        )
                    except KeyError:
                        pass

    def apply_events(self, sciety_events: Sequence[dict]):
        with self._lock:
            self._do_apply_events(sciety_events)

    def get_most_active_user_lists(
        self,
        top_n: Optional[int] = None
    ) -> Sequence[ListSummaryData]:
        result = get_sorted_list_summary_list_by_most_active([
            ListSummaryData(
                list_meta=list_meta,
                owner=self._owner_meta_by_list_id[list_meta.list_id],
                article_count=len(self._article_list_by_list_id[
                    list_meta.list_id
                ]),
                last_updated_datetime=self._article_list_by_list_id[
                    list_meta.list_id
                ].last_updated_datetime
            )
            for list_meta in self._list_meta_by_list_id.values()
        ])
        if top_n:
            result = result[:top_n]
        return result
