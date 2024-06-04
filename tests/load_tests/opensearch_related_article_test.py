import json
import random
from pathlib import Path
from locust import HttpUser, task

from sciety_labs.providers.opensearch.client import OpenSearchConnectionConfig
from tests.load_tests.data import get_data_file_path


OPEN_SEARCH_CONNECTION_CONFIG = OpenSearchConnectionConfig.from_env()

assert OPEN_SEARCH_CONNECTION_CONFIG is not None


SAMPLE_QUERY = (
    json.loads(
        Path(get_data_file_path('opensearch_sample_related_article_query.json'))
        .read_text(encoding='utf-8')
    )
)


def get_sample_query_with_random_vector() -> dict:
    vector_length = len(SAMPLE_QUERY['query']['knn']['s2.specter_embedding_v1.vector']['vector'])
    vector = [random.random() for _ in range(vector_length)]
    return {
        **SAMPLE_QUERY,
        'query': {
            **SAMPLE_QUERY['query'],
            'knn': {
                **SAMPLE_QUERY['query']['knn'],
                's2.specter_embedding_v1.vector': {
                    **SAMPLE_QUERY['query']['knn']['s2.specter_embedding_v1.vector'],
                    'vector': vector
                }
            }
        }
    }


class ScietyLabsOpenSearchUser(HttpUser):
    @task
    def related_articles(self):
        query = get_sample_query_with_random_vector()
        self.client.post(
            f'/{OPEN_SEARCH_CONNECTION_CONFIG.index_name}/_search',
            params={'_source_includes': 'doi,s2.title,europepmc.title_with_markup'},
            auth=(
                OPEN_SEARCH_CONNECTION_CONFIG.username,
                OPEN_SEARCH_CONNECTION_CONFIG.password
            ),
            json=query,
            verify=False
        )
