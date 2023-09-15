from pathlib import Path

from sciety_labs.providers.opensearch import (
    OpenSearchConnectionConfig,
    OpenSearchEnvVariables
)


class TestOpenSearchConnectionConfig:
    def test_should_return_none_if_none_of_the_env_vars_configured(self, env_mock: dict):
        env_mock.clear()
        assert OpenSearchConnectionConfig.from_env() is None

    def test_should_return_config_if_all_of_the_env_vars_are_present(
        self,
        env_mock: dict,
        tmp_path: Path
    ):
        username_file_path = tmp_path / 'username'
        password_file_path = tmp_path / 'password'
        username_file_path.write_text('username1', encoding='utf-8')
        password_file_path.write_text('password1', encoding='utf-8')
        env_mock.clear()
        env_mock[OpenSearchEnvVariables.OPENSEARCH_HOST] = 'hostname1'
        env_mock[OpenSearchEnvVariables.OPENSEARCH_PORT] = '1234'
        env_mock[OpenSearchEnvVariables.OPENSEARCH_USERNAME_FILE_PATH] = str(username_file_path)
        env_mock[OpenSearchEnvVariables.OPENSEARCH_PASSWORD_FILE_PATH] = str(password_file_path)
        env_mock[OpenSearchEnvVariables.OPENSEARCH_INDEX_NAME] = 'index1'
        env_mock[OpenSearchEnvVariables.OPENSEARCH_EMBEDDING_VECTOR_MAPPING_NAME] = 'vector1'
        config = OpenSearchConnectionConfig.from_env()
        assert config == OpenSearchConnectionConfig(
            hostname='hostname1',
            port=1234,
            username='username1',
            password='password1',
            index_name='index1',
            embedding_vector_mapping_name='vector1'
        )
