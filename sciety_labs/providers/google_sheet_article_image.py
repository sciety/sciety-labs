import logging
from typing import Iterable, Mapping, Optional

import google.auth
import googleapiclient.discovery

from sciety_labs.models.article import ArticleImages, ArticleMention
from sciety_labs.utils.cache import (
    ChainedObjectCache,
    DummySingleObjectCache,
    InMemorySingleObjectCache,
    SingleObjectCache
)


LOGGER = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


DEFAULT_SHEET_ID = '1zEiW1AniF8SRcM__3q1gbRbT_Svd_9d83oICVtom00w'
DEFAULT_SHEET_RANGE = 'A:B'


class GoogleSheetArticleImageProvider:
    def __init__(
        self,
        sheet_id: str = DEFAULT_SHEET_ID,
        sheet_range: str = DEFAULT_SHEET_RANGE,
        refresh_manually: bool = False,
        article_image_mapping_cache: Optional[SingleObjectCache[Mapping[str, str]]] = None
    ) -> None:
        self.sheet_id = sheet_id
        self.sheet_range = sheet_range
        if article_image_mapping_cache is None:
            article_image_mapping_cache = DummySingleObjectCache()
        self.article_image_mapping_cache = article_image_mapping_cache
        self.current_article_image_mapping_cache = article_image_mapping_cache
        if refresh_manually:
            self.current_article_image_mapping_cache = ChainedObjectCache[Mapping[str, str]]([
                InMemorySingleObjectCache(max_age_in_seconds=None),
                article_image_mapping_cache
            ])

    def load_mapping(self) -> Mapping[str, str]:
        LOGGER.info(
            'Loading article image mapping from sheet_id: %r, sheet_range: %r',
            self.sheet_id, self.sheet_range
        )
        credentials, _ = google.auth.default(scopes=SCOPES)
        service = googleapiclient.discovery.build('sheets', 'v4', credentials=credentials)
        sheets = service.spreadsheets()
        result = sheets.values().get(
            spreadsheetId=self.sheet_id,
            range=self.sheet_range
        ).execute()
        values = result.get('values', [])
        LOGGER.info('sheet values: %r', values)
        return dict((row for row in values[1:] if len(row) == 2 and row[1]))

    def get_mapping(self) -> Mapping[str, str]:
        return self.article_image_mapping_cache.get_or_load(
            load_fn=self.load_mapping
        )

    def refresh(self):
        self.article_image_mapping_cache.reload(
            load_fn=self.load_mapping
        )

    def get_article_image_url_by_doi(self, article_doi: str) -> Optional[str]:
        mapping = self.get_mapping()
        LOGGER.info('mapping: %r', mapping)
        return mapping.get(article_doi)

    def get_article_images_by_doi(self, article_doi: str) -> ArticleImages:
        return ArticleImages(
            image_url=self.get_article_image_url_by_doi(article_doi)
        )

    def iter_article_mention_with_article_image_url(
        self,
        article_mention_iterable: Iterable[ArticleMention]
    ) -> Iterable[ArticleMention]:
        return (
            article_mention._replace(
                article_images=self.get_article_images_by_doi(
                    article_mention.article_doi
                )
            )
            for article_mention in article_mention_iterable
        )
