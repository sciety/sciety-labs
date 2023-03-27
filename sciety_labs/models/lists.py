from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Dict, Iterable, NamedTuple, Optional, Protocol, Sequence, Sized

from sciety_labs.models.article import ArticleMention, get_doi_from_article_id_or_none
from sciety_labs.models.image import ObjectImages


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


def get_avatar_url_for_avatar_path(avatar_path: Optional[str]) -> Optional[str]:
    if not avatar_path:
        return avatar_path
    return f'https://sciety.org{avatar_path}'


class OwnerTypes:
    USER = 'user'
    GROUP = 'group'


class OwnerMetaData(NamedTuple):
    owner_type: str
    display_name: str
    avatar_url: Optional[str] = None
    slug: Optional[str] = None
    twitter_handle: Optional[str] = None

    @staticmethod
    def from_sciety_event_user_meta(sciety_event_user_meta: dict) -> 'OwnerMetaData':
        return OwnerMetaData(
            owner_type=OwnerTypes.USER,
            display_name=sciety_event_user_meta['user_display_name'],
            avatar_url=sciety_event_user_meta['avatar_url'],
            twitter_handle=sciety_event_user_meta.get('twitter_handle')
        )

    @staticmethod
    def from_sciety_event_group_meta(sciety_event_group_meta: dict) -> 'OwnerMetaData':
        return OwnerMetaData(
            owner_type=OwnerTypes.GROUP,
            display_name=sciety_event_group_meta['group_name'],
            avatar_url=get_avatar_url_for_avatar_path(
                sciety_event_group_meta.get('avatar_path')
            ),
            slug=sciety_event_group_meta.get('slug')
        )


class ArticleListItem(NamedTuple):
    article_id: str
    added_datetime: datetime


class ArticleCommentItem(NamedTuple):
    article_id: str
    comment: str
    added_datetime: datetime


@dataclass
class ArticleList(Sized):
    _article_list_item_by_article_id: Dict[str, ArticleListItem] = field(default_factory=dict)
    _article_comment_by_article_id: Dict[str, ArticleCommentItem] = field(default_factory=dict)
    last_updated_datetime: Optional[datetime] = None

    def __len__(self) -> int:
        return len(self._article_list_item_by_article_id)

    def iter_article_list_item(self) -> Iterable[ArticleListItem]:
        return self._article_list_item_by_article_id.values()

    def add(self, item: ArticleListItem):
        self._article_list_item_by_article_id[item.article_id] = item
        self.last_updated_datetime = item.added_datetime

    def remove_by_article_id(self, article_id: str, when: datetime):
        del self._article_list_item_by_article_id[article_id]
        self.last_updated_datetime = when

    def add_comment(self, comment: ArticleCommentItem):
        self._article_comment_by_article_id[comment.article_id] = comment

    def get_comment_by_article_id(self, article_id: str) -> Optional[ArticleCommentItem]:
        return self._article_comment_by_article_id.get(article_id)


class ListSummaryData(NamedTuple):
    list_meta: ListMetaData
    owner: OwnerMetaData
    article_count: int
    last_updated_datetime: Optional[datetime]
    list_images: Optional[ObjectImages] = None

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
    ANNOTATION_CREATED = 'AnnotationCreated'


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
            sciety_list = event.get('sciety_list')
            if not sciety_list:
                continue
            sciety_user = event.get('sciety_user')
            sciety_group = event.get('sciety_group')
            article_id = event.get('article_id')
            list_id = sciety_list['list_id']
            list_meta = ListMetaData.from_sciety_event_list_meta(sciety_list)
            list_id = list_meta.list_id
            if list_id:
                self._list_meta_by_list_id[list_id] = list_meta
            if sciety_user and not sciety_user['user_id']:
                sciety_user = None
            if sciety_group and not sciety_group['group_id']:
                sciety_group = None
            if list_id and sciety_user:
                self._owner_meta_by_list_id[list_id] = (
                    OwnerMetaData.from_sciety_event_user_meta(sciety_user)
                )
            if list_id and sciety_group:
                self._owner_meta_by_list_id[list_id] = (
                    OwnerMetaData.from_sciety_event_group_meta(sciety_group)
                )
            if list_id and article_id:
                if event_name == ScietyEventNames.ARTICLE_ADDED_TO_LIST:
                    self._article_list_by_list_id[list_id].add(
                        ArticleListItem(article_id=article_id, added_datetime=event_timestamp)
                    )
                if event_name == ScietyEventNames.ANNOTATION_CREATED:
                    self._article_list_by_list_id[list_id].add_comment(
                        ArticleCommentItem(
                            article_id=article_id,
                            comment=event['content'],
                            added_datetime=event_timestamp
                        )
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

    def get_list_summary_data_for_list_meta(self, list_meta) -> ListSummaryData:
        return ListSummaryData(
            list_meta=list_meta,
            owner=self._owner_meta_by_list_id[list_meta.list_id],
            article_count=len(self._article_list_by_list_id[
                list_meta.list_id
            ]),
            last_updated_datetime=self._article_list_by_list_id[
                list_meta.list_id
            ].last_updated_datetime
        )

    def iter_list_summary_data(self) -> Iterable[ListSummaryData]:
        for list_meta in self._list_meta_by_list_id.values():
            yield self.get_list_summary_data_for_list_meta(list_meta)

    def get_most_active_user_lists(
        self,
        top_n: Optional[int] = None,
        min_article_count: int = 1
    ) -> Sequence[ListSummaryData]:
        result = get_sorted_list_summary_list_by_most_active([
            list_summary_data
            for list_summary_data in self.iter_list_summary_data()
            if list_summary_data.article_count >= min_article_count
            and list_summary_data.owner.owner_type == OwnerTypes.USER
        ])
        if top_n:
            result = result[:top_n]
        return result

    def get_list_meta_data_by_list_id(
        self,
        list_id: str
    ) -> ListMetaData:
        return self._list_meta_by_list_id[list_id]

    def get_list_summary_data_by_list_id(
        self,
        list_id: str
    ) -> ListSummaryData:
        return self.get_list_summary_data_for_list_meta(
            self.get_list_meta_data_by_list_id(list_id)
        )

    def iter_unsorted_article_mentions_by_list_id(
        self,
        list_id: str
    ) -> Iterable[ArticleMention]:
        article_list = self._article_list_by_list_id[list_id]
        for article_list_item in article_list.iter_article_list_item():
            article_doi = get_doi_from_article_id_or_none(article_list_item.article_id)
            if not article_doi:
                continue
            comment_item = article_list.get_comment_by_article_id(article_list_item.article_id)
            comment_text = (
                comment_item.comment if comment_item
                else None
            )
            yield ArticleMention(
                article_doi=article_doi,
                comment=comment_text,
                created_at_timestamp=article_list_item.added_datetime
            )

    def iter_article_mentions_by_list_id(
        self,
        list_id: str
    ) -> Iterable[ArticleMention]:
        yield from sorted(
            self.iter_unsorted_article_mentions_by_list_id(list_id),
            key=ArticleMention.get_created_at_sort_key,
            reverse=True
        )
