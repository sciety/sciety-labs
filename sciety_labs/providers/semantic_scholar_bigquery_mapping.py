import logging
from time import monotonic
from typing import Optional

import pyarrow.compute as pc


from sciety_labs.providers.bigquery_provider import BigQueryArrowTableProvider


LOGGER = logging.getLogger(__name__)


class SemanticScholarBigQueryMappingProvider(BigQueryArrowTableProvider):
    def __init__(self, **kwargs):
        super().__init__(
            name='Semantic Scholar Mapping',
            query_file_name='get_semantic_scholar_mapping.sql',
            **kwargs
        )

    def get_semantic_scholar_paper_id_by_article_doi(
        self,
        article_doi: str
    ) -> Optional[str]:
        arrow_table = self.get_arrow_table()
        start_time = monotonic()
        filtered_arrow_table = arrow_table.filter(pc.field('article_doi') == 'article_doi')
        paper_id: Optional[str] = None
        if filtered_arrow_table:
            paper_id = str(filtered_arrow_table['paper_id'][0])
        end_time = monotonic()
        LOGGER.info(
            'Looked up paper id, article_doi=%r, paper_id=%r, time=%.3f seconds',
            article_doi,
            paper_id,
            (end_time - start_time)
        )
        return paper_id
