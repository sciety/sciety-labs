import logging
from typing import Iterable, Sequence, Tuple

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.models.article import ArticleMention, iter_preprint_article_mention
from sciety_labs.utils.pagination import UrlPaginationParameters


LOGGER = logging.getLogger(__name__)


def get_article_recommendation_page_and_item_count_for_article_dois(
    article_dois: Iterable[str],
    app_providers_and_models: AppProvidersAndModels,
    max_recommendations: int,
    pagination_parameters: UrlPaginationParameters
) -> Tuple[Sequence[ArticleMention], int]:
    all_article_recommendations = list(
        iter_preprint_article_mention(
            app_providers_and_models
            .article_recommendation_provider.get_article_recommendation_list_for_article_dois(
                article_dois,
                max_recommendations=max_recommendations
            ).recommendations
        )
    )
    item_count = len(all_article_recommendations)
    article_recommendation_with_article_meta = list(
        app_providers_and_models
        .article_aggregator.iter_page_article_mention_with_article_meta_and_stats(
            all_article_recommendations,
            page=pagination_parameters.page,
            items_per_page=pagination_parameters.items_per_page
        )
    )
    LOGGER.info(
        'article_recommendation_with_article_meta[:1]=%r',
        article_recommendation_with_article_meta[:1]
    )
    return article_recommendation_with_article_meta, item_count
