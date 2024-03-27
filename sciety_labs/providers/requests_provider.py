from typing import Dict, Mapping, Optional

import requests

from sciety_labs.utils.http_headers import get_merged_headers


class RequestsProvider:
    def __init__(
        self,
        requests_session: Optional[requests.Session] = None
    ) -> None:
        self.headers: Dict[str, str] = {
            'User-Agent': 'Sciety Labs; +https://github.com/sciety/sciety-labs'
        }
        if requests_session is None:
            requests_session = requests.Session()
        self.requests_session = requests_session
        self.timeout: float = 5 * 60

    def get_headers(
        self,
        headers: Optional[Mapping[str, str]] = None
    ) -> Mapping[str, str]:
        return get_merged_headers(self.headers, headers)
