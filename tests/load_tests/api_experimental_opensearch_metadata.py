from locust import HttpUser, task


TEST_DOI_1 = '10.1101/2023.05.01.538996'


TEST_API_PARAMS_1 = {
    'article_doi': TEST_DOI_1
}


NO_CACHE_HEADERS = {
    'Cache-Control': 'no-store'
}


class ScietyLabsApiSyncOpenSearchMetadataUser(HttpUser):
    @task
    def opensearch_metadata(self):
        self.client.get(
            '/api/experimental/sync/opensearch/metadata/by/doi',
            params=TEST_API_PARAMS_1,
            headers=NO_CACHE_HEADERS
        )

class ScietyLabsApiAsyncOpenSearchMetadataUser(HttpUser):
    @task
    def opensearch_metadata(self):
        self.client.get(
            '/api/experimental/async/opensearch/metadata/by/doi',
            params=TEST_API_PARAMS_1,
            headers=NO_CACHE_HEADERS
        )
