import dataclasses
import functools
import logging
import os
from pathlib import Path
from time import monotonic
from typing import Any, Collection, Mapping, Type, Union, cast, Optional
from urllib.parse import urlencode
import aiohttp


from opensearchpy import Transport
import opensearchpy

import requests


LOGGER = logging.getLogger(__name__)


class OpenSearchEnvVariables:
    OPENSEARCH_HOST = 'OPENSEARCH_HOST'
    OPENSEARCH_PORT = 'OPENSEARCH_PORT'
    OPENSEARCH_USERNAME_FILE_PATH = 'OPENSEARCH_USERNAME_FILE_PATH'
    OPENSEARCH_PASSWORD_FILE_PATH = 'OPENSEARCH_PASSWORD_FILE_PATH'
    OPENSEARCH_INDEX_V2_NAME = 'OPENSEARCH_INDEX_V2_NAME'
    OPENSEARCH_INDEX_V2_EMBEDDING_VECTOR_MAPPING_NAME = (
        'OPENSEARCH_INDEX_V2_EMBEDDING_VECTOR_MAPPING_NAME'
    )


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
class OpenSearchConnectionConfig:  # pylint: disable=too-many-instance-attributes
    hostname: str
    port: int
    username: str = dataclasses.field(repr=False)
    password: str = dataclasses.field(repr=False)
    index_name: str
    verify_certificates: bool = False
    timeout: float = 60
    embedding_vector_mapping_name: Optional[str] = None

    @staticmethod
    def from_env() -> Optional['OpenSearchConnectionConfig']:
        hostname = os.getenv(OpenSearchEnvVariables.OPENSEARCH_HOST)
        port_str = os.getenv(OpenSearchEnvVariables.OPENSEARCH_PORT)
        if not hostname or not port_str:
            LOGGER.info('no OpenSearch hostname or port configured')
            return None
        index_name = os.getenv(OpenSearchEnvVariables.OPENSEARCH_INDEX_V2_NAME)
        if not index_name:
            LOGGER.info('no OpenSearch index name configured')
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
        embedding_vector_mapping_name = os.getenv(
            OpenSearchEnvVariables.OPENSEARCH_INDEX_V2_EMBEDDING_VECTOR_MAPPING_NAME
        )
        return OpenSearchConnectionConfig(
            hostname=hostname,
            port=int(port_str),
            username=username,
            password=password,
            index_name=index_name,
            embedding_vector_mapping_name=embedding_vector_mapping_name
        )


class OpenSearchTransport(Transport):
    def __init__(
        self,
        *args,
        url_prefix: str,
        requests_session: Optional[requests.Session] = None,
        auth: Any = None,
        **kwargs
    ):
        self.url_prefix = url_prefix
        self.requests_session = requests_session
        self.auth = auth
        self.verify_certificates = kwargs.get('verify_certs', True)
        super().__init__(*args, **kwargs)

    def perform_request(  # pylint: disable=too-many-arguments
        self,
        method: str,
        url: str,
        params: Optional[Mapping[str, Any]] = None,
        body: Any = None,
        timeout: Optional[Union[int, float]] = None,
        ignore: Collection[int] = (),
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        if self.requests_session:
            full_url = f'{self.url_prefix}{url}'
            LOGGER.info('full_url: %r (%r)', full_url, method)
            LOGGER.debug('body: %r', body)
            start_time = monotonic()
            try:
                response = self.requests_session.request(
                    method=method,
                    url=full_url,
                    params=params,
                    json=body,
                    timeout=timeout,
                    headers=headers,
                    auth=self.auth,
                    verify=self.verify_certificates
                )
            except requests.exceptions.ConnectionError as exc:
                raise opensearchpy.exceptions.ConnectionError(str(exc)) from exc
            end_time = monotonic()
            LOGGER.info(
                'response: status=%r, time=%.3f seconds',
                response.status_code,
                (end_time - start_time)
            )
            if response.status_code == 404:
                raise opensearchpy.exceptions.NotFoundError(f'Not found: {full_url}')
            response.raise_for_status()
            return response.json()
        return super().perform_request(
            method=method,
            url=url,
            params=params,
            body=body,
            timeout=timeout,
            ignore=ignore,
            headers=headers
        )


class AsyncOpenSearchConnection(opensearchpy.AIOHttpConnection):
    def __init__(
        self,
        *args,
        client_session: Optional[aiohttp.ClientSession] = None,
        **kwargs
    ):
        self.client_session = client_session
        self.verify_certificates = kwargs.get('verify_certs', True)
        super().__init__(*args, **kwargs)

    async def perform_request(  # pylint: disable=too-many-arguments, too-many-locals
        self,
        method: str,
        url: str,
        params: Optional[Mapping[str, Any]] = None,
        body: Optional[bytes] = None,
        timeout: Optional[Union[int, float]] = None,
        ignore: Collection[int] = (),
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        if self.client_session is not None:
            url_path = f'{self.url_prefix}{url}'
            full_url = f'{self.host}{url_path}'
            if params:
                full_url += '?' + urlencode(params)
            LOGGER.info('Async Request: %r (method=%r)', full_url, method)
            LOGGER.debug('body: %r', body)
            req_headers = self.headers.copy()
            if headers:
                req_headers.update(headers)
            start_time = monotonic()
            try:
                async with self.client_session.request(
                    method=method,
                    url=full_url,
                    data=body,
                    timeout=timeout,
                    headers=req_headers,
                    verify_ssl=self.verify_certificates
                ) as response:
                    end_time = monotonic()
                    LOGGER.info(
                        'response: status=%r, time=%.3f seconds',
                        response.status,
                        (end_time - start_time)
                    )
                    if response.status == 404:
                        raise opensearchpy.exceptions.NotFoundError(f'Not found: {url}')
                    response.raise_for_status()
                    raw_data = await response.text()
                    return response.status, response.headers, raw_data
            except aiohttp.ClientConnectorError as exc:
                raise opensearchpy.exceptions.ConnectionError(str(exc)) from exc
        return await super().perform_request(
            method=method,
            url=url,
            params=params,
            body=body,
            timeout=timeout,
            ignore=ignore,
            headers=headers
        )


# def get_opensearch_client(
#     config: OpenSearchConnectionConfig,
#     requests_session: Optional[requests.Session] = None
# ) -> OpenSearch:
#     LOGGER.info('OpenSearch requests_session: %r', requests_session)
#     return OpenSearch(
#         hosts=[{
#             'host': config.hostname,
#             'port': config.port
#         }],
#         http_auth=(config.username, config.password),
#         use_ssl=True,
#         verify_certs=config.verify_certificates,
#         ssl_show_warn=config.verify_certificates,
#         timeout=config.timeout,
#         transport_class=cast(
#             Type[Transport],
#             functools.partial(
#                 OpenSearchTransport,
#                 url_prefix=f'https://{config.hostname}:{config.port}',
#                 requests_session=requests_session,
#                 auth=(config.username, config.password)
#             )
#         )
#     )


# def get_opensearch_client_or_none(
#     config: Optional[OpenSearchConnectionConfig],
#     requests_session: Optional[requests.Session] = None
# ) -> Optional[OpenSearch]:
#     if not config:
#         return None
#     return get_opensearch_client(config, requests_session=requests_session)


def get_async_opensearch_client(
    config: OpenSearchConnectionConfig,
    client_session: Optional[aiohttp.ClientSession] = None
) -> opensearchpy.AsyncOpenSearch:
    LOGGER.info('OpenSearch client_session: %r', client_session)
    return opensearchpy.AsyncOpenSearch(
        hosts=[{
            'host': config.hostname,
            'port': config.port
        }],
        http_auth=(config.username, config.password),
        use_ssl=True,
        verify_certs=config.verify_certificates,
        ssl_show_warn=config.verify_certificates,
        timeout=config.timeout,
        connection_class=cast(
            Type[AsyncOpenSearchConnection],
            functools.partial(
                AsyncOpenSearchConnection,
                client_session=client_session
            )
        )
    )


def get_async_opensearch_client_or_none(
    config: Optional[OpenSearchConnectionConfig],
    client_session: Optional[aiohttp.ClientSession] = None
) -> Optional[opensearchpy.AsyncOpenSearch]:
    if not config:
        return None
    return get_async_opensearch_client(config, client_session=client_session)
