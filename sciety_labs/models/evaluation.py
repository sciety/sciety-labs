import logging
from threading import Lock
from typing import AsyncIterable, AsyncIterator, Dict, Iterable, List, NamedTuple, Sequence, cast

from sciety_labs.models.article import ArticleMentionT, ArticleStats
from sciety_labs.models.sciety_event import (
    ALTERNATIVE_EVALUATION_RECORDED_EVENT_NAMES,
    ALTERNATIVE_EVALUATION_REMOVED_EVENT_NAMES
)


LOGGER = logging.getLogger(__name__)


DOI_ARTICLE_ID_PREFIX = 'doi:'


class EvaluationReference(NamedTuple):
    article_id: str
    evaluation_locator: str


def get_normalized_article_id(article_id: str) -> str:
    return article_id.lower()


class ScietyEventEvaluationStatsModel:
    def __init__(self, sciety_events: Sequence[dict]):
        self._evaluation_references_by_article_id: Dict[str, List[EvaluationReference]] = {}
        self._evaluation_reference_by_evaluation_locator: Dict[str, EvaluationReference] = {}
        self._lock = Lock()
        self.apply_events(sciety_events)

    def _do_apply_evaluation_recorded_event(self, event: dict):
        article_id = event['article_id']
        normalized_article_id = get_normalized_article_id(article_id)
        evaluation_locator = event['evaluation_locator']
        evaluation_reference = EvaluationReference(
            article_id=article_id,
            evaluation_locator=evaluation_locator
        )
        self._evaluation_references_by_article_id.setdefault(normalized_article_id, []).append(
            evaluation_reference
        )
        self._evaluation_reference_by_evaluation_locator[evaluation_locator] = (
            evaluation_reference
        )

    def _do_apply_incorrectly_recorded_evaluation_erased_event(self, event: dict):
        evaluation_locator = event['evaluation_locator']
        LOGGER.debug('removing evaluation with locator: %r', evaluation_locator)
        evaluation_reference = self._evaluation_reference_by_evaluation_locator[evaluation_locator]
        LOGGER.debug('removing evaluation: %r', evaluation_reference)
        normalized_article_id = get_normalized_article_id(evaluation_reference.article_id)
        self._evaluation_references_by_article_id[normalized_article_id].remove(
            evaluation_reference
        )

    def _do_apply_events(self, sciety_events: Sequence[dict]):
        self._evaluation_references_by_article_id.clear()
        self._evaluation_reference_by_evaluation_locator.clear()
        for event in sciety_events:
            event_name = event['event_name']
            if event_name in ALTERNATIVE_EVALUATION_RECORDED_EVENT_NAMES:
                self._do_apply_evaluation_recorded_event(event)
            if event_name in ALTERNATIVE_EVALUATION_REMOVED_EVENT_NAMES:
                self._do_apply_incorrectly_recorded_evaluation_erased_event(event)

    def apply_events(self, sciety_events: Sequence[dict]):
        with self._lock:
            self._do_apply_events(sciety_events)

    def get_evaluation_count_by_article_id(self, article_id: str) -> int:
        return len(
            self._evaluation_references_by_article_id.get(
                get_normalized_article_id(article_id),
                []
            )
        )

    def get_article_stats_by_article_doi(self, article_doi: str) -> ArticleStats:
        return ArticleStats(
            evaluation_count=self.get_evaluation_count_by_article_id(
                DOI_ARTICLE_ID_PREFIX + article_doi
            )
        )

    def get_article_mention_with_article_stats(
        self,
        article_mention: ArticleMentionT
    ) -> ArticleMentionT:
        return cast(
            ArticleMentionT,
            article_mention._replace(
                article_stats=self.get_article_stats_by_article_doi(
                    article_mention.article_doi
                )
            )
        )

    def async_iter_article_mention_with_article_stats(
        self,
        article_mention_iterable: AsyncIterable[ArticleMentionT]
    ) -> AsyncIterator[ArticleMentionT]:
        LOGGER.info('article_mention_iterable: %r', article_mention_iterable)
        return (
            self.get_article_mention_with_article_stats(article_mention)
            async for article_mention in article_mention_iterable
        )

    async def async_iter_evaluated_only_article_mention(
        self,
        article_mention_iterable: AsyncIterator[ArticleMentionT]
    ) -> AsyncIterator[ArticleMentionT]:
        async for article_mention in article_mention_iterable:
            if self.get_evaluation_count_by_article_id(
                DOI_ARTICLE_ID_PREFIX + article_mention.article_doi
            ):
                yield article_mention
