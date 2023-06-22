import logging
from time import monotonic
from typing import Any, Mapping, Optional, Sequence

import pyarrow.compute as pc


from sciety_labs.providers.bigquery_provider import BigQueryArrowTableProvider


LOGGER = logging.getLogger(__name__)


def _to_str_list(list_: Sequence[Any]) -> Sequence[str]:
    return [str(value) for value in list_]


class SemanticScholarBigQueryMappingProvider(BigQueryArrowTableProvider):
    def __init__(self, **kwargs):
        super().__init__(
            name='Semantic Scholar Mapping',
            query_file_name='get_semantic_scholar_mapping.sql',
            **kwargs
        )

    def get_semantic_scholar_paper_ids_by_article_dois_map(
        self,
        article_dois: Sequence[str]
    ) -> Mapping[str, str]:
        arrow_table = self.get_arrow_table()
        start_time = monotonic()
        filtered_arrow_table = arrow_table.filter(
            pc.field('article_doi').isin(article_dois)
        )
        paper_ids_by_article_dois_map = dict(zip(
            _to_str_list(filtered_arrow_table['article_doi']),
            _to_str_list(filtered_arrow_table['paper_id'])
        ))
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
