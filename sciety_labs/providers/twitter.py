import logging
import os
import re
from pathlib import Path
from typing import Iterable, NamedTuple, Optional

import requests

from sciety_labs.models.article import ArticleAuthor, ArticleComment, ArticleMention
from sciety_labs.providers.requests_provider import RequestsProvider
from sciety_labs.utils.datetime import parse_timestamp


LOGGER = logging.getLogger(__name__)


TWITTER_API_AUTHORIZATION_FILE_PATH_ENV_VAR = 'TWITTER_API_AUTHORIZATION_FILE_PATH'


BIORXIV_DOI_PREFIX = '10.1101'


class TwitterUser(NamedTuple):
    user_id: str
    username: str
    description: str
    name: str


class TwitterUserNotFound(RuntimeError):
    pass


def get_doi_without_version(doi: str) -> str:
    m = re.match(r'(.*)v\d+', doi)  # pylint: disable=invalid-name
    if not m:
        return doi
    return m.group(1)


def get_doi_from_url_or_none(url: str) -> Optional[str]:
    m = re.match(r'.*/(10.\d{4,}/[^/]+)', url)  # pylint: disable=invalid-name
    LOGGER.debug('m: %r', m)
    if not m:
        return None
    doi = m.group(1)
    if not doi.startswith(BIORXIV_DOI_PREFIX + '/'):
        return None
    if doi.startswith(BIORXIV_DOI_PREFIX):
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
    LOGGER.debug('expanded_urls: %r', expanded_urls)
    if not expanded_urls:
        LOGGER.debug('user_timeline_response_item.keys: %r', user_timeline_response_item.keys())
    yield from iter_dois_from_urls(expanded_urls)


def get_text_with_expanded_urls(text: str, url_entities: Iterable[dict]) -> str:
    result = text
    for url_entity in url_entities:
        url = url_entity['url']
        expanded_url = url_entity['expanded_url']
        result = re.sub(r'\b' + re.escape(url) + r'\b', expanded_url, result)
    return result


def iter_twitter_article_list_item_for_user_tweets_response(
    user_tweets_response: dict,
    twitter_user: TwitterUser
) -> Iterable[ArticleMention]:
    comment_author = ArticleAuthor(name=twitter_user.name)
    for item in user_tweets_response['data']:
        LOGGER.debug('item: %r', item)
        dois = list(iter_dois_from_user_tweet_response_item(
            item
        ))
        LOGGER.debug('dois: %r', dois)
        if len(dois) != 1:
            continue
        doi = dois[0]
        text = item.get('text')
        if text:
            text = get_text_with_expanded_urls(text, item.get('entities', {}).get('urls', []))
        comment = (
            ArticleComment(text=text, author=comment_author)
            if text
            else None
        )
        yield ArticleMention(
            created_at_timestamp=parse_timestamp(item['created_at']),
            article_doi=doi,
            external_reference_by_name={'tweet_id': item['id']},
            comment=comment
        )


def get_twitter_user_from_dict(user_dict: dict) -> TwitterUser:
    return TwitterUser(
        user_id=user_dict['id'],
        username=user_dict['username'],
        description=user_dict['description'],
        name=user_dict['name']
    )


def get_twitter_user_from_user_lookup_response(
    user_lookup_response: dict,
    username: str
) -> TwitterUser:
    for item in user_lookup_response['data']:
        LOGGER.debug('item: %r', item)
        if item['username'] == username:
            return get_twitter_user_from_dict(item)
    raise TwitterUserNotFound(f'user id not found for: {repr(username)}')


def iter_api_page_responses(
    url: str,
    params: dict,
    session: requests.Session,
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
        response = session.get(
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


class TwitterUserArticleListProvider(RequestsProvider):
    def __init__(
        self,
        authorization_file: str,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.twitter_authorization = Path(authorization_file).read_text(encoding='utf-8')
        self.headers['Authorization'] = self.twitter_authorization

    def get_twitter_user_by_screen_name(self, screen_name: str) -> TwitterUser:
        LOGGER.info('Looking up user %r', screen_name)
        response = self.requests_session.get(
            'https://api.twitter.com/2/users/by',
            params={
                'usernames': screen_name,
                'user.fields': 'description'
            },
            headers=self.headers,
            timeout=self.timeout
        )
        response.raise_for_status()
        return get_twitter_user_from_user_lookup_response(
            response.json(),
            username=screen_name
        )

    def iter_article_mentions_by_user(
        self,
        twitter_user: TwitterUser
    ) -> Iterable[ArticleMention]:
        LOGGER.info('Making Twitter API request for %r', twitter_user)
        response_json_iterable = iter_api_page_responses(
            f'https://api.twitter.com/2/users/{twitter_user.user_id}/tweets',
            params={
                'tweet.fields': 'created_at,text,entities',
                'max_results': '100'
            },
            session=self.requests_session,
            headers=self.headers,
            timeout=self.timeout
        )
        for response_json in response_json_iterable:
            yield from iter_twitter_article_list_item_for_user_tweets_response(
                response_json,
                twitter_user=twitter_user
            )


def get_twitter_api_authorization_file_path() -> Optional[str]:
    return os.getenv(TWITTER_API_AUTHORIZATION_FILE_PATH_ENV_VAR)


def get_twitter_user_article_list_provider_or_none(
    **kwargs
) -> Optional[TwitterUserArticleListProvider]:
    twitter_api_authorization_file_path = get_twitter_api_authorization_file_path()
    if not twitter_api_authorization_file_path:
        LOGGER.info('Twitter API authorization not configured, not using twitter api')
        return None
    if not os.path.exists(twitter_api_authorization_file_path):
        LOGGER.info(
            'Twitter API authorization file does not exist, not using twitter api: %r',
            twitter_api_authorization_file_path
        )
        return None
    LOGGER.info('Using Twitter API authorization: %r', twitter_api_authorization_file_path)
    return TwitterUserArticleListProvider(twitter_api_authorization_file_path, **kwargs)
