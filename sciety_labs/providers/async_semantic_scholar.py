import logging
from typing import Mapping, Optional, Sequence

from sciety_labs.providers.async_requests_provider import AsyncRequestsProvider


LOGGER = logging.getLogger(__name__)


class AsyncSemanticScholarTitleAbstractEmbeddingVectorProvider(AsyncRequestsProvider):
    async def get_embedding_vector(
        self,
        title: str,
        abstract: str,
        headers: Optional[Mapping[str, str]] = None
    ) -> Sequence[float]:
        paper_id = '_dummy_paper_id'
        papers = [{
            'paper_id': paper_id,
            'title': title,
            'abstract': abstract
        }]
        async with self.post(
            'https://model-apis.semanticscholar.org/specter/v1/invoke',
            json=papers,
            timeout=self.timeout,
            headers=self.get_headers(headers=headers)
        ) as response:
            response.raise_for_status()
            response_json = await response.json()
            embeddings_by_paper_id = {
                pred['paper_id']: pred['embedding']
                for pred in response_json.get('preds')
            }
            return embeddings_by_paper_id[paper_id]
