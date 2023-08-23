from typing import Mapping, Optional, Protocol, Sequence


class SemanticScholarMappingProvider(Protocol):
    def get_semantic_scholar_paper_ids_by_article_dois_map(
        self,
        article_dois: Sequence[str]
    ) -> Mapping[str, str]:
        pass

    def get_semantic_scholar_paper_id_by_article_doi(
        self,
        article_doi: str
    ) -> Optional[str]:
        pass

    def preload(self):
        pass
