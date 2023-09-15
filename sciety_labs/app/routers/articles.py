import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests

import opensearchpy.exceptions

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.utils.common import (
    AnnotatedPaginationParameters,
    get_page_title
)
from sciety_labs.app.utils.recommendation import (
    get_article_recommendation_list_for_article_dois,
    get_article_recommendation_page_and_item_count_for_article_dois
)
from sciety_labs.models.article import iter_preprint_article_mention
from sciety_labs.providers.semantic_scholar import DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS
from sciety_labs.utils.pagination import get_url_pagination_state_for_pagination_parameters
from sciety_labs.utils.text import remove_markup_or_none


LOGGER = logging.getLogger(__name__)


def create_articles_router(
    app_providers_and_models: AppProvidersAndModels,
    templates: Jinja2Templates
):
    article_aggregator = app_providers_and_models.article_aggregator

    router = APIRouter()

    @router.get('/articles/by', response_class=HTMLResponse)
    def article_by_article_doi(
        request: Request,
        article_doi: str
    ):
        try:
            article_meta = (
                app_providers_and_models
                .crossref_metadata_provider.get_article_metadata_by_doi(article_doi)
            )
        except requests.exceptions.HTTPError as exception:
            status_code = exception.response.status_code
            LOGGER.info('Exception retrieving metadata (%r): %r', status_code, exception)
            if status_code != 404:
                raise
            return templates.TemplateResponse(
                'errors/error.html', {
                    'request': request,
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

        try:
            all_article_recommendations = list(
                iter_preprint_article_mention(
                    get_article_recommendation_list_for_article_dois(
                        [article_doi],
                        app_providers_and_models=app_providers_and_models,
                        max_recommendations=DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS
                    ).recommendations
                )
            )
        except (requests.exceptions.HTTPError, opensearchpy.exceptions.TransportError) as exc:
            LOGGER.warning('failed to get recommendations for %r due to %r', article_doi, exc)
            all_article_recommendations = []
        article_recommendation_with_article_meta = list(
            article_aggregator.iter_page_article_mention_with_article_meta_and_stats(
                all_article_recommendations,
                page=1,
                items_per_page=3
            )
        )
        LOGGER.info(
            'article_recommendation_with_article_meta[:1]=%r',
            article_recommendation_with_article_meta[:1]
        )

        article_recommendation_url = (
            request.url.replace(path='/articles/article-recommendations/by')
        )

        return templates.TemplateResponse(
            'pages/article-by-article-doi.html', {
                'request': request,
                'page_title': get_page_title(article_meta.article_title),
                'page_description': remove_markup_or_none(
                    article_meta.abstract
                ),
                'article_meta': article_meta,
                'article_stats': article_stats,
                'article_images': article_images,
                'article_recommendation_list': article_recommendation_with_article_meta,
                'article_recommendation_url': article_recommendation_url
            }
        )

    @router.get('/articles/article-recommendations/by', response_class=HTMLResponse)
    def article_recommendations_by_article_doi(  # pylint: disable=too-many-arguments
        request: Request,
        article_doi: str,
        pagination_parameters: AnnotatedPaginationParameters,
        max_recommendations: Optional[int] = None
    ):
        article_meta = (
            app_providers_and_models
            .crossref_metadata_provider.get_article_metadata_by_doi(article_doi)
        )
        article_recommendation_with_article_meta, item_count = (
            get_article_recommendation_page_and_item_count_for_article_dois(
                [article_doi],
                app_providers_and_models=app_providers_and_models,
                max_recommendations=max_recommendations,
                pagination_parameters=pagination_parameters
            )
        )

        url_pagination_state = get_url_pagination_state_for_pagination_parameters(
            url=request.url,
            pagination_parameters=pagination_parameters,
            item_count=item_count
        )
        return templates.TemplateResponse(
            'pages/article-recommendations-by-article-doi.html', {
                'request': request,
                'page_title': get_page_title(
                    f'Article recommendations for {article_meta.article_title}'
                ),
                'article_meta': article_meta,
                'article_list_content': article_recommendation_with_article_meta,
                'pagination': url_pagination_state
            }
        )

    return router
