from datetime import date, timedelta
import logging
from typing import Annotated, Any, Dict, Optional, cast

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.utils.common import (
    AnnotatedPaginationParameters,
    get_page_title
)
from sciety_labs.app.utils.recommendation import (
    DEFAULT_PUBLISHED_WITHIN_LAST_N_DAYS_BY_EVALUATED_ONLY,
    get_article_recommendation_page_and_item_count_for_article_dois
)
from sciety_labs.models.article import ArticleStats
from sciety_labs.providers.article_recommendation import ArticleRecommendationFilterParameters
from sciety_labs.utils.pagination import get_url_pagination_state_for_pagination_parameters
from sciety_labs.utils.text import remove_markup_or_none


LOGGER = logging.getLogger(__name__)


AnnotatedArticleDoiQueryParameter = Annotated[
    str,
    Query(pattern=r'^10\.\d{4,}(\.\d+)?/.*$')
]


def get_article_recommendation_filter_parameters(
    article_doi: str,
    article_stats: Optional[ArticleStats]
) -> ArticleRecommendationFilterParameters:
    evaluated_only = bool(article_stats and article_stats.evaluation_count)
    published_within_last_n_days = (
        DEFAULT_PUBLISHED_WITHIN_LAST_N_DAYS_BY_EVALUATED_ONLY[evaluated_only]
    )
    return ArticleRecommendationFilterParameters(
        exclude_article_dois={article_doi},
        from_publication_date=date.today() - timedelta(days=published_within_last_n_days),
        evaluated_only=evaluated_only
    )


def create_articles_router(
    app_providers_and_models: AppProvidersAndModels,
    templates: Jinja2Templates
):
    router = APIRouter()

    @router.get('/articles/by', response_class=HTMLResponse)
    def article_by_article_doi(
        request: Request,
        article_doi: AnnotatedArticleDoiQueryParameter
    ):
        try:
            article_meta = (
                app_providers_and_models
                .crossref_metadata_provider.get_article_metadata_by_doi(article_doi)
            )
        except requests.exceptions.RequestException as exception:
            status_code = exception.response.status_code if exception.response is not None else 500
            LOGGER.info('Exception retrieving metadata (%r): %r', status_code, exception)
            if status_code != 404:
                raise
            return templates.TemplateResponse(
                request=request,
                name='errors/error.html',
                context={
                    'page_title': get_page_title(f'Article not found: {article_doi}'),
                    'error_message': f'Article not found: {article_doi}',
                    'exception': exception
                },
                status_code=404
            )
        LOGGER.info('article_meta=%r', article_meta)

        article_stats = (
            app_providers_and_models
            .evaluation_stats_model.get_article_stats_by_article_doi(article_doi)
        )
        article_images = (
            app_providers_and_models
            .google_sheet_article_image_provider.get_article_images_by_doi(article_doi)
        )

        article_recommendation_url = (
            request.url.replace(path='/articles/article-recommendations/by')
        )
        article_recommendation_fragment_url = (
            article_recommendation_url.include_query_params(
                fragment=True,
                max_recommendations=3,
                enable_pagination=False
            )
        )
        LOGGER.info('article_recommendation_fragment_url: %r', article_recommendation_fragment_url)

        return templates.TemplateResponse(
            request=request,
            name='pages/article-by-article-doi.html',
            context={
                'page_title': get_page_title(article_meta.article_title),
                'page_description': remove_markup_or_none(
                    article_meta.abstract
                ),
                'article_meta': article_meta,
                'article_stats': article_stats,
                'article_images': article_images,
                'article_recommendation_fragment_url': article_recommendation_fragment_url
            }
        )

    @router.get('/articles/article-recommendations/by', response_class=HTMLResponse)
    def article_recommendations_by_article_doi(  # pylint: disable=too-many-arguments
        request: Request,
        article_doi: AnnotatedArticleDoiQueryParameter,
        pagination_parameters: AnnotatedPaginationParameters,
        max_recommendations: Optional[int] = None,
        fragment: bool = False
    ):
        article_meta = (
            app_providers_and_models
            .crossref_metadata_provider.get_article_metadata_by_doi(article_doi)
        )
        if not fragment:
            article_recommendation_fragment_url = (
                request.url.include_query_params(fragment=True)
            )
            return templates.TemplateResponse(
                request=request,
                name='pages/article-recommendations-by-article-doi.html',
                context={
                    'page_title': get_page_title(
                        f'Article recommendations for {article_meta.article_title}'
                    ),
                    'article_meta': article_meta,
                    'article_recommendation_fragment_url': article_recommendation_fragment_url
                }
            )
        article_meta = (
            app_providers_and_models
            .crossref_metadata_provider.get_article_metadata_by_doi(article_doi)
        )
        article_stats = (
            app_providers_and_models
            .evaluation_stats_model.get_article_stats_by_article_doi(article_doi)
        )
        filter_parameters = get_article_recommendation_filter_parameters(
            article_doi,
            article_stats=article_stats
        )
        article_recommendation_with_article_meta, item_count = (
            get_article_recommendation_page_and_item_count_for_article_dois(
                [article_doi],
                app_providers_and_models=app_providers_and_models,
                max_recommendations=max_recommendations,
                pagination_parameters=pagination_parameters,
                filter_parameters=filter_parameters
            )
        )

        article_recommendation_url = (
            request.url.remove_query_params([
                'fragment', 'enable_pagination', 'max_recommendations'
            ])
            if not pagination_parameters.enable_pagination
            else None
        )

        url_pagination_state = get_url_pagination_state_for_pagination_parameters(
            url=request.url.remove_query_params(['fragment']),
            pagination_parameters=pagination_parameters,
            item_count=item_count
        )
        LOGGER.info('url_pagination_state: %r', url_pagination_state)
        return templates.TemplateResponse(
            request=request,
            name='fragments/article-recommendations.html',
            context=cast(
                Dict[str, Any],  # workaround for mypy false positive
                {
                    'article_list_content': article_recommendation_with_article_meta,
                    'pagination': url_pagination_state,
                    'article_recommendation_url': article_recommendation_url
                }
            )
        )

    return router
