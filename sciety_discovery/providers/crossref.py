from typing import Iterable
import requests

from sciety_discovery.models.article import ArticleMention, ArticleMetaData


def get_article_metadata_from_crossref_metadata(
    doi: str,
    crossref_metadata: dict
) -> ArticleMetaData:
    return ArticleMetaData(
        article_doi=doi,
        article_title='\n'.join(crossref_metadata['title'])
    )


class CrossrefMetaDataProvider:
    def __init__(self) -> None:
        self.headers = {'accept': 'application/json'}
        self.timeout: float = 5 * 60

    def get_crossref_metadata_dict_by_doi(self, doi: str) -> dict:
        url = f'https://api.crossref.org/works/{doi}'
        response = requests.get(url, headers=self.headers, timeout=self.timeout)
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
        return (
            item._replace(
                article_meta=self.get_article_metadata_by_doi(
                    item.article_doi
                )
            )
            for item in article_mention_iterable
        )
