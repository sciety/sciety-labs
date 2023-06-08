import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.utils.common import (
    AnnotatedPaginationParameters,
    get_page_title
)
from sciety_labs.utils.pagination import get_url_pagination_state_for_pagination_parameters


LOGGER = logging.getLogger(__name__)


def create_list_by_twitter_handle_router(
    app_providers_and_models: AppProvidersAndModels,
    templates: Jinja2Templates
):
    article_aggregator = app_providers_and_models.article_aggregator

    router = APIRouter()

    @router.get('/lists/by-twitter-handle/{twitter_handle}', response_class=HTMLResponse)
    def list_by_twitter_handle(
        request: Request,
        twitter_handle: str,
        pagination_parameters: AnnotatedPaginationParameters
    ):
        assert app_providers_and_models.twitter_user_article_list_provider
        twitter_user = (
            app_providers_and_models
            .twitter_user_article_list_provider.get_twitter_user_by_screen_name(
                twitter_handle
            )
        )
        article_mention_iterable = (
            app_providers_and_models
            .twitter_user_article_list_provider.iter_article_mentions_by_user(
                twitter_user
            )
        )
        article_mention_with_article_meta = list(
            article_aggregator.iter_page_article_mention_with_article_meta_and_stats(
                article_mention_iterable,
                page=pagination_parameters.page,
                items_per_page=pagination_parameters.items_per_page
            )
        )
        LOGGER.info(
            'article_mention_with_article_meta[:1]=%r', article_mention_with_article_meta[:1]
        )

        # Note: we don't know the page count unless this is the last page
        url_pagination_state = get_url_pagination_state_for_pagination_parameters(
            url=request.url,
            pagination_parameters=pagination_parameters,
            remaining_item_iterable=article_mention_iterable
        )
        return templates.TemplateResponse(
            'pages/list-by-twitter-handle.html', {
                'request': request,
                'page_title': get_page_title(
                    f'Twitter curations by {twitter_user.name} (@{twitter_handle})'
                ),
                'twitter_handle': twitter_handle,
                'twitter_user': twitter_user,
                'article_list_content': article_mention_with_article_meta,
                'pagination': url_pagination_state
            }
        )

    return router
