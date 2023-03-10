import logging
import concurrent.futures
from itertools import tee
from typing import Dict, Iterable, Mapping, Optional

import requests
import lxml.etree

from sciety_labs.models.article import ArticleMention, ArticleMetaData


LOGGER = logging.getLogger(__name__)


def get_author_name_from_crossref_metadata_author_dict(
    author_dict: dict
) -> str:
    if author_dict.get('name'):
        return author_dict['name']
    return ' '.join([
        author_dict['given'],
        author_dict['family']
    ])


def remove_namespaces_from_xml_node(root: lxml.etree._Element):
    for element in root.getiterator():
        LOGGER.debug('element: %r', element)
        tag_parts = element.tag.split(':', maxsplit=1)
        element.tag = str(lxml.etree.QName(tag_parts[-1]).localname)


def map_xml_tags(root: lxml.etree._Element, mapping: Mapping[str, str]):
    for element in root.getiterator():
        element.tag = mapping.get(element.tag, element.tag)


def get_cleaned_abstract_html(abstract_html: Optional[str]) -> Optional[str]:
    if not abstract_html:
        return None
    if not abstract_html.startswith('<'):
        return abstract_html
    try:
        parser = lxml.etree.XMLParser(recover=True)
        root = lxml.etree.fromstring(
            f'<root>{abstract_html}</root>',
            parser=parser
        )
        remove_namespaces_from_xml_node(root)
        map_xml_tags(root, {
            'title': 'h3',
            'sec': 'section',
            'italic': 'i',
            'list': 'ul',
            'list-item': 'li'
        })
        LOGGER.debug('root: %r', root)
        LOGGER.debug('root.tag: %r', root.tag)
        return b''.join(lxml.etree.tostring(child) for child in root).decode('utf-8')
    except lxml.etree.XMLSyntaxError as exc:
        LOGGER.debug('failed to parse abstract %r due to %r', abstract_html, exc)
        return abstract_html


def get_article_metadata_from_crossref_metadata(
    doi: str,
    crossref_metadata: dict
) -> ArticleMetaData:
    return ArticleMetaData(
        article_doi=doi,
        article_title='\n'.join(crossref_metadata['title']),
        abstract=get_cleaned_abstract_html(crossref_metadata.get('abstract')),
        author_name_list=[
            get_author_name_from_crossref_metadata_author_dict(author_dict)
            for author_dict in crossref_metadata.get('author', [])
        ]
    )


class CrossrefMetaDataProvider:
    def __init__(self, requests_session: Optional[requests.Session] = None) -> None:
        self.headers = {'accept': 'application/json'}
        self.timeout: float = 5 * 60
        if requests_session is None:
            requests_session = requests.Session()
        self.requests_session = requests_session

    def get_crossref_metadata_dict_by_doi(self, doi: str) -> dict:
        url = f'https://api.crossref.org/works/{doi}'
        response = self.requests_session.get(url, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()['message']

    def get_article_metadata_by_doi(self, doi: str) -> ArticleMetaData:
        return get_article_metadata_from_crossref_metadata(
            doi,
            self.get_crossref_metadata_dict_by_doi(doi)
        )

    def iter_article_mention_with_article_meta(
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
        return (
            item._replace(
                article_meta=article_meta_by_doi_map.get(item.article_doi)
            )
            for item in article_mention_iterable
        )
