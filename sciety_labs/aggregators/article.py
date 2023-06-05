import logging
from typing import Iterable, Optional

from sciety_labs.models.article import ArticleMention
from sciety_labs.models.evaluation import ScietyEventEvaluationStatsModel
from sciety_labs.providers.crossref import CrossrefMetaDataProvider
from sciety_labs.providers.google_sheet_image import GoogleSheetArticleImageProvider
from sciety_labs.utils.pagination import get_page_iterable


LOGGER = logging.getLogger(__name__)


class ArticleAggregator:
    def __init__(
        self,
        evaluation_stats_model: ScietyEventEvaluationStatsModel,
        crossref_metadata_provider: CrossrefMetaDataProvider,
        google_sheet_article_image_provider: GoogleSheetArticleImageProvider
    ):
        self.evaluation_stats_model = evaluation_stats_model
        self.crossref_metadata_provider = crossref_metadata_provider
        self.google_sheet_article_image_provider = google_sheet_article_image_provider

    def iter_page_article_mention_with_article_meta_and_stats(
        self,
        article_mention_iterable: Iterable[ArticleMention],
        page: int,
        items_per_page: Optional[int]
    ) -> Iterable[ArticleMention]:
        article_mention_iterable = (
            self.evaluation_stats_model.iter_article_mention_with_article_stats(
                article_mention_iterable
            )
        )
        article_mention_with_article_meta = (
            self.crossref_metadata_provider.iter_article_mention_with_article_meta(
                get_page_iterable(
                    article_mention_iterable, page=page, items_per_page=items_per_page
                )
            )
        )
        article_mention_with_article_meta = (
            self.google_sheet_article_image_provider.iter_article_mention_with_article_image_url(
                article_mention_with_article_meta
            )
        )
        article_mention_with_article_meta = list(article_mention_with_article_meta)
        LOGGER.debug(
            'article_mention_with_article_meta[:1]=%r', article_mention_with_article_meta[:1]
        )
        return article_mention_with_article_meta
