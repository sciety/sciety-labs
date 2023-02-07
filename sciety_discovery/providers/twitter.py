import logging
import re
from pathlib import Path
from typing import Iterable, NamedTuple, Optional

import requests


LOGGER = logging.getLogger(__name__)


BIORXIV_DOI_PREFIX = '10.1101'


class TwitterArticleListItem(NamedTuple):
    article_doi: str
    article_title: str


def get_doi_without_version(doi: str) -> str:
    m = re.match(r'(.*)v\d+', doi)  # pylint: disable=invalid-name
    if not m:
        return doi
    return m.group(1)


def get_doi_from_url_or_none(url: str) -> Optional[str]:
    m = re.match(r'.*/(10.\d{4,}/[^/]+)', url)  # pylint: disable=invalid-name
    LOGGER.info('m: %r', m)
    if not m:
        return None
    doi = m.group(1)
    if not doi.startswith(BIORXIV_DOI_PREFIX + '/'):
        return None
    if 'biorxiv' in url:
        doi = get_doi_without_version(doi)
    return doi


def iter_dois_from_urls(urls: Iterable[str]) -> Iterable[str]:
    for url in urls:
        doi = get_doi_from_url_or_none(url)
        if doi:
            yield doi


def iter_expanded_urls_from_tweet_response_item(
    user_timeline_response_item: dict
) -> Iterable[str]:
    for url_entity in user_timeline_response_item.get('entities', {}).get('urls', []):
        yield url_entity['expanded_url']


def iter_dois_from_user_tweet_response_item(
    user_timeline_response_item: dict
) -> Iterable[str]:
    expanded_urls = list(iter_expanded_urls_from_tweet_response_item(
        user_timeline_response_item
    ))
    LOGGER.info('expanded_urls: %r', expanded_urls)
    if not expanded_urls:
        LOGGER.info('user_timeline_response_item.keys: %r', user_timeline_response_item.keys())
    yield from iter_dois_from_urls(expanded_urls)


def iter_twitter_article_list_item_for_user_tweets_response(
    user_tweets_response: dict
) -> Iterable[TwitterArticleListItem]:
    for item in user_tweets_response['data']:
        LOGGER.debug('item: %r', item)
        dois = list(iter_dois_from_user_tweet_response_item(
            item
        ))
        LOGGER.debug('dois: %r', dois)
        if len(dois) != 1:
            continue
        doi = dois[0]
        yield TwitterArticleListItem(
            article_doi=doi,
            article_title=doi
        )


def get_user_id_from_user_lookup_response(
    user_lookup_response: dict,
    username: str
) -> str:
    for item in user_lookup_response['data']:
        LOGGER.debug('item: %r', item)
        if item['username'] == username:
            return item['id']
    raise RuntimeError(f'user id not found for: {repr(username)}')


def iter_api_page_responses(
    url: str,
    params: dict,
    timeout: float = 5 * 60,
    **kwargs
) -> Iterable[dict]:
    next_token: Optional[str] = None
    while True:
        _params = (
            {**params, 'pagination_token': next_token}
            if next_token
            else params
        )
        LOGGER.info('requesting, url=%r, params=%r', url, _params)
        response = requests.get(
            url,
            params=_params,
            timeout=timeout,
            **kwargs
        )
        response.raise_for_status()
        response_json = response.json()
        LOGGER.debug('response_json: %s', response_json)
        yield response_json
        next_token = response_json['meta'].get('next_token')
        if not next_token:
            break


class TwitterUserArticleListProvider:
    def __init__(
        self,
        authorization_file: str
    ):
        self.twitter_authorization = Path(authorization_file).read_text(encoding='utf-8')
        self.headers = {
            'Authorization': self.twitter_authorization
        }

    def get_twitter_user_id_by_screen_name(
        self,
        screen_name: str
    ) -> str:
        LOGGER.info('Looking up user %r', screen_name)
        response = requests.get(
            'https://api.twitter.com/2/users/by',
            params={
                'usernames': screen_name,
                'user.fields': 'description'
            },
            headers=self.headers,
            timeout=5 * 60
        )
        response.raise_for_status()
        return get_user_id_from_user_lookup_response(
            response.json(),
            username=screen_name
        )

    def iter_article_mentions_by_user_id(
        self,
        twitter_user_id: str
    ) -> Iterable[TwitterArticleListItem]:
        LOGGER.info('Making Twitter API request for %r', twitter_user_id)
        response_json_iterable = iter_api_page_responses(
            f'https://api.twitter.com/2/users/{twitter_user_id}/tweets',
            params={
                'tweet.fields': 'created_at,text,entities',
                'max_results': '100'
            },
            headers=self.headers,
            timeout=5 * 60
        )
        for response_json in response_json_iterable:
            yield from iter_twitter_article_list_item_for_user_tweets_response(
                response_json
            )

    def iter_article_mentions_by_screen_name(
        self,
        screen_name: str
    ) -> Iterable[TwitterArticleListItem]:
        twitter_user_id = self.get_twitter_user_id_by_screen_name(screen_name)
        yield from self.iter_article_mentions_by_user_id(twitter_user_id)
