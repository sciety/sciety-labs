from locust import HttpUser, task


TEST_DOI_1 = '10.1101/2023.05.01.538996'

TEST_FIELDS_1 = {
    'externalIds',
    'title',
    'publicationDate',
    'authors',
    '_evaluationCount',
    '_score'
}

TEST_API_PARAMS_1 = {
    'fields': ','.join(sorted(TEST_FIELDS_1)),
    '_evaluated_only': 'false',
    '_published_within_last_n_days': 60,
    'limit': 3
}


class ScietyLabsApiRelatedArticlesUser(HttpUser):
    @task
    def related_articles(self):
        self.client.get(
            f'/api/like/s2/recommendations/v1/papers/forpaper/DOI:{TEST_DOI_1}',
            params=TEST_API_PARAMS_1
        )
