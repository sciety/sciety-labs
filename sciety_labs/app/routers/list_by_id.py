import logging
from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.utils.common import (
    DEFAULT_ARTICLE_RECOMMENDATION_RSS_ITEM_COUNT,
    DEFAULT_ITEMS_PER_PAGE,
    AnnotatedPaginationParameters,
    get_owner_url,
    get_page_title,
    get_rss_url
)
from sciety_labs.app.utils.recommendation import (
    get_article_recommendation_page_and_item_count_for_article_dois
)
from sciety_labs.app.utils.response import AtomResponse
from sciety_labs.models.article import iter_preprint_article_mention
from sciety_labs.providers.semantic_scholar import DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS
from sciety_labs.utils.pagination import get_url_pagination_state_for_pagination_parameters
from sciety_labs.utils.text import remove_markup_or_none


LOGGER = logging.getLogger(__name__)


def create_list_by_id_router(
    app_providers_and_models: AppProvidersAndModels,
    templates: Jinja2Templates
):
    article_aggregator = app_providers_and_models.article_aggregator

    router = APIRouter()

    @router.get('/lists/by-id/{list_id}', response_class=HTMLResponse)
    def list_by_sciety_list_id(
        request: Request,
        list_id: str,
        pagination_parameters: AnnotatedPaginationParameters
    ):
        list_summary_data = (
            app_providers_and_models.lists_model.get_list_summary_data_by_list_id(list_id)
        )
        LOGGER.info('list_summary_data: %r', list_summary_data)
        list_images = (
            app_providers_and_models
            .google_sheet_list_image_provider.get_list_images_by_list_id(list_id)
        )
        LOGGER.info('list_images: %r', list_images)
        item_count = list_summary_data.article_count
        article_mention_with_article_meta = (
            article_aggregator.iter_page_article_mention_with_article_meta_and_stats(
                app_providers_and_models.lists_model.iter_article_mentions_by_list_id(list_id),
                page=pagination_parameters.page,
                items_per_page=pagination_parameters.items_per_page
            )
        )

        url_pagination_state = get_url_pagination_state_for_pagination_parameters(
            url=request.url,
            pagination_parameters=pagination_parameters,
            item_count=item_count
        )
        return templates.TemplateResponse(
            'pages/list-by-sciety-list-id.html', {
                'request': request,
                'page_title': get_page_title(list_summary_data.list_meta.list_name),
                'page_description': remove_markup_or_none(
                    list_summary_data.list_meta.list_description
                ),
                'rss_url': get_rss_url(request),
                'owner_url': get_owner_url(list_summary_data.owner),
                'list_summary_data': list_summary_data,
                'list_images': list_images,
                'article_list_content': article_mention_with_article_meta,
                'pagination': url_pagination_state
            }
        )

    @router.get('/lists/by-id/{list_id}/atom.xml', response_class=AtomResponse)
    def list_atom_by_sciety_list_id(
        request: Request,
        list_id: str,
        items_per_page: Optional[int] = DEFAULT_ITEMS_PER_PAGE,
        page: int = 1
    ):
        list_summary_data = (
            app_providers_and_models.lists_model.get_list_summary_data_by_list_id(list_id)
        )
        LOGGER.info('list_summary_data: %r', list_summary_data)
        article_mention_with_article_meta = (
            article_aggregator.iter_page_article_mention_with_article_meta_and_stats(
                app_providers_and_models.lists_model.iter_article_mentions_by_list_id(list_id),
                page=page,
                items_per_page=items_per_page
            )
        )
        return templates.TemplateResponse(
            'pages/list-by-sciety-list-id.atom.xml', {
                'request': request,
                'list_summary_data': list_summary_data,
                'article_list_content': article_mention_with_article_meta
            },
            media_type=AtomResponse.media_type
        )

    # pylint: disable=duplicate-code
    @router.get('/lists/by-id/{list_id}/article-recommendations', response_class=HTMLResponse)
    def article_recommendations_by_sciety_list_id(  # pylint: disable=too-many-arguments
        request: Request,
        list_id: str,
        pagination_parameters: AnnotatedPaginationParameters,
        from_sciety: bool = False,
        from_sciety_alias: bool = Query(False, alias='from-sciety'),
        max_recommendations: int = DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS
    ):
        list_summary_data = (
            app_providers_and_models.lists_model.get_list_summary_data_by_list_id(list_id)
        )
        article_recommendation_with_article_meta, item_count = (
            get_article_recommendation_page_and_item_count_for_article_dois(
                [
                    article_mention.article_doi
                    for article_mention in (
                        app_providers_and_models
                        .lists_model.iter_article_mentions_by_list_id(list_id)
                    )
                ],
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
            'pages/article-recommendations-by-sciety-list-id.html', {
                'request': request,
                'page_title': get_page_title(
                    f'Article recommendations for {list_summary_data.list_meta.list_name}'
                ),
                'rss_url': get_rss_url(request),
                'owner_url': get_owner_url(list_summary_data.owner),
                'list_summary_data': list_summary_data,
                'from_sciety': from_sciety or from_sciety_alias,
                'article_list_content': article_recommendation_with_article_meta,
                'pagination': url_pagination_state
            }
        )
    # pylint: enable=duplicate-code

    @router.get(
        '/lists/by-id/{list_id}/article-recommendations/atom.xml',
        response_class=AtomResponse
    )
    def article_recommendations_atom_by_sciety_list_id(
        request: Request,
        list_id: str,
        items_per_page: Optional[int] = DEFAULT_ARTICLE_RECOMMENDATION_RSS_ITEM_COUNT,
        page: int = 1,
        max_recommendations: int = DEFAULT_SEMANTIC_SCHOLAR_MAX_RECOMMENDATIONS
    ):
        list_summary_data = (
            app_providers_and_models.lists_model.get_list_summary_data_by_list_id(list_id)
        )
        LOGGER.info('list_summary_data: %r', list_summary_data)
        article_recommendation_list = (
            app_providers_and_models
            .semantic_scholar_provider.get_article_recommendation_list_for_article_dois(
                (
                    article_mention.article_doi
                    for article_mention in (
                        app_providers_and_models
                        .lists_model.iter_article_mentions_by_list_id(
                            list_id
                        )
                    )
                ),
                max_recommendations=max_recommendations
            )
        )
        recommendation_timestamp = article_recommendation_list.recommendation_timestamp
        all_article_recommendations = list(
            iter_preprint_article_mention(article_recommendation_list.recommendations)
        )
        article_recommendation_with_article_meta = list(
            article_aggregator.iter_page_article_mention_with_article_meta_and_stats(
                all_article_recommendations,
                page=page,
                items_per_page=items_per_page
            )
        )
        LOGGER.info('recommendation_timestamp: %r', recommendation_timestamp)
        return templates.TemplateResponse(
            'pages/article-recommendations-by-sciety-list-id.atom.xml', {
                'request': request,
                'feed_title': (
                    f'Article recommendations for {list_summary_data.list_meta.list_name}'
                ),
                'recommendation_timestamp': recommendation_timestamp,
                'list_summary_data': list_summary_data,
                'article_list_content': article_recommendation_with_article_meta
            },
            media_type=AtomResponse.media_type
        )

    return router
