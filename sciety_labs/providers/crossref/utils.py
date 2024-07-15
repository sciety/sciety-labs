from datetime import date
import logging
from typing import Iterable, Mapping, Optional, Sequence

import lxml.etree

from sciety_labs.models.article import ArticleMention, ArticleMetaData


LOGGER = logging.getLogger(__name__)


def get_author_name_from_crossref_metadata_author_dict(
    author_dict: dict
) -> str:
    if author_dict.get('name'):
        return author_dict['name']
    return ' '.join([
        author_dict.get('given', ''),
        author_dict.get('family', '')
    ]).strip() or '?'


def get_tag_name_without_namespace(tag: str) -> str:
    if tag.startswith('{'):
        local_name = str(lxml.etree.QName(tag).localname)
    else:
        local_name = tag
    tag_parts = local_name.split(':', maxsplit=1)
    return tag_parts[-1]


def remove_namespaces_from_xml_node(root: lxml.etree._Element):
    for element in root.getiterator():
        LOGGER.debug('element: %r', element)
        element.tag = get_tag_name_without_namespace(element.tag)


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
            'list-item': 'li',
            'bold': 'b'
        })
        if root[0].tag == 'h3':
            root.remove(root[0])
        LOGGER.debug('root: %r', root)
        LOGGER.debug('root.tag: %r', root.tag)
        return b''.join(lxml.etree.tostring(child) for child in root).decode('utf-8')
    except lxml.etree.XMLSyntaxError as exc:
        LOGGER.debug('failed to parse abstract %r due to %r', abstract_html, exc)
        return abstract_html


def get_optional_date_from_date_parts(
    date_parts: Optional[Sequence[Sequence[int]]]
) -> Optional[date]:
    if not date_parts:
        return None
    assert len(date_parts) == 1
    if len(date_parts[0]) != 3:
        LOGGER.warning('incomplete date pars: %r', date_parts[0])
        return None
    year, month, day = date_parts[0]
    return date(year, month, day)


def get_optional_date_from_date_field(date_field: Optional[dict]) -> Optional[date]:
    if not date_field:
        return None
    return get_optional_date_from_date_parts(date_field.get('date-parts'))


def get_published_date_from_crossref_metadata(crossref_metadata: dict) -> Optional[date]:
    accepted_date = get_optional_date_from_date_field(crossref_metadata.get('accepted'))
    published_date = get_optional_date_from_date_field(crossref_metadata.get('published'))
    if accepted_date and published_date:
        return max(accepted_date, published_date)
    return accepted_date or published_date


def get_article_metadata_from_crossref_metadata(
    doi: str,
    crossref_metadata: dict
) -> ArticleMetaData:
    try:
        return ArticleMetaData(
            article_doi=doi,
            article_title='\n'.join(crossref_metadata['title']),
            abstract=get_cleaned_abstract_html(crossref_metadata.get('abstract')),
            author_name_list=[
                get_author_name_from_crossref_metadata_author_dict(author_dict)
                for author_dict in crossref_metadata.get('author', [])
            ],
            published_date=get_published_date_from_crossref_metadata(
                crossref_metadata
            )
        )
    except Exception as exc:
        LOGGER.error('Error parsing metadata for DOI %r due to %r', doi, exc)
        raise


def get_filter_parameter_for_dois(dois: Iterable[str]) -> str:
    return ','.join((f'doi:{doi}' for doi in dois))


def get_batch_doi_request_parameters(dois: Sequence[str]) -> Mapping[str, str]:
    return {'filter': get_filter_parameter_for_dois(dois), 'rows': str(len(dois))}


def get_response_dict_by_doi_map(response_dict: dict) -> Mapping[str, dict]:
    return {
        item['DOI']: item
        for item in response_dict['message']['items']
    }


def get_article_meta_by_doi_map_for_response_dict_mapping(
    response_dict_by_doi_map: Mapping[str, dict]
) -> Mapping[str, ArticleMetaData]:
    return {
        doi: get_article_metadata_from_crossref_metadata(doi, response_dict)
        for doi, response_dict in response_dict_by_doi_map.items()
    }


def iter_article_mention_with_replaced_article_meta(
    article_mention_iterable: Iterable[ArticleMention],
    article_meta_by_doi_map: Mapping[str, ArticleMetaData]
) -> Iterable[ArticleMention]:
    return (
        item._replace(
            article_meta=article_meta_by_doi_map.get(item.article_doi)
        )
        for item in article_mention_iterable
    )
