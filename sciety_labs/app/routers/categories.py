from datetime import date, datetime
import logging
from typing import Sequence, Union

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.utils.common import (
    DEFAULT_ITEMS_PER_PAGE,
    AnnotatedFromScietyParameter,
    AnnotatedPaginationParameters,
    get_page_title,
    get_rss_url
)
from sciety_labs.app.utils.response import AtomResponse
from sciety_labs.models.article import ArticleSearchResultItem
from sciety_labs.providers.papers.async_papers import PageNumberBasedPaginationParameters
from sciety_labs.utils.datetime import get_utcnow
from sciety_labs.utils.pagination import get_url_pagination_state_for_pagination_parameters


LOGGER = logging.getLogger(__name__)


def get_rss_updated_timestamp(
    search_result_list_with_article_meta: Sequence[ArticleSearchResultItem]
) -> Union[date, datetime]:
    latest_evaluation_publication_timestamps = [
        article_mention.article_stats.latest_evaluation_publication_timestamp
        for article_mention in search_result_list_with_article_meta
        if (
            article_mention.article_stats
            and article_mention.article_stats.latest_evaluation_publication_timestamp
        )
    ]
    if not latest_evaluation_publication_timestamps:
        return get_utcnow()
    return max(latest_evaluation_publication_timestamps)


def create_categories_router(
    app_providers_and_models: AppProvidersAndModels,
    templates: Jinja2Templates
):
    article_aggregator = app_providers_and_models.article_aggregator

    router = APIRouter()

    @router.get('/categories', response_class=HTMLResponse)
    async def categories(
        request: Request,
        evaluated_only: bool = True
    ):
        category_display_names = await (
            app_providers_and_models
            .async_paper_provider
            .get_category_display_name_list(
                evaluated_only=evaluated_only
            )
        )
        return templates.TemplateResponse(
            request=request,
            name='pages/categories-list.html',
            context={
                'page_title': 'Browse Categories',
                'category_display_names': category_display_names
            }
        )

    @router.get('/categories/articles', response_class=HTMLResponse)
    async def categories_articles(
        request: Request,
        category: str,
        pagination_parameters: AnnotatedPaginationParameters,
        from_sciety: AnnotatedFromScietyParameter,
        evaluated_only: bool = True
    ):
        search_results_list = await (
            app_providers_and_models
            .async_paper_provider
            .get_preprints_for_category_results_list(
                category=category,
                evaluated_only=evaluated_only,
                pagination_parameters=PageNumberBasedPaginationParameters(
                    page=pagination_parameters.page,
                    items_per_page=pagination_parameters.items_per_page
                )
            )
        )
        article_mention_with_article_meta = (
            article_aggregator.iter_page_article_mention_with_article_meta_and_stats(
                search_results_list.items,
                page=1,  # pagination is handled by service
                items_per_page=pagination_parameters.items_per_page
            )
        )
        url_pagination_state = get_url_pagination_state_for_pagination_parameters(
            url=request.url,
            pagination_parameters=pagination_parameters,
            item_count=search_results_list.total
        )
        return templates.TemplateResponse(
            request=request,
            name='pages/categories-articles.html',
            context={
                'page_title': get_page_title(
                    category
                ),
                'rss_url': get_rss_url(request),
                'category_display_name': category,
                'from_sciety': from_sciety,
                'article_list_content': article_mention_with_article_meta,
                'pagination': url_pagination_state
            }
        )

    @router.get('/categories/articles/atom.xml', response_class=AtomResponse)
    async def categories_articles_atom_xml(
        request: Request,
        category: str,
        items_per_page: int = DEFAULT_ITEMS_PER_PAGE,
        page: int = 1,
        evaluated_only: bool = True
    ):
        search_results_list = await (
            app_providers_and_models
            .async_paper_provider
            .get_preprints_for_category_results_list(
                category=category,
                evaluated_only=evaluated_only,
                pagination_parameters=PageNumberBasedPaginationParameters(
                    page=page,
                    items_per_page=items_per_page
                )
            )
        )
        article_mention_with_article_meta = (
            article_aggregator.iter_page_article_mention_with_article_meta_and_stats(
                search_results_list.items,
                page=1,  # pagination is handled by service
                items_per_page=items_per_page
            )
        )
        return templates.TemplateResponse(
            request=request,
            name='pages/categories-articles.atom.xml',
            context={
                'page_title': get_page_title(
                    category
                ),
                'updated_timestamp': get_rss_updated_timestamp(
                    article_mention_with_article_meta
                ),
                'category_display_name': category,
                'article_list_content': article_mention_with_article_meta
            },
            media_type=AtomResponse.media_type
        )

    return router
