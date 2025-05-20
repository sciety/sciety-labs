import functools
import logging
from time import monotonic
from typing import Any, Collection, Mapping, Type, Union, cast, Optional
from urllib.parse import urlencode
import aiohttp


from opensearchpy import OpenSearch, Transport
import opensearchpy

import requests

from sciety_labs.providers.opensearch.config import (
    OpenSearchConnectionConfig
)


LOGGER = logging.getLogger(__name__)


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
                    timeout=aiohttp.ClientTimeout(total=timeout),
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


def get_opensearch_client(
    config: OpenSearchConnectionConfig,
    requests_session: Optional[requests.Session] = None
) -> OpenSearch:
    LOGGER.info('OpenSearch requests_session: %r', requests_session)
    return OpenSearch(
        hosts=[{
            'host': config.hostname,
            'port': config.port
        }],
        http_auth=(config.username, config.password),
        use_ssl=True,
        verify_certs=config.verify_certificates,
        ssl_show_warn=config.verify_certificates,
        timeout=config.timeout,
        transport_class=cast(
            Type[Transport],
            functools.partial(
                OpenSearchTransport,
                url_prefix=f'https://{config.hostname}:{config.port}',
                requests_session=requests_session,
                auth=(config.username, config.password)
            )
        )
    )


def get_opensearch_client_or_none(
    config: Optional[OpenSearchConnectionConfig],
    requests_session: Optional[requests.Session] = None
) -> Optional[OpenSearch]:
    if not config:
        return None
    return get_opensearch_client(config, requests_session=requests_session)


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
