from typing import Dict, Mapping, Optional

import aiohttp


class AsyncRequestsProvider:
    def __init__(
        self,
        client_session: Optional[aiohttp.ClientSession] = None
    ) -> None:
        self.headers: Dict[str, str] = {
            'User-Agent': 'Sciety Labs; +https://github.com/sciety/sciety-labs'
        }
        if client_session is None:
            client_session = aiohttp.ClientSession()
        self.client_session = client_session
        self.timeout: float = 5 * 60

    def get_headers(
        self,
        headers: Optional[Mapping[str, str]] = None
    ) -> Mapping[str, str]:
        if headers:
            return {
                **headers,
                **self.headers
            }
        return self.headers
