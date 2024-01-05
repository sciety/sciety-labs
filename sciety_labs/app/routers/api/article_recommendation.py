from datetime import date, timedelta
import logging
import textwrap
from typing import Any, Optional, Sequence, Set, cast

from typing_extensions import NotRequired, TypedDict

from fastapi import APIRouter
import fastapi
from pydantic import BaseModel
import requests

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.utils.recommendation import (
    DEFAULT_PUBLISHED_WITHIN_LAST_N_DAYS_BY_EVALUATED_ONLY,
    get_article_recommendation_list_for_article_dois
)
from sciety_labs.providers.article_recommendation import (
    ArticleRecommendation,
    ArticleRecommendationFilterParameters,
    ArticleRecommendationList
)
from sciety_labs.providers.opensearch_article_recommendation import (
    DEFAULT_OPENSEARCH_MAX_RECOMMENDATIONS
)
from sciety_labs.utils.datetime import get_date_as_isoformat
from sciety_labs.utils.fastapi import get_cache_control_headers_for_request


LOGGER = logging.getLogger(__name__)


DEFAULT_LIKE_S2_RECOMMENDATION_FIELDS = {'externalIds'}


class ExternalIdsDict(TypedDict):
    DOI: str


class AuthorDict(TypedDict):
    name: str


class PaperDict(TypedDict):
    externalIds: NotRequired[Optional[ExternalIdsDict]]
    title: NotRequired[Optional[str]]
    publicationDate: NotRequired[Optional[str]]
    authors: NotRequired[Optional[Sequence[AuthorDict]]]
    _evaluationCount: NotRequired[Optional[int]]
    _score: NotRequired[Optional[float]]


class RecommendationResponseDict(TypedDict):
    recommendedPapers: Sequence[PaperDict]


class ErrorMessage(BaseModel):
    error: str


LIKE_S2_RECOMMENDATION_API_SUMMARY = (
    '''
    Preprint recommendation API endpoint similar to the one provided by S2
    '''
)

LIKE_S2_RECOMMENDATION_API_DESCRIPTION = textwrap.dedent(
    '''
    API endpoint similar to S2\'s [Get recommended papers for a single positive example paper](https://api.semanticscholar.org/api-docs/recommendations#tag/Paper-Recommendations/operation/get_papers_for_paper).

    Only DOIs are accepted.

    It will use the underlying functionality to provide related articles within Sciety Labs.

    When using OpenSearch, this then also provides the improvements made there. e.g.:

    - Only preprints are returned
    - Related articles can be provided for almost any DOI with title and abstract in Crossref
    - The publication date is more accurate
    - Ability filter by evaluated preprints
    - Ability to increase the date range

    Parameters and fields starting with underscore are specific to this API (not like S2).
    '''  # noqa pylint: disable=line-too-long
)

LIKE_S2_RECOMMENDATION_API_EXAMPLE_RESPONSES: dict = {
    200: {
        'content': {
            'application/json': {
                'example': {
                    'recommendedPapers': [{
                        'externalIds': {'DOI': '10.12345/doi1'},
                        'title': 'Title 1',
                        'publicationDate': '2001-02-03',
                        'authors': [{'name': 'Author 1'}, {'name': 'Author 2'}]
                    }, {
                        'externalIds': {'DOI': '10.12345/doi2'},
                        'title': 'Title 2',
                        'publicationDate': '2001-02-03',
                        'authors': None
                    }]
                }
            }
        }
    },
    404: {
        'model': ErrorMessage,
        'content': {
            'application/json': {
                'example': {
                    'error': 'Paper with id DOI:invalid-doi not found'
                }
            }
        }
    }
}


LIKE_S2_RECOMMENDATION_API_ARTICLE_DOI_FASTAPI_PATH = fastapi.Path(
    alias='DOI',
    description=textwrap.dedent(
        '''
        The DOI to provide paper recommendations for.
        '''
    ),
    examples=[  # Note: These only seem to appear in /redoc
        '10.1101/2022.08.08.502889'
    ]
)

LIKE_S2_RECOMMENDATION_API_FIELDS_FASTAPI_QUERY = fastapi.Query(
    default=','.join(sorted(DEFAULT_LIKE_S2_RECOMMENDATION_FIELDS)),
    description=textwrap.dedent(
        '''
        Comma separated list of fields. The following fields can be retrieved:

        - `externalIds` (only containing `DOI`)
        - `title`
        - `publicationDate`
        - `authors` (only containing `name`)
        - `_evaluationCount`
        - `_score`
        '''
    ),
    examples=[  # Note: These only seem to appear in /redoc
        'externalIds',
        'externalIds,title,publicationDate,authors',
        'externalIds,title,publicationDate,authors,_evaluationCount,_score'
    ]
)

LIKE_S2_RECOMMENDATION_API_LIMIT_FASTAPI_QUERY = fastapi.Query(
    default=None,
    description=textwrap.dedent(
        f'''
        Maximimum number of papers returned.
        The default will be implementation specific.
        When the OpenSearch backend is used, it will be
        `{DEFAULT_OPENSEARCH_MAX_RECOMMENDATIONS}`.
        '''
    )
)

LIKE_S2_RECOMMENDATION_API_EVALUATED_ONLY_FASTAPI_QUERY = fastapi.Query(
    alias='_evaluated_only',
    default=False,
    description=textwrap.dedent(
        '''
        If true, only evaluated articles will be recommended.
        Not part of S2, and only working with OpenSearch.
        '''
    )
)

LIKE_S2_RECOMMENDATION_API_PUBLISHED_WITHIN_LAST_N_DAYS_FASTAPI_QUERY = fastapi.Query(
    alias='_published_within_last_n_days',
    default=None,
    examples=list(
        DEFAULT_PUBLISHED_WITHIN_LAST_N_DAYS_BY_EVALUATED_ONLY.values()
    ),
    description=textwrap.dedent(
        f'''
        Only consider papers published within the last *n* days.

        The default will be
        `{DEFAULT_PUBLISHED_WITHIN_LAST_N_DAYS_BY_EVALUATED_ONLY[False]}`,
        or
        `{DEFAULT_PUBLISHED_WITHIN_LAST_N_DAYS_BY_EVALUATED_ONLY[True]}`
        when `evaluated_only` is `true`.
        '''
    )
)


def get_s2_recommended_author_list_for_author_names(
    author_name_list: Optional[Sequence[str]]
) -> Optional[Sequence[AuthorDict]]:
    if not author_name_list:
        return None
    return [{'name': name} for name in author_name_list]


def get_s2_recommended_paper_response_for_article_recommendation(
    article_recommendation: ArticleRecommendation,
    fields: Optional[Set[str]] = None
) -> PaperDict:
    response: PaperDict = {
        'externalIds': {
            'DOI': article_recommendation.article_doi
        },
        '_score': article_recommendation.score
    }
    article_meta = article_recommendation.article_meta
    if article_meta:
        response = {
            **response,
            'title': article_meta.article_title,
            'publicationDate': get_date_as_isoformat(article_meta.published_date),
            'authors': get_s2_recommended_author_list_for_author_names(
                article_meta.author_name_list
            )
        }
    article_stats = article_recommendation.article_stats
    if article_stats:
        response = {
            **response,
            '_evaluationCount': article_stats.evaluation_count
        }
    if fields:
        response = cast(
            PaperDict,
            {key: value for key, value in response.items() if key in fields}
        )
    return response


def get_s2_recommended_papers_response_for_article_recommendation_list(
    article_recommendation_list: ArticleRecommendationList,
    fields: Optional[Set[str]] = None
) -> RecommendationResponseDict:
    return {
        'recommendedPapers': [
            get_s2_recommended_paper_response_for_article_recommendation(
                article_recommendation,
                fields=fields
            )
            for article_recommendation in article_recommendation_list.recommendations
        ]
    }


def create_api_article_recommendation_router(
    app_providers_and_models: AppProvidersAndModels
):
    router = APIRouter()

    @router.get(
        '/like/s2/recommendations/v1/papers/forpaper/DOI:{DOI:path}',
        summary=LIKE_S2_RECOMMENDATION_API_SUMMARY,
        description=LIKE_S2_RECOMMENDATION_API_DESCRIPTION,
        response_model=RecommendationResponseDict,
        responses=LIKE_S2_RECOMMENDATION_API_EXAMPLE_RESPONSES
    )
    def like_s2_recommendations_for_paper(  # pylint: disable=too-many-arguments
        request: fastapi.Request,
        article_doi: str = LIKE_S2_RECOMMENDATION_API_ARTICLE_DOI_FASTAPI_PATH,
        fields: str = LIKE_S2_RECOMMENDATION_API_FIELDS_FASTAPI_QUERY,
        limit: Optional[int] = LIKE_S2_RECOMMENDATION_API_LIMIT_FASTAPI_QUERY,
        evaluated_only: bool = LIKE_S2_RECOMMENDATION_API_EVALUATED_ONLY_FASTAPI_QUERY,
        published_within_last_n_days: Optional[int] = (
            LIKE_S2_RECOMMENDATION_API_PUBLISHED_WITHIN_LAST_N_DAYS_FASTAPI_QUERY
        )
    ):
        fields_set = set(fields.split(','))
        if not published_within_last_n_days:
            published_within_last_n_days = DEFAULT_PUBLISHED_WITHIN_LAST_N_DAYS_BY_EVALUATED_ONLY[
                evaluated_only
            ]
        filter_parameters = ArticleRecommendationFilterParameters(
            exclude_article_dois={article_doi},
            from_publication_date=date.today() - timedelta(days=published_within_last_n_days),
            evaluated_only=evaluated_only
        )
        try:
            article_recommendation_list = get_article_recommendation_list_for_article_dois(
                [article_doi],
                app_providers_and_models=app_providers_and_models,
                filter_parameters=filter_parameters,
                max_recommendations=limit,
                headers=get_cache_control_headers_for_request(request)
            )
        except requests.exceptions.RequestException as exception:
            status_code = exception.response.status_code if exception.response else 500
            LOGGER.info('Exception retrieving metadata (%r): %r', status_code, exception)
            if status_code != 404:
                raise
            return fastapi.responses.JSONResponse(
                {'error': f'Paper with id DOI:{article_doi} not found'},
                status_code=404
            )
        return get_s2_recommended_papers_response_for_article_recommendation_list(
            article_recommendation_list,
            fields=fields_set
        )

    @router.get(
        '/async/like/s2/recommendations/v1/papers/forpaper/DOI:{DOI:path}',
    )
    async def async_like_s2_recommendations_for_paper(  # pylint: disable=too-many-arguments
        request: fastapi.Request,
        article_doi: str = LIKE_S2_RECOMMENDATION_API_ARTICLE_DOI_FASTAPI_PATH,
        fields: str = LIKE_S2_RECOMMENDATION_API_FIELDS_FASTAPI_QUERY,
        limit: Optional[int] = LIKE_S2_RECOMMENDATION_API_LIMIT_FASTAPI_QUERY,
        evaluated_only: bool = LIKE_S2_RECOMMENDATION_API_EVALUATED_ONLY_FASTAPI_QUERY,
        published_within_last_n_days: Optional[int] = (
            LIKE_S2_RECOMMENDATION_API_PUBLISHED_WITHIN_LAST_N_DAYS_FASTAPI_QUERY
        )
    ):
        fields_set = set(fields.split(','))
        if not published_within_last_n_days:
            published_within_last_n_days = DEFAULT_PUBLISHED_WITHIN_LAST_N_DAYS_BY_EVALUATED_ONLY[
                evaluated_only
            ]
        filter_parameters = ArticleRecommendationFilterParameters(
            exclude_article_dois={article_doi},
            from_publication_date=date.today() - timedelta(days=published_within_last_n_days),
            evaluated_only=evaluated_only
        )
        try:
            assert app_providers_and_models.async_single_article_recommendation_provider
            article_recommendation_list = await (
                app_providers_and_models
                .async_single_article_recommendation_provider
                .get_article_recommendation_list_for_article_doi(
                    article_doi=article_doi,
                    max_recommendations=limit,
                    filter_parameters=filter_parameters,
                    headers=get_cache_control_headers_for_request(request)
                )
            )
        except requests.exceptions.RequestException as exception:
            status_code = exception.response.status_code if exception.response else 500
            LOGGER.info('Exception retrieving metadata (%r): %r', status_code, exception)
            if status_code != 404:
                raise
            return fastapi.responses.JSONResponse(
                {'error': f'Paper with id DOI:{article_doi} not found'},
                status_code=404
            )
        return get_s2_recommended_papers_response_for_article_recommendation_list(
            article_recommendation_list,
            fields=fields_set
        )

    return router
