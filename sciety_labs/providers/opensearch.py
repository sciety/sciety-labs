import dataclasses
import logging
import os
from pathlib import Path
from typing import Optional


from opensearchpy import OpenSearch


LOGGER = logging.getLogger(__name__)


class OpenSearchEnvVariables:
    OPENSEARCH_HOST = 'OPENSEARCH_HOST'
    OPENSEARCH_PORT = 'OPENSEARCH_PORT'
    OPENSEARCH_USERNAME_FILE_PATH = 'OPENSEARCH_USERNAME_FILE_PATH'
    OPENSEARCH_PASSWORD_FILE_PATH = 'OPENSEARCH_PASSWORD_FILE_PATH'


def get_optional_secret_file_path_from_env_var_file_path(env_var_name: str) -> Optional[str]:
    file_path = os.getenv(env_var_name)
    if not file_path:
        LOGGER.info('secret env var not configured: %r', env_var_name)
        return None
    if not os.path.exists(file_path):
        LOGGER.info(
            'secret env var configured, but file does not exist: %r -> %r',
            env_var_name, file_path
        )
        return None
    return file_path


def get_optional_secret_from_env_var_file_path(env_var_name: str) -> Optional[str]:
    file_path = get_optional_secret_file_path_from_env_var_file_path(env_var_name)
    if not file_path:
        return None
    return Path(file_path).read_text(encoding='utf-8')


@dataclasses.dataclass(frozen=True)
class OpenSearchConnectionConfig:
    hostname: str
    port: int
    username: str = dataclasses.field(repr=False)
    password: str = dataclasses.field(repr=False)
    verify_certificates: bool = False

    @staticmethod
    def from_env() -> Optional['OpenSearchConnectionConfig']:
        hostname = os.getenv(OpenSearchEnvVariables.OPENSEARCH_HOST)
        port_str = os.getenv(OpenSearchEnvVariables.OPENSEARCH_PORT)
        if not hostname or not port_str:
            LOGGER.info('no OpenSearch hostname or port configured')
            return None
        username = get_optional_secret_from_env_var_file_path(
            OpenSearchEnvVariables.OPENSEARCH_USERNAME_FILE_PATH
        )
        password = get_optional_secret_from_env_var_file_path(
            OpenSearchEnvVariables.OPENSEARCH_PASSWORD_FILE_PATH
        )
        if not username or not password:
            LOGGER.info('no OpenSearch username or password configured')
            return None
        return OpenSearchConnectionConfig(
            hostname=hostname,
            port=int(port_str),
            username=username,
            password=password
        )


def get_opensearch_client(config: OpenSearchConnectionConfig) -> OpenSearch:
    return OpenSearch(
        hosts=[{
            'host': config.hostname,
            'port': config.port
        }],
        http_auth=(config.username, config.password),
        use_ssl=True,
        verify_certs=config.verify_certificates,
        ssl_show_warn=config.verify_certificates
    )
