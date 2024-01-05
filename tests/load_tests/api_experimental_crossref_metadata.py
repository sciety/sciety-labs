from locust import HttpUser, task


TEST_DOI_1 = '10.1101/2023.05.01.538996'


TEST_API_PARAMS_1 = {
    'article_doi': TEST_DOI_1
}


NO_CACHE_HEADERS = {
    'Cache-Control': 'no-store'
}


class ScietyLabsApiSyncCrossrefMetadataUser(HttpUser):
    @task
    def crossref_metadata(self):
        self.client.get(
            '/api/experimental/sync/crossref/metadata/by/doi',
            params=TEST_API_PARAMS_1,
            headers=NO_CACHE_HEADERS
        )


class ScietyLabsApiAsyncCrossrefMetadataUser(HttpUser):
    @task
    def crossref_metadata(self):
        self.client.get(
            '/api/experimental/async/crossref/metadata/by/doi',
            params=TEST_API_PARAMS_1,
            headers=NO_CACHE_HEADERS
        )
