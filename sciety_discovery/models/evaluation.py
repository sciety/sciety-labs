from threading import Lock
from typing import Dict, Iterable, List, NamedTuple, Sequence

from sciety_discovery.models.article import ArticleMention, ArticleStats


DOI_ARTICLE_ID_PREFIX = 'doi:'


class EvaluationReference(NamedTuple):
    article_id: str
    evaluation_locator: str


class ScietyEventEvaluationStatsModel:
    def __init__(self, sciety_events: Sequence[dict]):
        self._evaluation_reference_by_article_id: Dict[str, List[EvaluationReference]] = {}
        self._lock = Lock()
        self.apply_events(sciety_events)

    def _do_apply_events(self, sciety_events: Sequence[dict]):
        for event in sciety_events:
            event_name = event['event_name']
            if event_name != 'EvaluationRecorded':
                continue
            article_id = event['article_id']
            evaluation_locator = event['evaluation_locator']
            self._evaluation_reference_by_article_id.setdefault(article_id, []).append(
                EvaluationReference(
                    article_id=article_id,
                    evaluation_locator=evaluation_locator
                )
            )

    def apply_events(self, sciety_events: Sequence[dict]):
        with self._lock:
            self._do_apply_events(sciety_events)

    def get_evaluation_count_by_article_id(self, article_id: str) -> int:
        return len(self._evaluation_reference_by_article_id.get(article_id, []))

    def iter_article_mention_with_article_stats(
        self,
        article_mention_iterable: Iterable[ArticleMention]
    ) -> Iterable[ArticleMention]:
        return (
            article_mention._replace(
                article_stats=ArticleStats(
                    evaluation_count=self.get_evaluation_count_by_article_id(
                        DOI_ARTICLE_ID_PREFIX + article_mention.article_doi
                    )
                )
            )
            for article_mention in article_mention_iterable
        )
