import logging
from typing import Mapping, Optional, Sequence, Tuple

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.models.article import ArticleMention
from sciety_labs.providers.interfaces.article_recommendation import (
    ArticleRecommendationFilterParameters,
    ArticleRecommendationList
)
from sciety_labs.utils.async_utils import async_iter_sync_iterable, get_list_for_async_iterable
from sciety_labs.utils.pagination import UrlPaginationParameters


LOGGER = logging.getLogger(__name__)


DEFAULT_PUBLISHED_WITHIN_LAST_N_DAYS_BY_EVALUATED_ONLY = {
    False: 60,
    True: 365
}


async def get_article_recommendation_list_for_article_dois(
    article_dois: Sequence[str],
    app_providers_and_models: AppProvidersAndModels,
    filter_parameters: Optional[ArticleRecommendationFilterParameters] = None,
    max_recommendations: Optional[int] = None,
    headers: Optional[Mapping[str, str]] = None
) -> ArticleRecommendationList:
    if (
        len(article_dois) == 1
        and app_providers_and_models.async_single_article_recommendation_provider
    ):
        LOGGER.info('Retrieving single article recommendation')
        article_recommendation_list = await (
            app_providers_and_models
            .async_single_article_recommendation_provider
            .get_article_recommendation_list_for_article_doi(
                article_doi=article_dois[0],
                max_recommendations=max_recommendations,
                filter_parameters=filter_parameters,
                headers=headers
            )
        )
    else:
        LOGGER.info('Retrieving article recommendation for multiple dois')
        article_recommendation_list = await (
            app_providers_and_models
            .article_recommendation_provider.get_article_recommendation_list_for_article_dois(
                article_dois,
                max_recommendations=max_recommendations
            )
        )
    return article_recommendation_list


async def get_article_recommendation_page_and_item_count_for_article_dois(
    article_dois: Sequence[str],
    app_providers_and_models: AppProvidersAndModels,
    max_recommendations: Optional[int],
    pagination_parameters: UrlPaginationParameters,
    filter_parameters: Optional[ArticleRecommendationFilterParameters] = None
) -> Tuple[Sequence[ArticleMention], int]:
    article_recommendation_list = await get_article_recommendation_list_for_article_dois(
        article_dois,
        app_providers_and_models=app_providers_and_models,
        max_recommendations=max_recommendations,
        filter_parameters=filter_parameters
    )
    all_article_recommendations = article_recommendation_list.recommendations
    item_count = len(all_article_recommendations)
    article_recommendation_with_article_meta = await get_list_for_async_iterable(
        app_providers_and_models
        .article_aggregator
        .async_iter_page_article_mention_with_article_meta_and_stats(
            async_iter_sync_iterable(all_article_recommendations),
            page=pagination_parameters.page,
            items_per_page=pagination_parameters.items_per_page
        )
    )
    LOGGER.info(
        'article_recommendation_with_article_meta[:1]=%r',
        article_recommendation_with_article_meta[:1]
    )
    return article_recommendation_with_article_meta, item_count
