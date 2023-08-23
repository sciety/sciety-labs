import logging
from typing import Any, Mapping, Sequence

import pyarrow.compute as pc


from sciety_labs.providers.bigquery_provider import BigQueryArrowTableProvider
from sciety_labs.providers.semantic_scholar_mapping import BaseSemanticScholarMappingProvider


LOGGER = logging.getLogger(__name__)


def _to_str_list(list_: Sequence[Any]) -> Sequence[str]:
    return [str(value) for value in list_]


class SemanticScholarBigQueryMappingProvider(
    BigQueryArrowTableProvider,
    BaseSemanticScholarMappingProvider
):
    def __init__(self, **kwargs):
        super().__init__(
            name='Semantic Scholar Mapping',
            query_file_name='get_semantic_scholar_mapping.sql',
            **kwargs
        )

    def do_get_semantic_scholar_paper_ids_by_article_dois_map(
        self,
        article_dois: Sequence[str]
    ) -> Mapping[str, str]:
        arrow_table = self.get_arrow_table()
        filtered_arrow_table = arrow_table.filter(
            pc.field('article_doi').isin(article_dois)
        )
        return dict(zip(
            _to_str_list(filtered_arrow_table['article_doi']),
            _to_str_list(filtered_arrow_table['paper_id'])
        ))
