from abc import ABC, abstractmethod
from typing import Mapping, Optional, Protocol, Sequence


class SemanticScholarMappingProvider(Protocol):
    @abstractmethod
    def get_semantic_scholar_paper_ids_by_article_dois_map(
        self,
        article_dois: Sequence[str]
    ) -> Mapping[str, str]:
        pass

    @abstractmethod
    def get_semantic_scholar_paper_id_by_article_doi(
        self,
        article_doi: str
    ) -> Optional[str]:
        pass

    @abstractmethod
    def preload(self):
        pass


class BaseSemanticScholarMappingProvider(ABC, SemanticScholarMappingProvider):
    def get_semantic_scholar_paper_id_by_article_doi(
        self,
        article_doi: str
    ) -> Optional[str]:
        paper_ids_by_article_dois_map = self.get_semantic_scholar_paper_ids_by_article_dois_map(
            article_dois=[article_doi]
        )
        return paper_ids_by_article_dois_map.get(article_doi)
