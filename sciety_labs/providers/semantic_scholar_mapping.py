from abc import ABC, abstractmethod
import logging
from time import monotonic
from typing import Mapping, Optional, Protocol, Sequence


LOGGER = logging.getLogger(__name__)


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
    @abstractmethod
    def do_get_semantic_scholar_paper_ids_by_article_dois_map(
        self,
        article_dois: Sequence[str]
    ) -> Mapping[str, str]:
        pass

    def get_semantic_scholar_paper_ids_by_article_dois_map(
        self,
        article_dois: Sequence[str]
    ) -> Mapping[str, str]:
        start_time = monotonic()
        paper_ids_by_article_dois_map = self.do_get_semantic_scholar_paper_ids_by_article_dois_map(
            article_dois=article_dois
        )
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
