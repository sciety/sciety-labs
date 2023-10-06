import logging
import textwrap
from typing import Optional, Sequence, Set, cast

from typing_extensions import NotRequired, TypedDict

from fastapi import APIRouter
import fastapi
from pydantic import BaseModel
import requests

from sciety_labs.app.app_providers_and_models import AppProvidersAndModels
from sciety_labs.app.utils.recommendation import (
    get_article_recommendation_list_for_article_dois
)
from sciety_labs.providers.article_recommendation import (
    ArticleRecommendation,
    ArticleRecommendationList
)
from sciety_labs.providers.opensearch_article_recommendation import (
    DEFAULT_OPENSEARCH_MAX_RECOMMENDATIONS
)
from sciety_labs.utils.datetime import get_date_as_isoformat


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


class RecommendationResponseDict(TypedDict):
    recommendedPapers: Sequence[PaperDict]


class ErrorMessage(BaseModel):
    error: str


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
        }
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
        summary=(
            '''
            Preprint recommendation API endpoint similar to the one provided by S2
            '''
        ),
        description=textwrap.dedent(
            '''
            API endpoint similar to S2\'s [Get recommended papers for a single positive example paper](https://api.semanticscholar.org/api-docs/recommendations#tag/Paper-Recommendations/operation/get_papers_for_paper).

            Only DOIs are accepted.

            It will use the underlying functionality to provide related articles within Sciety Labs.

            When using OpenSearch, this then also provides the improvements made there. e.g.:

            - Only preprints are returned
            - Related articles can be provided for almost any DOI with title and abstract in Crossref
            - The publication date is more accurate
            '''  # noqa pylint: disable=line-too-long
        ),
        response_model=RecommendationResponseDict,
        responses={
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
    )
    def like_s2_recommendations_for_paper(
        article_doi: str = fastapi.Path(
            alias='DOI',
            description=textwrap.dedent(
                '''
                The DOI to provide paper recommendations for.
                '''
            )
        ),
        fields: str = fastapi.Query(
            default=','.join(sorted(DEFAULT_LIKE_S2_RECOMMENDATION_FIELDS)),
            description=textwrap.dedent(
                '''
                Comma separated list of fields. The following fields can be retrieved:

                - `externalIds` (only containing `DOI`)
                - `title`
                - `publicationDate`
                - `authors` (only containing `name`)
                '''
            )
        ),
        limit: Optional[int] = fastapi.Query(
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
    ):
        fields_set = set(fields.split(','))
        try:
            article_recommendation_list = get_article_recommendation_list_for_article_dois(
                [article_doi],
                app_providers_and_models=app_providers_and_models,
                max_recommendations=limit
            )
        except requests.exceptions.HTTPError as exception:
            status_code = exception.response.status_code
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
