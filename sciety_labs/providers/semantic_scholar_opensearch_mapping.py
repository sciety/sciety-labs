import logging
from time import monotonic
from typing import Mapping, Optional, Sequence

from opensearchpy import OpenSearch


from sciety_labs.providers.semantic_scholar_mapping import SemanticScholarMappingProvider


LOGGER = logging.getLogger(__name__)


class SemanticScholarOpenSearchMappingProvider(
    SemanticScholarMappingProvider
):
    def __init__(
        self,
        opensearch_client: OpenSearch,
        index_name: str
    ):
        self.opensearch_client = opensearch_client
        self.index_name = index_name

    def get_semantic_scholar_paper_ids_by_article_dois_map(
        self,
        article_dois: Sequence[str]
    ) -> Mapping[str, str]:
        start_time = monotonic()
        mget_response = self.opensearch_client.mget(
            index=self.index_name,
            body={'ids': article_dois}
        )
        paper_ids_by_article_dois_map = {
            doc['_id']: doc['_source']['paper_id']
            for doc in mget_response['docs']
            if doc.get('_source', {}).get('paper_id')
        }
        end_time = monotonic()
        LOGGER.info(
            'Looked up paper ids, article_dois=%r, map=%r, time=%.3f seconds',
            article_dois,
            paper_ids_by_article_dois_map,
            (end_time - start_time)
        )
        return paper_ids_by_article_dois_map

    def get_semantic_scholar_paper_id_by_article_doi(
        self,
        article_doi: str
    ) -> Optional[str]:
        paper_ids_by_article_dois_map = self.get_semantic_scholar_paper_ids_by_article_dois_map(
            article_dois=[article_doi]
        )
        return paper_ids_by_article_dois_map.get(article_doi)

    def preload(self):
        pass
