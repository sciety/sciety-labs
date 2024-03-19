from unittest.mock import MagicMock

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sciety_labs.app.app_templates import get_app_templates

from sciety_labs.app.routers.articles import create_articles_router
from sciety_labs.config.site_config import SiteConfig
from sciety_labs.models.article import ArticleMetaData


DOI_1 = '10.12345/test-doi-1'

INVALID_DOI_1 = 'invalid-doi-1'


@pytest.fixture(name='test_client')
def _test_client(app_providers_and_models_mock: MagicMock) -> TestClient:
    app = FastAPI()
    get_article_metadata_by_doi_mock: MagicMock = (
        app_providers_and_models_mock
        .async_crossref_metadata_provider
        .get_article_metadata_by_doi
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
