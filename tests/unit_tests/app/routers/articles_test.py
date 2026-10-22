from unittest.mock import MagicMock

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sciety_labs.app.app_templates import get_app_templates

from sciety_labs.app.routers.articles import (
    create_articles_router,
    validate_article_doi_to_be_displayed
)
from sciety_labs.config.site_config import SiteConfig
from sciety_labs.models.article import (
    ARTICLE_DOIS_NOT_TO_BE_DISPLAYED,
    ArticleMetaData,
    ArticleNotFoundError
)


DOI_1 = '10.12345/test-doi-1'

INVALID_DOI_1 = 'invalid-doi-1'


@pytest.fixture(name='test_client')
def _test_client(app_providers_and_models_mock: MagicMock) -> TestClient:
    app = FastAPI()
    get_article_metadata_by_doi_mock: MagicMock = (
        app_providers_and_models_mock.crossref_metadata_provider.get_article_metadata_by_doi
    )
    get_article_metadata_by_doi_mock.return_value = ArticleMetaData(
        article_doi=DOI_1,
        article_title='Title 1'
    )
    templates = get_app_templates(site_config=SiteConfig())
    app.include_router(create_articles_router(
        app_providers_and_models=app_providers_and_models_mock,
        templates=templates
    ))
    return TestClient(app)


class TestArticlesRouter:
    def test_should_provide_article_response(self, test_client: TestClient):
        response = test_client.get(
            '/articles/by',
            params={'article_doi': DOI_1}
        )
        response.raise_for_status()

    def test_should_return_422_for_invalid_article_doi(self, test_client: TestClient):
        response = test_client.get(
            '/articles/by',
            params={'article_doi': INVALID_DOI_1}
        )
        assert response.status_code == 422


class TestValidateArticleDoiToBeDisplayed:
    def test_should_not_raise_error_for_regular_article_doi(self):
        validate_article_doi_to_be_displayed(article_doi=DOI_1)

    @pytest.mark.parametrize('article_doi', ARTICLE_DOIS_NOT_TO_BE_DISPLAYED)
    def test_should_raise_article_not_found_error_for_doi_not_to_be_displayed(
        self,
        article_doi: str
    ):
        with pytest.raises(ArticleNotFoundError):
            validate_article_doi_to_be_displayed(article_doi=article_doi)
