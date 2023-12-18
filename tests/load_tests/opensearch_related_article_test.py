import json
from pathlib import Path
from locust import HttpUser, task

from sciety_labs.providers.opensearch import OpenSearchConnectionConfig
from tests.load_tests.data import get_data_file_path


OPEN_SEARCH_CONNECTION_CONFIG = OpenSearchConnectionConfig.from_env()

assert OPEN_SEARCH_CONNECTION_CONFIG is not None


SAMPLE_REQUEST = (
    json.loads(
        Path(get_data_file_path('opensearch_sample_related_article_query.json'))
        .read_text(encoding='utf-8')
    )
)


class ScietyLabsOpenSearchUser(HttpUser):
    @task
    def related_articles(self):
        self.client.post(
            f'/{OPEN_SEARCH_CONNECTION_CONFIG.index_name}/_search',
            params={'_source_includes': 'doi,s2.title,europepmc.title_with_markup'},
            auth=(
                OPEN_SEARCH_CONNECTION_CONFIG.username,
                OPEN_SEARCH_CONNECTION_CONFIG.password
            ),
            json=SAMPLE_REQUEST,
            verify=False
        )
