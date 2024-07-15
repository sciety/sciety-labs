import logging
import concurrent.futures
from itertools import tee
from typing import Dict, Iterable, Mapping, Optional, Sequence


from sciety_labs.models.article import ArticleMention, ArticleMetaData
from sciety_labs.providers.crossref.utils import (
    get_article_meta_by_doi_map_for_response_dict_mapping,
    get_article_metadata_from_crossref_metadata,
    get_batch_doi_request_parameters,
    get_response_dict_by_doi_map,
    iter_article_mention_with_replaced_article_meta
)
from sciety_labs.providers.requests_provider import RequestsProvider


LOGGER = logging.getLogger(__name__)


class CrossrefMetaDataProvider(RequestsProvider):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.headers['accept'] = 'application/json'

    def get_crossref_metadata_dict_by_doi(
        self,
        doi: str,
        headers: Optional[Mapping[str, str]] = None
    ) -> dict:
        url = f'https://api.crossref.org/works/{doi}'
        response = self.requests_session.get(
            url,
            headers=self.get_headers(headers=headers),
            timeout=self.timeout
        )
        if response.status_code != 200:
            LOGGER.warning(
                'Crossref response (doi=%r, status=%r): %r',
                doi,
                response.status_code,
                response.content
            )
        response.raise_for_status()
        return response.json()['message']

    def get_batch_crossref_metadata_dict_by_doi(self, dois: Sequence[str]) -> Mapping[str, dict]:
        url = 'https://api.crossref.org/works'
        params = get_batch_doi_request_parameters(dois)
        response = self.requests_session.get(
            url, headers=self.headers, params=params, timeout=self.timeout
        )
        response.raise_for_status()
        return get_response_dict_by_doi_map(response.json())

    def get_article_metadata_by_doi(
        self,
        doi: str,
        headers: Optional[Mapping[str, str]] = None
    ) -> ArticleMetaData:
        return get_article_metadata_from_crossref_metadata(
            doi,
            self.get_crossref_metadata_dict_by_doi(doi, headers=headers),
        )

    def iter_article_mention_with_article_meta(
        self,
        article_mention_iterable: Iterable[ArticleMention]
    ) -> Iterable[ArticleMention]:
        article_mention_list = list(article_mention_iterable)
        article_dois = {
            item.article_doi
            for item in article_mention_list
        }
        if not article_dois:
            return article_mention_list
        article_meta_by_doi_map = get_article_meta_by_doi_map_for_response_dict_mapping(
            self.get_batch_crossref_metadata_dict_by_doi(list(article_dois))
        )
        return iter_article_mention_with_replaced_article_meta(
            article_mention_list,
            article_meta_by_doi_map=article_meta_by_doi_map
        )

    def iter_article_mention_with_article_meta_parallel(
        self,
        article_mention_iterable: Iterable[ArticleMention]
    ) -> Iterable[ArticleMention]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            article_mention_iterable, temp_article_mention_iterable = (
                tee(article_mention_iterable, 2)
            )
            article_dois = {
                item.article_doi
                for item in temp_article_mention_iterable
            }
            LOGGER.info('Looking up article dois: %r', article_dois)
            doi_by_future_map = {
                executor.submit(
                    self.get_article_metadata_by_doi,
                    article_doi
                ): article_doi
                for article_doi in article_dois
            }
            article_meta_by_doi_map: Dict[str, ArticleMetaData] = {}
            for future in concurrent.futures.as_completed(doi_by_future_map):
                article_doi = doi_by_future_map[future]
                try:
                    article_meta = future.result()
                    article_meta_by_doi_map[article_doi] = article_meta
                except Exception as exc:  # pylint: disable=broad-except
                    LOGGER.warning('Failed to lookup DOI: %r due to %r', article_doi, exc)
        return iter_article_mention_with_replaced_article_meta(
            article_mention_iterable,
            article_meta_by_doi_map=article_meta_by_doi_map
        )
