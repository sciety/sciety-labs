import logging
from typing import Optional, Sequence, Tuple

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.models.article import ArticleMention, iter_preprint_article_mention
from sciety_labs.providers.article_recommendation import (
    ArticleRecommendationFilterParameters,
    ArticleRecommendationList
)
from sciety_labs.utils.pagination import UrlPaginationParameters


LOGGER = logging.getLogger(__name__)


DEFAULT_PUBLISHED_WITHIN_LAST_N_DAYS_BY_EVALUATED_ONLY = {
    False: 60,
    True: 365
}


def get_article_recommendation_list_for_article_dois(
    article_dois: Sequence[str],
    app_providers_and_models: AppProvidersAndModels,
    filter_parameters: Optional[ArticleRecommendationFilterParameters] = None,
    max_recommendations: Optional[int] = None
) -> ArticleRecommendationList:
    if len(article_dois) == 1 and app_providers_and_models.single_article_recommendation_provider:
        LOGGER.info('Retrieving single article recommendation')
        article_recommendation_list = (
            app_providers_and_models
            .single_article_recommendation_provider.get_article_recommendation_list_for_article_doi(
                article_doi=article_dois[0],
                max_recommendations=max_recommendations,
                filter_parameters=filter_parameters
            )
        )
    else:
        LOGGER.info('Retrieving article recommendation for multiple dois')
        article_recommendation_list = (
            app_providers_and_models
            .article_recommendation_provider.get_article_recommendation_list_for_article_dois(
                article_dois,
                max_recommendations=max_recommendations
            )
        )
    return article_recommendation_list


def get_article_recommendation_page_and_item_count_for_article_dois(
    article_dois: Sequence[str],
    app_providers_and_models: AppProvidersAndModels,
    max_recommendations: Optional[int],
    pagination_parameters: UrlPaginationParameters,
    filter_parameters: Optional[ArticleRecommendationFilterParameters] = None
) -> Tuple[Sequence[ArticleMention], int]:
    article_recommendation_list = get_article_recommendation_list_for_article_dois(
        article_dois,
        app_providers_and_models=app_providers_and_models,
        max_recommendations=max_recommendations,
        filter_parameters=filter_parameters
    )
    all_article_recommendations = list(
        iter_preprint_article_mention(article_recommendation_list.recommendations)
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
