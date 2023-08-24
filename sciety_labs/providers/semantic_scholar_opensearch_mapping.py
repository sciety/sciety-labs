import logging
from typing import Mapping, Sequence

from opensearchpy import OpenSearch


from sciety_labs.providers.semantic_scholar_mapping import BaseSemanticScholarMappingProvider


LOGGER = logging.getLogger(__name__)


class SemanticScholarOpenSearchMappingProvider(
    BaseSemanticScholarMappingProvider
):
    def __init__(
        self,
        opensearch_client: OpenSearch,
        index_name: str
    ):
        self.opensearch_client = opensearch_client
        self.index_name = index_name

    def do_get_semantic_scholar_paper_ids_by_article_dois_map(
        self,
        article_dois: Sequence[str]
    ) -> Mapping[str, str]:
        mget_response = self.opensearch_client.mget(
            index=self.index_name,
            body={'ids': article_dois}
        )
        return {
            doc['_id']: doc['_source']['paper_id']
            for doc in mget_response['docs']
            if doc.get('_source', {}).get('paper_id')
        }

    def preload(self):
        pass

    def refresh(self):
        pass
